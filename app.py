from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

# Secret key is required for Flask sessions
app.secret_key = "ridesync-dev-secret-key"

# SQLite database file
DATABASE = "ridesync.db"


# DATABASE CONNECTION

def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# CREATE DATABASE TABLE

def init_db():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT UNIQUE,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student'
    )
    """)
    
    columns = [
        row["name"]
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    ]

    if "username" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN username TEXT")
    
    if "phone" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN phone TEXT")


    connection.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username
        ON users(username)
    """)


    connection.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            registration_number TEXT UNIQUE NOT NULL,
            price_per_hour REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'available',
            image TEXT
        )
    """)


    connection.commit()
    connection.close()


# HOME

@app.route("/")
def home():
    if "user_id" in session:
        return f"""
        <h1>Welcome to RideSync, {session['user_name']}!</h1>
        <p>You are successfully logged in.</p>

        <a href="/vehicles">Browse Vehicles</a>
        <br><br>
        <a href="/logout">Logout</a>
        """

    return redirect(url_for("login"))
# VEHICLES

@app.route("/vehicles")
def vehicles():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    vehicle_list = connection.execute(
        "SELECT * FROM vehicles ORDER BY type, id"
    ).fetchall()

    connection.close()

    return render_template(
        "vehicles.html",
        vehicles=vehicle_list
    )


#register 

@app.route("/register", methods=["GET", "POST"])
def register():
    message = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([name, username, email, phone, password, confirm_password]):
            message = "All fields are required."

        elif password != confirm_password:
            message = "Passwords do not match."

        elif (
            len(password) < 8
            or not any(char.isalpha() for char in password)
            or not any(char.isdigit() for char in password)
            or not any(not char.isalnum() for char in password)
        ):
            message = "Password must contain at least 8 characters, including a letter, number and special character."

        else:
            phone_digits = phone.replace(" ", "").replace("-", "")

            if phone_digits.startswith("+91"):
                phone_digits = phone_digits[3:]

            if (
                len(phone_digits) != 10
                or not phone_digits.isdigit()
                or phone_digits[0] not in "6789"
            ):
                message = "Enter a valid Indian mobile number."

            else:
                normalized_phone = "+91" + phone_digits
                connection = get_db_connection()

                existing_user = connection.execute(
                    "SELECT id FROM users WHERE email = ? OR username = ?",
                    (email, username)
                ).fetchone()

                if existing_user:
                    message = "An account with this email or username already exists."
                    connection.close()

                else:
                    hashed_password = generate_password_hash(password)

                    connection.execute(
                        """
                        INSERT INTO users (name, username, email, phone, password)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (name, username, email, normalized_phone, hashed_password)
                    )

                    connection.commit()
                    connection.close()

                    return redirect(url_for("login"))

    return render_template("register.html", message=message)


# LOGIN

@app.route("/login", methods=["GET", "POST"])
def login():
    message = None

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        if not identifier or not password:
            message = "Username or email and password are required."
        else:
            connection = get_db_connection()

            user = connection.execute(
                """
                SELECT * FROM users
                WHERE LOWER(email) = ? OR LOWER(username) = ?
                """,
                (identifier.lower(), identifier.lower())
            ).fetchone()
            connection.close()

            if user and check_password_hash(user["password"], password):
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["role"] = user["role"]

                return redirect(url_for("home"))
            else:
                message = "Invalid email or password."

    return render_template("login.html", message=message)


# LOGOUT

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# START APPLICATION

if __name__ == "__main__":
    init_db()
    app.run(debug=True)