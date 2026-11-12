
from contextlib import closing
from functools import wraps
import math

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import database


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
VEHICLE_STATUSES = ("available", "unavailable")


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))

        try:
            with closing(database.get_db_connection()) as connection:
                user = connection.execute(
                    "SELECT role FROM users WHERE id = ?",
                    (session["user_id"],),
                ).fetchone()
        except database.DatabaseError:
            current_app.logger.exception("Unable to verify admin access")
            return render_template(
                "database_error.html",
                status_code=503,
            ), 503

        if user is None:
            session.clear()
            return redirect(url_for("login"))

        if user["role"] != "admin":
            return render_template("admin_forbidden.html"), 403

        return view(*args, **kwargs)

    return wrapped_view


def _vehicle_form_data():
    return {
        "name": request.form.get("name", "").strip(),
        "type": request.form.get("type", "").strip(),
        "brand": request.form.get("brand", "").strip(),
        "model": request.form.get("model", "").strip(),
        "registration_number": request.form.get(
            "registration_number", ""
        ).strip(),
        "price_per_hour": request.form.get("price_per_hour", "").strip(),
        "status": request.form.get("status", "available").strip(),
        "image": request.form.get("image", "").strip(),
    }


def _validate_vehicle(vehicle):
    required_fields = (
        "name",
        "type",
        "brand",
        "model",
        "registration_number",
        "price_per_hour",
    )

    if any(not vehicle[field] for field in required_fields):
        return None, "All required vehicle fields must be filled in."

    if vehicle["status"] not in VEHICLE_STATUSES:
        return None, "Choose a valid vehicle status."

    try:
        price_per_hour = float(vehicle["price_per_hour"])
    except ValueError:
        return None, "Enter a valid hourly price greater than zero."

    if not math.isfinite(price_per_hour) or price_per_hour <= 0:
        return None, "Enter a valid hourly price greater than zero."

    cleaned = dict(vehicle)
    cleaned["price_per_hour"] = price_per_hour
    return cleaned, None


def _vehicle_not_found():
    return render_template(
        "admin_error.html",
        title="Vehicle not found",
        message="That vehicle does not exist or is no longer available.",
    ), 404


def _database_unavailable():
    current_app.logger.exception("Admin vehicle database operation failed")
    return render_template("database_error.html"), 503


@admin_bp.route("/", strict_slashes=False)
@admin_required
def dashboard():
    return render_template("admin_dashboard.html")


@admin_bp.route("/vehicles")
@admin_required
def vehicles():
    try:
        with closing(database.get_db_connection()) as connection:
            vehicle_list = connection.execute(
                "SELECT * FROM vehicles ORDER BY type, id"
            ).fetchall()
    except database.DatabaseError:
        return _database_unavailable()

    return render_template("admin_vehicles.html", vehicles=vehicle_list)


