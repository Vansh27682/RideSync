
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, flash, redirect, render_template,
    request, session, url_for
)
from werkzeug.security import generate_password_hash, check_password_hash


# --------------------------------------------------
# APPLICATION CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "ridesync.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "ridesync-development-secret-key-change-before-launch"
)


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

def init_db():
    with get_db_connection() as connection:

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

        connection.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                vehicle_id INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                duration_hours INTEGER NOT NULL,
                total_price REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Confirmed',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
            )
        """)

        vehicle_count = connection.execute(
            "SELECT COUNT(*) FROM vehicles"
        ).fetchone()[0]

        # Add sample vehicles only if the table is empty.
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
                ("Apache RTR 200", "Bike", "TVS", "4V", "UK07RS2008", 90, "available", None),
            ]

            connection.executemany("""
                INSERT INTO vehicles (
                    name, type, brand, model,
                    registration_number, price_per_hour,
                    status, image
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, vehicles)


# --------------------------------------------------
# AUTHENTICATION HELPER
# --------------------------------------------------

def login_required():
    return "user_id" in session


@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year}


# --------------------------------------------------
# DASHBOARD / HOME
# --------------------------------------------------

@app.route("/")
def home():

    if not login_required():
        return redirect(url_for("login"))

    with get_db_connection() as connection:

        total_vehicles = connection.execute(
            "SELECT COUNT(*) FROM vehicles"
        ).fetchone()[0]

        available_vehicles = connection.execute(
            "SELECT COUNT(*) FROM vehicles WHERE lower(status) = 'available'"
        ).fetchone()[0]

        my_bookings = connection.execute("""
            SELECT COUNT(*) FROM bookings
            WHERE user_id = ? AND status = 'Confirmed'
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
            WHERE lower(status) = 'available'
            ORDER BY price_per_hour ASC
            LIMIT 3
        """).fetchall()

    return render_template(
        "dashboard.html",
        total_vehicles=total_vehicles,
        available_vehicles=available_vehicles,
        my_bookings=my_bookings,
        recent=recent,
        featured=featured
    )


# --------------------------------------------------
# VEHICLE LISTING, SEARCH AND FILTER
# --------------------------------------------------

@app.route("/vehicles")
def vehicles():

    if not login_required():
        return redirect(url_for("login"))

    search = request.args.get("q", "").strip()
    category = request.args.get("type", "All")

    with get_db_connection() as connection:

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

    return render_template(
        "vehicles.html",
        vehicles=vehicle_list,
        search=search,
        category=category
    )


# --------------------------------------------------
# BOOK A VEHICLE
# --------------------------------------------------

@app.route("/book/<int:vehicle_id>", methods=["POST"])
def book_vehicle(vehicle_id):

    if not login_required():
        return redirect(url_for("login"))

    start_time = request.form.get("start_time", "").strip()

    try:
        duration = int(request.form.get("duration", "1"))
        start_dt = datetime.fromisoformat(start_time)

        if duration < 1 or duration > 24:
            raise ValueError

        if start_dt <= datetime.now():
            raise ValueError

    except (ValueError, TypeError):
        flash(
            "Choose a future pickup time and a duration between 1 and 24 hours.",
            "error"
        )
        return redirect(url_for("vehicles"))

    with get_db_connection() as connection:

        vehicle = connection.execute(
            "SELECT * FROM vehicles WHERE id = ?",
            (vehicle_id,)
        ).fetchone()

        if not vehicle or vehicle["status"].lower() != "available":
            flash("This vehicle is currently unavailable.", "error")
            return redirect(url_for("vehicles"))

        total = float(vehicle["price_per_hour"]) * duration

        connection.execute("""
            INSERT INTO bookings (
                user_id, vehicle_id, start_time,
                duration_hours, total_price
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            vehicle_id,
            start_dt.isoformat(timespec="minutes"),
            duration,
            total
        ))

    flash(
        f"{vehicle['name']} reserved successfully. Your booking is confirmed.",
        "success"
    )

    return redirect(url_for("bookings"))


# --------------------------------------------------
# BOOKING HISTORY
# --------------------------------------------------

@app.route("/bookings")
def bookings():

    if not login_required():
        return redirect(url_for("login"))

    with get_db_connection() as connection:

        booking_list = connection.execute("""
            SELECT b.*, v.name AS vehicle_name,
                   v.type AS vehicle_type,
                   v.registration_number,
                   v.brand
            FROM bookings b
            JOIN vehicles v ON v.id = b.vehicle_id
            WHERE b.user_id = ?
            ORDER BY b.id DESC
        """, (session["user_id"],)).fetchall()

    return render_template(
        "bookings.html",
        bookings=booking_list
    )


# --------------------------------------------------
# CANCEL BOOKING
# --------------------------------------------------

@app.route("/booking/<int:booking_id>/cancel", methods=["POST"])
def cancel_booking(booking_id):

    if not login_required():
        return redirect(url_for("login"))

    with get_db_connection() as connection:

        result = connection.execute("""
            UPDATE bookings
            SET status = 'Cancelled'
            WHERE id = ?
            AND user_id = ?
            AND status = 'Confirmed'
        """, (booking_id, session["user_id"]))

    if result.rowcount:
        flash("Your booking has been cancelled.", "success")
    else:
        flash("This booking could not be cancelled.", "error")

    return redirect(url_for("bookings"))


# --------------------------------------------------
# USER REGISTRATION
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email:
            flash("Please complete all fields.", "error")

        elif password != confirm:
            flash("Passwords do not match.", "error")

        elif len(password) < 8:
            flash("Use a password with at least 8 characters.", "error")

        else:
            try:
                with get_db_connection() as connection:

                    connection.execute("""
                        INSERT INTO users (name, email, password)
                        VALUES (?, ?, ?)
                    """, (
                        name,
                        email,
                        generate_password_hash(password)
                    ))

                flash(
                    "Account created. Sign in to continue.",
                    "success"
                )

                return redirect(url_for("login"))

            except sqlite3.IntegrityError:
                flash(
                    "An account with this email already exists.",
                    "error"
                )

    return render_template("register.html")


# --------------------------------------------------
# USER LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db_connection() as connection:

            user = connection.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()

        if user and check_password_hash(user["password"], password):

            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            return redirect(url_for("home"))

        flash(
            "The email or password you entered is incorrect.",
            "error"
        )

    return render_template("login.html")


# --------------------------------------------------
# USER LOGOUT
# --------------------------------------------------

@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    flash("You have been signed out.", "success")

    return redirect(url_for("login"))


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
