
from datetime import datetime
from math import ceil

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import database

booking_bp = Blueprint("booking", __name__)


@booking_bp.route("/book/<int:vehicle_id>", methods=["GET", "POST"])
def book_vehicle(vehicle_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = database.get_db_connection()
    

    vehicle = connection.execute(
        "SELECT * FROM vehicles WHERE id = ?",
        (vehicle_id,)
    ).fetchone()

    if not vehicle:
        connection.close()
        return "Vehicle not found", 404

    if request.method == "POST":
        start_value = request.form.get("start_time", "").strip()
        end_value = request.form.get("end_time", "").strip()

        try:
            start_time = datetime.strptime(start_value, "%Y-%m-%dT%H:%M")
            end_time = datetime.strptime(end_value, "%Y-%m-%dT%H:%M")
        except ValueError:
            connection.close()
            flash("Please enter valid start and end times.", "error")
            return redirect(url_for("booking.book_vehicle", vehicle_id=vehicle_id))

        now = datetime.now()

        if start_time < now or end_time <= start_time:
            connection.close()
            flash("Choose a future start time and an end time after the start.", "error")
            return redirect(url_for("booking.book_vehicle", vehicle_id=vehicle_id))

        overlap = connection.execute(
            """
            SELECT id FROM bookings
            WHERE vehicle_id = ?
              AND status = 'confirmed'
              AND start_time < ?
              AND end_time > ?
            """,
            (vehicle_id, end_value, start_value)
        ).fetchone()

        if overlap:
            connection.close()
            flash("This vehicle is already booked for that time.", "error")
            return redirect(url_for("booking.book_vehicle", vehicle_id=vehicle_id))

        hours = ceil((end_time - start_time).total_seconds() / 3600)
        total_price = hours * vehicle["price_per_hour"]

        connection.execute(
            """
            INSERT INTO bookings
                (user_id, vehicle_id, start_time, end_time, total_price)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                vehicle_id,
                start_value,
                end_value,
                total_price
            )
        )

        connection.commit()
        connection.close()

        flash(f"Booking confirmed. Total cost: Rs. {total_price:.2f}", "success")
        return redirect(url_for("booking.my_bookings"))

    connection.close()
    return render_template("book_vehicle.html", vehicle=vehicle)


@booking_bp.route("/my-bookings")
def my_bookings():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = database.get_db_connection()

    bookings = connection.execute(
        """
        SELECT bookings.*, vehicles.brand, vehicles.name, vehicles.registration_number
        FROM bookings
        JOIN vehicles ON bookings.vehicle_id = vehicles.id
        WHERE bookings.user_id = ?
        ORDER BY bookings.created_at DESC
        """,
        (session["user_id"],)
    ).fetchall()

    connection.close()

    return render_template("my_bookings.html", bookings=bookings)


@booking_bp.route("/cancel-booking/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = database.get_db_connection()

    booking = connection.execute(
        """
        SELECT id FROM bookings
        WHERE id = ? AND user_id = ? AND status = 'confirmed'
        """,
        (booking_id, session["user_id"])
    ).fetchone()

    if not booking:
        connection.close()
        flash("Booking not found or already cancelled.", "error")
        return redirect(url_for("booking.my_bookings"))

    connection.execute(
        "UPDATE bookings SET status = 'cancelled' WHERE id = ?",
        (booking_id,)
    )

    connection.commit()
    connection.close()

    flash("Booking cancelled successfully.", "success")
    return redirect(url_for("vehicles"))