@admin_bp.route("/vehicles/new", methods=["GET", "POST"])
@admin_required
def add_vehicle():
    vehicle = {
        "name": "",
        "type": "",
        "brand": "",
        "model": "",
        "registration_number": "",
        "price_per_hour": "",
        "status": "available",
        "image": "",
    }

    if request.method == "POST":
        vehicle = _vehicle_form_data()
        cleaned, error = _validate_vehicle(vehicle)

        if error:
            return render_template(
                "admin_vehicle_form.html",
                vehicle=vehicle,
                statuses=VEHICLE_STATUSES,
                title="Add Vehicle",
                error=error,
            ), 400

        try:
            with closing(database.get_db_connection()) as connection:
                duplicate = connection.execute(
                    """
                    SELECT id FROM vehicles
                    WHERE LOWER(registration_number) = LOWER(?)
                    """,
                    (cleaned["registration_number"],),
                ).fetchone()

                if duplicate:
                    return render_template(
                        "admin_vehicle_form.html",
                        vehicle=vehicle,
                        statuses=VEHICLE_STATUSES,
                        title="Add Vehicle",
                        error="A vehicle with that registration number already exists.",
                    ), 400

                connection.execute(
                    """
                    INSERT INTO vehicles
                        (name, type, brand, model, registration_number,
                         price_per_hour, status, image)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cleaned["name"],
                        cleaned["type"],
                        cleaned["brand"],
                        cleaned["model"],
                        cleaned["registration_number"],
                        cleaned["price_per_hour"],
                        cleaned["status"],
                        cleaned["image"] or None,
                    ),
                )
                connection.commit()

        except database.IntegrityError:
            current_app.logger.info(
                "Vehicle creation rejected by a database constraint"
            )
            return render_template(
                "admin_vehicle_form.html",
                vehicle=vehicle,
                statuses=VEHICLE_STATUSES,
                title="Add Vehicle",
                error="A vehicle with that registration number already exists.",
            ), 400

        except database.DatabaseError:
            return _database_unavailable()

        flash("Vehicle added successfully.", "success")
        return redirect(url_for("admin.vehicles"))

    return render_template(
        "admin_vehicle_form.html",
        vehicle=vehicle,
        statuses=VEHICLE_STATUSES,
        title="Add Vehicle",
    )


@admin_bp.route("/vehicles/<int:vehicle_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_vehicle(vehicle_id):
    try:
        with closing(database.get_db_connection()) as connection:
            row = connection.execute(
                "SELECT * FROM vehicles WHERE id = ?",
                (vehicle_id,),
            ).fetchone()

    except database.DatabaseError:
        return _database_unavailable()

    if row is None:
        return _vehicle_not_found()

    vehicle = dict(row)

    if request.method == "POST":
        vehicle = _vehicle_form_data()
        cleaned, error = _validate_vehicle(vehicle)

        if error:
            return render_template(
                "admin_vehicle_form.html",
                vehicle=vehicle,
                statuses=VEHICLE_STATUSES,
                title="Edit Vehicle",
                error=error,
            ), 400

        try:
            with closing(database.get_db_connection()) as connection:
                duplicate = connection.execute(
                    """
                    SELECT id FROM vehicles
                    WHERE LOWER(registration_number) = LOWER(?) AND id != ?
                    """,
                    (cleaned["registration_number"], vehicle_id),
                ).fetchone()

                if duplicate:
                    return render_template(
                        "admin_vehicle_form.html",
                        vehicle=vehicle,
                        statuses=VEHICLE_STATUSES,
                        title="Edit Vehicle",
                        error="A vehicle with that registration number already exists.",
                    ), 400

                cursor = connection.execute(
                    """
                    UPDATE vehicles
                    SET name = ?, type = ?, brand = ?, model = ?,
                        registration_number = ?, price_per_hour = ?,
                        status = ?, image = ?
                    WHERE id = ?
                    """,
                    (
                        cleaned["name"],
                        cleaned["type"],
                        cleaned["brand"],
                        cleaned["model"],
                        cleaned["registration_number"],
                        cleaned["price_per_hour"],
                        cleaned["status"],
                        cleaned["image"] or None,
                        vehicle_id,
                    ),
                )

                if cursor.rowcount == 0:
                    return _vehicle_not_found()

                connection.commit()

        except database.IntegrityError:
            current_app.logger.info(
                "Vehicle update rejected by a database constraint"
            )
            return render_template(
                "admin_vehicle_form.html",
                vehicle=vehicle,
                statuses=VEHICLE_STATUSES,
                title="Edit Vehicle",
                error="A vehicle with that registration number already exists.",
            ), 400

        except database.DatabaseError:
            return _database_unavailable()

        flash("Vehicle updated successfully.", "success")
        return redirect(url_for("admin.vehicles"))

    return render_template(
        "admin_vehicle_form.html",
        vehicle=vehicle,
        statuses=VEHICLE_STATUSES,
        title="Edit Vehicle",
    )


@admin_bp.route("/vehicles/<int:vehicle_id>/status", methods=["POST"])
@admin_required
def change_vehicle_status(vehicle_id):
    status = request.form.get("status", "").strip()

    try:
        with closing(database.get_db_connection()) as connection:
            vehicle = connection.execute(
                "SELECT id FROM vehicles WHERE id = ?",
                (vehicle_id,),
            ).fetchone()

            if vehicle is None:
                return _vehicle_not_found()

            if status not in VEHICLE_STATUSES:
                flash("Choose a valid vehicle status.", "error")
                return redirect(url_for("admin.vehicles"))

            connection.execute(
                "UPDATE vehicles SET status = ? WHERE id = ?",
                (status, vehicle_id),
            )
            connection.commit()

    except database.DatabaseError:
        return _database_unavailable()

    flash("Vehicle status updated.", "success")
    return redirect(url_for("admin.vehicles"))


@admin_bp.route("/vehicles/<int:vehicle_id>/delete", methods=["POST"])
@admin_required
def delete_vehicle(vehicle_id):
    try:
        with closing(database.get_db_connection()) as connection:

            if database.is_postgres():
                connection.execute("BEGIN")
                connection.execute(
                    "SELECT id FROM vehicles WHERE id = ? FOR UPDATE",
                    (vehicle_id,),
                )
            else:
                connection.execute("BEGIN IMMEDIATE")

            vehicle = connection.execute(
                "SELECT id FROM vehicles WHERE id = ?",
                (vehicle_id,),
            ).fetchone()

            if vehicle is None:
                connection.rollback()
                return _vehicle_not_found()

            bookings = connection.execute(
                "SELECT 1 FROM bookings WHERE vehicle_id = ? LIMIT 1",
                (vehicle_id,),
            ).fetchone()

            if bookings:
                connection.rollback()
                flash(
                    "This vehicle has booking history and cannot be deleted.",
                    "error",
                )
                return redirect(url_for("admin.vehicles"))

            connection.execute(
                "DELETE FROM vehicles WHERE id = ?",
                (vehicle_id,),
            )
            connection.commit()

    except database.DatabaseError:
        return _database_unavailable()

    flash("Vehicle deleted successfully.", "success")
    return redirect(url_for("admin.vehicles"))
