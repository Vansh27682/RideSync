from datetime import datetime, timedelta

import app as ridesync
import pytest


@pytest.fixture
def admin_clients(tmp_path, monkeypatch):
    monkeypatch.setattr(
        ridesync,
        "DATABASE",
        str(tmp_path / "test_admin.db"),
    )
    ridesync.app.config["TESTING"] = True
    ridesync.init_db()

    connection = ridesync.get_db_connection()
    connection.executemany(
        """
        INSERT INTO users (name, username, email, password, role)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            ("Admin User", "admin", "admin@example.com", "unused", "admin"),
            ("Student User", "student", "student@example.com", "unused", "student"),
        ],
    )
    connection.execute(
        """
        INSERT INTO vehicles
            (name, type, brand, model, registration_number,
             price_per_hour, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("Activa", "Scooter", "Honda", "Activa 6G", "TEST-001", 100, "available"),
    )
    connection.commit()
    connection.close()

    def authenticated_client(user_id, name, role):
        client = ridesync.app.test_client()
        with client.session_transaction() as user_session:
            user_session["user_id"] = user_id
            user_session["user_name"] = name
            user_session["role"] = role
        return client

    return {
        "anonymous": ridesync.app.test_client(),
        "admin": authenticated_client(1, "Admin User", "admin"),
        "student": authenticated_client(2, "Student User", "student"),
    }


def vehicle_form(**overrides):
    data = {
        "name": "Activa",
        "type": "Scooter",
        "brand": "Honda",
        "model": "Activa 6G",
        "registration_number": "TEST-002",
        "price_per_hour": "125.50",
        "status": "available",
        "image": "",
    }
    data.update(overrides)
    return data


def test_admin_routes_redirect_logged_out_users(admin_clients):
    response = admin_clients["anonymous"].get("/admin")

    assert response.status_code == 302
    assert "/login" in response.location


def test_student_cannot_access_admin_routes(admin_clients):
    client = admin_clients["student"]

    assert client.get("/admin").status_code == 403
    assert client.get("/admin/vehicles").status_code == 403
    response = client.post(
        "/admin/vehicles/new",
        data=vehicle_form(),
    )
    assert response.status_code == 403

    connection = ridesync.get_db_connection()
    count = connection.execute(
        "SELECT COUNT(*) FROM vehicles"
    ).fetchone()[0]
    connection.close()
    assert count == 1


def test_admin_dashboard_and_vehicle_list(admin_clients):
    client = admin_clients["admin"]

    dashboard = client.get("/admin")
    listing = client.get("/admin/vehicles")

    assert dashboard.status_code == 200
    assert b"Vehicle Management" in dashboard.data
    assert b"Logout" in dashboard.data
    assert listing.status_code == 200
    assert b"TEST-001" in listing.data
    assert b"Add vehicle" in listing.data


def test_admin_can_add_vehicle_and_reject_invalid_or_duplicate_data(admin_clients):
    client = admin_clients["admin"]

    response = client.post("/admin/vehicles/new", data=vehicle_form())
    assert response.status_code == 302
    assert "/admin/vehicles" in response.location

    connection = ridesync.get_db_connection()
    created = connection.execute(
        "SELECT * FROM vehicles WHERE registration_number = ?",
        ("TEST-002",),
    ).fetchone()
    connection.close()
    assert created is not None
    assert created["price_per_hour"] == 125.5

    for data, expected_message in (
        ({}, b"All required vehicle fields"),
        (vehicle_form(price_per_hour="0"), b"hourly price"),
        (vehicle_form(price_per_hour="not-a-price"), b"hourly price"),
        (vehicle_form(status="maintenance"), b"valid vehicle status"),
        (
            vehicle_form(registration_number="test-001"),
            b"registration number already exists",
        ),
    ):
        response = client.post("/admin/vehicles/new", data=data)
        assert response.status_code == 400
        assert expected_message in response.data
        assert b"sqlite" not in response.data.lower()


def test_admin_can_edit_vehicle(admin_clients):
    response = admin_clients["admin"].post(
        "/admin/vehicles/1/edit",
        data=vehicle_form(
            name="Updated Activa",
            registration_number="TEST-001",
            price_per_hour="140",
            status="unavailable",
        ),
    )

    assert response.status_code == 302
    connection = ridesync.get_db_connection()
    vehicle = connection.execute(
        "SELECT name, price_per_hour, status FROM vehicles WHERE id = 1"
    ).fetchone()
    connection.close()
    assert vehicle["name"] == "Updated Activa"
    assert vehicle["price_per_hour"] == 140
    assert vehicle["status"] == "unavailable"


def test_admin_can_change_vehicle_status_and_invalid_status_is_rejected(admin_clients):
    client = admin_clients["admin"]

    response = client.post(
        "/admin/vehicles/1/status",
        data={"status": "unavailable"},
    )
    assert response.status_code == 302

    response = client.post(
        "/admin/vehicles/1/status",
        data={"status": "maintenance"},
    )
    assert response.status_code == 302

    connection = ridesync.get_db_connection()
    status = connection.execute(
        "SELECT status FROM vehicles WHERE id = 1"
    ).fetchone()["status"]
    connection.close()
    assert status == "unavailable"


def test_admin_can_delete_vehicle_without_booking_history(admin_clients):
    response = admin_clients["admin"].post("/admin/vehicles/1/delete")

    assert response.status_code == 302
    connection = ridesync.get_db_connection()
    vehicle = connection.execute(
        "SELECT id FROM vehicles WHERE id = 1"
    ).fetchone()
    connection.close()
    assert vehicle is None


def test_admin_cannot_delete_vehicle_with_booking_history(admin_clients):
    connection = ridesync.get_db_connection()
    connection.execute(
        """
        INSERT INTO bookings
            (user_id, vehicle_id, start_time, end_time, total_price)
        VALUES (?, ?, ?, ?, ?)
        """,
        (2, 1, "2030-01-01T10:00", "2030-01-01T11:00", 100),
    )
    connection.commit()
    connection.close()

    response = admin_clients["admin"].post("/admin/vehicles/1/delete")
    assert response.status_code == 302

    connection = ridesync.get_db_connection()
    vehicle = connection.execute(
        "SELECT id FROM vehicles WHERE id = 1"
    ).fetchone()
    booking = connection.execute(
        "SELECT id FROM bookings WHERE vehicle_id = 1"
    ).fetchone()
    connection.close()
    assert vehicle is not None
    assert booking is not None


def test_invalid_vehicle_ids_are_handled_as_not_found(admin_clients):
    client = admin_clients["admin"]

    assert client.get("/admin/vehicles/999/edit").status_code == 404
    assert client.get("/admin/vehicles/not-an-id/edit").status_code == 404
    assert client.post(
        "/admin/vehicles/999/status",
        data={"status": "available"},
    ).status_code == 404
    assert client.post("/admin/vehicles/999/delete").status_code == 404


def test_student_can_still_list_and_book_available_vehicles(admin_clients):
    client = admin_clients["student"]

    listing = client.get("/vehicles")
    assert listing.status_code == 200
    assert b"TEST-001" in listing.data

    start_time = datetime.now() + timedelta(days=2)
    end_time = start_time + timedelta(hours=1)
    response = client.post(
        "/book/1",
        data={
            "start_time": start_time.strftime("%Y-%m-%dT%H:%M"),
            "end_time": end_time.strftime("%Y-%m-%dT%H:%M"),
        },
    )
    assert response.status_code == 302

    connection = ridesync.get_db_connection()
    booking = connection.execute(
        "SELECT vehicle_id, user_id, status FROM bookings"
    ).fetchone()
    connection.close()
    assert booking["vehicle_id"] == 1
    assert booking["user_id"] == 2
    assert booking["status"] == "confirmed"


def test_student_cannot_book_unavailable_vehicle_by_direct_url(admin_clients):
    connection = ridesync.get_db_connection()
    connection.execute(
        "UPDATE vehicles SET status = 'unavailable' WHERE id = 1"
    )
    connection.commit()
    connection.close()

    response = admin_clients["student"].get("/book/1")

    assert response.status_code == 302
    assert "/vehicles" in response.location
    connection = ridesync.get_db_connection()
    count = connection.execute(
        "SELECT COUNT(*) FROM bookings"
    ).fetchone()[0]
    connection.close()
    assert count == 0
