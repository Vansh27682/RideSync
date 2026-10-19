from contextlib import closing
import base64
from email.message import EmailMessage
import os
import re
import secrets
import smtplib
import sqlite3
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.secret_key = os.environ.get("RIDESYNC_SECRET_KEY") or secrets.token_hex(32)

DATABASE = os.environ.get(
    "RIDESYNC_DATABASE",
    str(Path(__file__).resolve().with_name("ridesync.db")),
)
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PHONE_PATTERN = re.compile(r"\+[1-9]\d{7,14}")
OTP_EXPIRY_SECONDS = 600
OTP_RESEND_WAIT_SECONDS = 60
OTP_MAX_ATTEMPTS = 5


# Database connection

def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# Database initialization

def init_db():
    with closing(get_db_connection()) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        if "phone" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN phone TEXT")

        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone
            ON users(phone)
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                channel TEXT NOT NULL DEFAULT 'email',
                code_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                consumed INTEGER NOT NULL DEFAULT 0
            )
        """)
        otp_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(password_reset_otps)"
            ).fetchall()
        }
        if "channel" not in otp_columns:
            connection.execute(
                "ALTER TABLE password_reset_otps "
                "ADD COLUMN channel TEXT NOT NULL DEFAULT 'email'"
            )
        connection.commit()


# Password validation

def validate_password(password):
    if len(password) < 8:
        return "Password must contain at least 8 characters."

    if not re.search(r"[A-Za-z]", password):
        return "Password must contain at least one alphabet."

    if not re.search(r"\d", password):
        return "Password must contain at least one number."

    if not re.search(r"[^A-Za-z0-9]", password):
        return "Password must contain at least one special character."

    return None


def send_email_otp(email, code):
    host = os.environ.get("SMTP_HOST")
    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError as error:
        raise RuntimeError("SMTP_PORT must be a valid port number.") from error
    if not 1 <= port <= 65535:
        raise RuntimeError("SMTP_PORT must be between 1 and 65535.")
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    sender = os.environ.get("SMTP_FROM")

    if not all((host, username, password, sender)):
        raise RuntimeError(
            "Email OTP is not configured. Set SMTP_HOST, SMTP_USERNAME, "
            "SMTP_PASSWORD, and SMTP_FROM."
        )

    message = EmailMessage()
    message["Subject"] = "Your RideSync password reset code"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        f"Your RideSync password reset code is {code}. "
        f"It expires in {OTP_EXPIRY_SECONDS // 60} minutes."
    )

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=10) as server:
            server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(message)


def send_sms_otp(phone, code):
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    sender = os.environ.get("TWILIO_PHONE_NUMBER")

    if not all((account_sid, auth_token, sender)):
        raise RuntimeError(
            "SMS OTP is not configured. Set TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER."
        )

    endpoint = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{account_sid}/Messages.json"
    )
    payload = urlencode({
        "From": sender,
        "To": phone,
        "Body": (
            f"Your RideSync password reset code is {code}. "
            f"It expires in {OTP_EXPIRY_SECONDS // 60} minutes."
        ),
    }).encode()
    request_to_send = Request(endpoint, data=payload, method="POST")
    request_to_send.add_header("Content-Type", "application/x-www-form-urlencoded")
    request_to_send.add_header(
        "Authorization",
        "Basic "
        + base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode(),
    )

    try:
        with urlopen(request_to_send, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"Twilio returned HTTP {response.status}.")
    except HTTPError as error:
        raise RuntimeError(f"Twilio returned HTTP {error.code}.") from error
    except URLError as error:
        raise RuntimeError("Could not connect to the Twilio service.") from error


def deliver_otp(channel, destination, code):
    if channel == "email":
        send_email_otp(destination, code)
    else:
        send_sms_otp(destination, code)


def clear_password_reset_session():
    session.pop("password_reset_challenge_id", None)
    session.pop("password_reset_user_id", None)
    session.pop("password_reset_verified_at", None)


# Home and dashboard

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        name=session["user_name"],
        username=session["username"],
        role=session["role"],
    )


# Registration

@app.route("/register", methods=["GET", "POST"])
def register():
    message = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all((name, username, email, phone, password, confirm_password)):
            message = "All fields are required."
        elif len(username) < 3:
            message = "Username must contain at least 3 characters."
        elif not re.fullmatch(r"[A-Za-z0-9_]+", username):
            message = "Username can only contain letters, numbers and underscores."
        elif not EMAIL_PATTERN.fullmatch(email):
            message = "Please enter a valid email address."
        elif not PHONE_PATTERN.fullmatch(phone):
            message = "Enter a valid mobile number in international format, such as +14155552671."
        elif password != confirm_password:
            message = "Passwords do not match."
        else:
            password_error = validate_password(password)
            if password_error:
                message = password_error
            else:
                try:
                    with closing(get_db_connection()) as connection:
                        existing_username = connection.execute(
                            "SELECT id FROM users WHERE username = ?",
                            (username,),
                        ).fetchone()
                        existing_email = connection.execute(
                            "SELECT id FROM users WHERE email = ?",
                            (email,),
                        ).fetchone()
                        existing_phone = connection.execute(
                            "SELECT id FROM users WHERE phone = ?",
                            (phone,),
                        ).fetchone()

                        if existing_username:
                            message = "This username is already taken."
                        elif existing_email:
                            message = "An account with this email already exists."
                        elif existing_phone:
                            message = "This mobile number is already registered."
                        else:
                            try:
                                connection.execute(
                                    """
                                    INSERT INTO users
                                        (name, username, email, phone, password_hash)
                                    VALUES (?, ?, ?, ?, ?)
                                    """,
                                    (
                                        name,
                                        username,
                                        email,
                                        phone,
                                        generate_password_hash(password),
                                    ),
                                )
                                connection.commit()
                            except sqlite3.IntegrityError:
                                message = (
                                    "This username, email, or mobile number "
                                    "is already registered."
                                )
                            else:
                                return redirect(
                                    url_for("login", registered="success")
                                )
                except sqlite3.Error:
                    app.logger.exception(
                        "Database error while registering an account"
                    )
                    message = (
                        "We couldn't access the account database. "
                        "Please try again later."
                    )

    return render_template("register.html", message=message)


# Login

@app.route("/login", methods=["GET", "POST"])
def login():
    message = None
    success_message = None

    if request.args.get("registered") == "success":
        success_message = "Registration successful. Please login."
    elif request.args.get("reset") == "success":
        success_message = "Password reset successful. Please login."

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        password = request.form.get("password", "")

        if not identifier or not password:
            message = "Username or email and password are required."
        else:
            try:
                with closing(get_db_connection()) as connection:
                    user = connection.execute(
                        """
                        SELECT * FROM users
                        WHERE username = ? OR email = ?
                        """,
                        (identifier, identifier),
                    ).fetchone()

                if user and check_password_hash(user["password_hash"], password):
                    session.clear()
                    session["user_id"] = user["id"]
                    session["user_name"] = user["name"]
                    session["username"] = user["username"]
                    session["role"] = user["role"]
                    return redirect(url_for("home"))

                message = "Invalid username/email or password."
            except sqlite3.Error:
                app.logger.exception("Database error while logging in")
                message = (
                    "We couldn't access the account database. "
                    "Please try again later."
                )

    return render_template(
        "login.html",
        message=message,
        success_message=success_message,
    )


# Password reset

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    message = None
    success_message = None

    if request.method == "POST":
        channel = request.form.get("channel", "")
        identifier = request.form.get("identifier", "").strip()
        if channel == "email":
            identifier = identifier.lower()
            valid_identifier = bool(EMAIL_PATTERN.fullmatch(identifier))
            query = "SELECT id, email FROM users WHERE email = ?"
        elif channel == "phone":
            valid_identifier = bool(PHONE_PATTERN.fullmatch(identifier))
            query = "SELECT id, phone FROM users WHERE phone = ?"
        else:
            valid_identifier = False

        if not valid_identifier:
            message = "Enter a valid registered email address or mobile number."
        else:
            clear_password_reset_session()
            with closing(get_db_connection()) as connection:
                user = connection.execute(query, (identifier,)).fetchone()
                now = int(time.time())
                recent_otp = None
                if user:
                    recent_otp = connection.execute(
                        """
                        SELECT id, consumed, expires_at FROM password_reset_otps
                        WHERE user_id = ? AND created_at > ?
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        (user["id"], now - OTP_RESEND_WAIT_SECONDS),
                    ).fetchone()

                if user and not recent_otp:
                    code = f"{secrets.randbelow(1_000_000):06d}"
                    code_hash = generate_password_hash(code)
                    cursor = connection.execute(
                        """
                        INSERT INTO password_reset_otps
                            (user_id, channel, code_hash, created_at, expires_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            user["id"],
                            channel,
                            code_hash,
                            now,
                            now + OTP_EXPIRY_SECONDS,
                        ),
                    )
                    connection.commit()
                    challenge_id = cursor.lastrowid
                    destination = user["email"] if channel == "email" else user["phone"]
                    try:
                        deliver_otp(channel, destination, code)
                    except (OSError, RuntimeError, smtplib.SMTPException):
                        connection.execute(
                            "UPDATE password_reset_otps SET consumed = 1 WHERE id = ?",
                            (challenge_id,),
                        )
                        connection.commit()
                        app.logger.exception("Unable to deliver password reset OTP")
                        message = (
                            "We could not send a verification code right now. "
                            "Please try again later."
                        )
                    else:
                        session["password_reset_challenge_id"] = challenge_id
                        success_message = (
                            "If an account matches those details, a verification "
                            "code has been sent."
                        )
                else:
                    if (
                        user
                        and not recent_otp["consumed"]
                        and recent_otp["expires_at"] > now
                    ):
                        session["password_reset_challenge_id"] = recent_otp["id"]
                    success_message = (
                        "If an account matches those details, a code may have "
                        "been sent recently. Use that code or try again in a minute."
                    )

    return render_template(
        "forgot_password.html",
        message=message,
        success_message=success_message,
    )


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    challenge_id = session.get("password_reset_challenge_id")
    if not challenge_id:
        return redirect(url_for("forgot_password"))

    message = None
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        with closing(get_db_connection()) as connection:
            challenge = connection.execute(
                """
                SELECT * FROM password_reset_otps
                WHERE id = ? AND consumed = 0
                """,
                (challenge_id,),
            ).fetchone()

            if not challenge:
                clear_password_reset_session()
                message = "That code is no longer valid. Request a new one."
            elif challenge["expires_at"] <= int(time.time()):
                clear_password_reset_session()
                message = "That code has expired. Request a new one."
            elif challenge["attempts"] >= OTP_MAX_ATTEMPTS:
                connection.execute(
                    "UPDATE password_reset_otps SET consumed = 1 WHERE id = ?",
                    (challenge_id,),
                )
                connection.commit()
                clear_password_reset_session()
                message = "Too many incorrect attempts. Request a new code."
            elif not re.fullmatch(r"\d{6}", code):
                message = "Enter the 6-digit verification code."
            else:
                connection.execute(
                    "UPDATE password_reset_otps SET attempts = attempts + 1 WHERE id = ?",
                    (challenge_id,),
                )
                if challenge["attempts"] + 1 >= OTP_MAX_ATTEMPTS:
                    connection.execute(
                        "UPDATE password_reset_otps SET consumed = 1 WHERE id = ?",
                        (challenge_id,),
                    )
                connection.commit()
                if check_password_hash(challenge["code_hash"], code):
                    clear_password_reset_session()
                    session["password_reset_user_id"] = challenge["user_id"]
                    session["password_reset_verified_at"] = int(time.time())
                    connection.execute(
                        "UPDATE password_reset_otps SET consumed = 1 WHERE id = ?",
                        (challenge_id,),
                    )
                    connection.commit()
                    return redirect(url_for("reset_password"))
                if challenge["attempts"] + 1 >= OTP_MAX_ATTEMPTS:
                    clear_password_reset_session()
                    message = "Too many incorrect attempts. Request a new code."
                else:
                    message = "The verification code is incorrect."

    return render_template("verify_otp.html", message=message)


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    user_id = session.get("password_reset_user_id")
    verified_at = session.get("password_reset_verified_at")
    if (
        not user_id
        or not verified_at
        or int(time.time()) - verified_at > OTP_EXPIRY_SECONDS
    ):
        clear_password_reset_session()
        return redirect(url_for("forgot_password"))

    message = None
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if password != confirm_password:
            message = "Passwords do not match."
        else:
            password_error = validate_password(password)
            if password_error:
                message = password_error
            else:
                with closing(get_db_connection()) as connection:
                    connection.execute(
                        "UPDATE users SET password_hash = ? WHERE id = ?",
                        (generate_password_hash(password), user_id),
                    )
                    connection.commit()
                clear_password_reset_session()
                return redirect(url_for("login", reset="success"))

    return render_template("reset_password.html", message=message)


# Logout

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# Initialize database for both direct and WSGI application startup
init_db()


# Start application

if __name__ == "__main__":
    app.run(debug=True)
