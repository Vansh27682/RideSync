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
    vehicle_count = connection.execute(
        "SELECT COUNT(*) FROM vehicles"
    ).fetchone()[0]

    if vehicle_count == 0:
        vehicles = [
            ("Activa 6G", "Scooter", "Honda", "6G", "UK07RS1001", 40, "available", None),
            ("Jupiter", "Scooter", "TVS", "ZX", "UK07RS1002", 40, "available", None),
            ("Access 125", "Scooter", "Suzuki", "125", "UK07RS1003", 45, "available", None),
            ("Ntorq 125", "Scooter", "TVS", "Race Edition", "UK07RS1004", 50, "available", None),
            ("Dio", "Scooter", "Honda", "Standard", "UK07RS1005", 40, "available", None),
            ("Pleasure Plus", "Scooter", "Hero", "XTEC", "UK07RS1006", 40, "available", None),
            ("Destini 125", "Scooter", "Hero", "XTEC", "UK07RS1007", 45, "available", None),
            ("RayZR 125", "Scooter", "Yamaha", "Fi Hybrid", "UK07RS1008", 50, "available", None),
            ("Avenis 125", "Scooter", "Suzuki", "Standard", "UK07RS1009", 45, "available", None),
            ("Fascino 125", "Scooter", "Yamaha", "Fi Hybrid", "UK07RS1010", 45, "available", None),
            ("Activa 125", "Scooter", "Honda", "H-Smart", "UK07RS1011", 50, "available", None),
            ("Jupiter 125", "Scooter", "TVS", "Disc", "UK07RS1012", 50, "available", None),

            ("Pulsar 150", "Bike", "Bajaj", "150", "UK07RS2001", 65, "available", None),
            ("Apache RTR 160", "Bike", "TVS", "160 4V", "UK07RS2002", 75, "available", None),
            ("Splendor Plus", "Bike", "Hero", "XTEC", "UK07RS2003", 55, "available", None),
            ("FZ-S", "Bike", "Yamaha", "FI V4", "UK07RS2004", 75, "available", None),
            ("Hunter 350", "Bike", "Royal Enfield", "Metro", "UK07RS2005", 100, "available", None),
            ("Classic 350", "Bike", "Royal Enfield", "Classic", "UK07RS2006", 110, "available", None),
            ("Pulsar NS200", "Bike", "Bajaj", "NS200", "UK07RS2007", 90, "available", None),
            ("Apache RTR 200", "Bike", "TVS", "4V", "UK07RS2008", 90, "available", None)
        ]

        connection.executemany("""
            INSERT INTO vehicles
            (name, type, brand, model, registration_number,
             price_per_hour, status, image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, vehicles)


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