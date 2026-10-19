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
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student'
        )
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


# REGISTER

@app.route("/register", methods=["GET", "POST"])
def register():

    message = None

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Check whether passwords match
        if password != confirm_password:
            message = "Passwords do not match."

        # Basic password validation
        elif len(password) < 6:
            message = "Password must contain at least 6 characters."

        else:
            connection = get_db_connection()

            # Check whether email already exists
            existing_user = connection.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()

            if existing_user:
                message = "An account with this email already exists."

            else:
                # Hash password before storing it
                hashed_password = generate_password_hash(password)

                connection.execute(
                    """
                    INSERT INTO users (name, email, password)
                    VALUES (?, ?, ?)
                    """,
                    (name, email, hashed_password)
                )

                connection.commit()
                connection.close()

                # Registration successful → Login page
                return redirect(url_for("login"))

            connection.close()

    return render_template(
        "register.html",
        message=message
    )


# LOGIN

@app.route("/login", methods=["GET", "POST"])
def login():

    message = None

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        connection = get_db_connection()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        # Check email and hashed password
        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            return redirect(url_for("home"))

        else:
            message = "Invalid email or password."

    return render_template(
        "login.html",
        message=message
    )


# LOGOUT

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# START APPLICATION

if __name__ == "__main__":
    init_db()
    app.run(debug=True)