

import os
import hmac
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
)
from werkzeug.security import generate_password_hash, check_password_hash

import database

from booking import booking_bp
from admin import admin_bp


DATABASE = database.DATABASE

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "ridesync-dev-secret-key"
)

app.register_blueprint(booking_bp)
app.register_blueprint(admin_bp)


# DATABASE CONNECTION

def get_db_connection():
    database.DATABASE = DATABASE
    return database.get_db_connection()


# AUTHENTICATION HELPER

def login_required():
    return "user_id" in session


@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year}


# DATABASE INITIALIZATION

def init_db():
    connection = get_db_connection()

    if database.is_postgres():

        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                username TEXT UNIQUE,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'customer'
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                registration_number TEXT UNIQUE NOT NULL,
                price_per_hour DOUBLE PRECISION NOT NULL,
                status TEXT NOT NULL DEFAULT 'available',
                image TEXT
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                vehicle_id INTEGER NOT NULL REFERENCES vehicles(id),
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                total_price DOUBLE PRECISION NOT NULL,
                status TEXT NOT NULL DEFAULT 'confirmed',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

    else:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT UNIQUE,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'customer'
            )
        """)

        columns = [
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        ]

        if "username" not in columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN username TEXT"
            )

        if "phone" not in columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN phone TEXT"
            )

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

        connection.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                vehicle_id INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                total_price REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'confirmed',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            )
        """)

    connection.execute("""
        UPDATE users
        SET role = 'customer'
        WHERE role = 'student'
    """)

    connection.commit()
    connection.close()


# DASHBOARD / HOME

@app.route("/")
def home():

    if not login_required():
        return redirect(url_for("login"))

    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    connection = get_db_connection()

    total_vehicles = connection.execute(
        "SELECT COUNT(*) FROM vehicles"
    ).fetchone()[0]

    available_vehicles = connection.execute("""
        SELECT COUNT(*) FROM vehicles
        WHERE LOWER(status) = 'available'
    """).fetchone()[0]

    my_bookings = connection.execute("""
        SELECT COUNT(*) FROM bookings
        WHERE user_id = ? AND LOWER(status) = 'confirmed'
    """, (session["user_id"],)).fetchone()[0]

    recent = connection.execute("""
        SELECT b.*, v.name AS vehicle_name,
               v.type AS vehicle_type
        FROM bookings b
        JOIN vehicles v ON v.id = b.vehicle_id
        WHERE b.user_id = ?
        ORDER BY b.id DESC
        LIMIT 4
    """, (session["user_id"],)).fetchall()

    featured = connection.execute("""
        SELECT * FROM vehicles
        WHERE LOWER(status) = 'available'
        ORDER BY price_per_hour ASC
        LIMIT 3
    """).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        total_vehicles=total_vehicles,
        available_vehicles=available_vehicles,
        my_bookings=my_bookings,
        recent=recent,
        featured=featured
    )


# VEHICLES

@app.route("/vehicles")
def vehicles():

    if not login_required():
        return redirect(url_for("login"))

    search = request.args.get("q", "").strip()
    category = request.args.get("type", "All")

    connection = get_db_connection()

    query = "SELECT * FROM vehicles WHERE 1=1"
    params = []

    if search:
        query += """
            AND (
                name LIKE ?
                OR brand LIKE ?
                OR registration_number LIKE ?
            )
        """
        params.extend([f"%{search}%"] * 3)

    if category in ("Bike", "Scooter"):
        query += " AND type = ?"
        params.append(category)

    query += " ORDER BY type, price_per_hour"

    vehicle_list = connection.execute(
        query, params
    ).fetchall()

    connection.close()

    return render_template(
        "vehicles.html",
        vehicles=vehicle_list,
        search=search,
        category=category
    )


# REGISTRATION

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

        role = request.form.get("role", "customer").strip().lower()
        admin_code = request.form.get("admin_code", "")

        if not all([
            name, username, email, phone,
            password, confirm_password
        ]):
            message = "All fields are required."

        elif role not in ["customer", "admin"]:
            message = "Invalid account type selected."

        elif password != confirm_password:
            message = "Passwords do not match."

        elif (
            len(password) < 8
            or not any(char.isalpha() for char in password)
            or not any(char.isdigit() for char in password)
            or not any(not char.isalnum() for char in password)
        ):
            message = (
                "Password must contain at least 8 characters, "
                "including a letter, number and special character."
            )

        elif role == "admin" and not os.environ.get("RIDESYNC_ADMIN_CODE"):
            message = "Admin registration is currently unavailable."

        elif role == "admin" and not hmac.compare_digest(
            admin_code,
            os.environ.get("RIDESYNC_ADMIN_CODE", "")
        ):
            message = "Invalid admin registration code."

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
                    """
                    SELECT id FROM users
                    WHERE email = ? OR username = ?
                    """,
                    (email, username)
                ).fetchone()

                if existing_user:
                    message = (
                        "An account with this email or username "
                        "already exists."
                    )
                    connection.close()

                else:

                    hashed_password = generate_password_hash(password)

                    try:
                        connection.execute(
                            """
                            INSERT INTO users
                            (name, username, email, phone, password, role)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                name,
                                username,
                                email,
                                normalized_phone,
                                hashed_password,
                                role
                            )
                        )

                        connection.commit()
                        connection.close()

                        return redirect(url_for("login"))

                    except database.IntegrityError:
                        connection.close()
                        message = (
                            "An account with this email or username "
                            "already exists."
                        )

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

                session.clear()
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["role"] = user["role"]

                return redirect(url_for("home"))

            message = "Invalid email or password."

    return render_template("login.html", message=message)


# LOGOUT

@app.route("/logout", methods=["GET", "POST"])
def logout():

    session.clear()

    return redirect(url_for("login"))


# START APPLICATION

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

