
from datetime import datetime, timedelta

import pytest
import app as ridesync


@pytest.fixture
def booking_client(tmp_path, monkeypatch):
    monkeypatch.setattr(
        ridesync, "DATABASE", str(tmp_path / "test_booking.db")
    )

    ridesync.init_db()

    connection = ridesync.get_db_connection()

    connection.execute(
        """
        INSERT INTO users (name, username, email, phone, password, role)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("Test User", "testuser", "test@example.com", "+919876543210", "testpass", "student"),
    )

    connection.execute(
        """
        INSERT INTO vehicles
            (name, type, brand, model, registration_number, price_per_hour, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("Activa", "Scooter", "Honda", "Activa 6G", "TEST-001", 100, "available"),
    )

    connection.commit()
    connection.close()

    client = ridesync.app.test_client()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_name"] = "Test User"
        session["role"] = "student"

    return client


def test_booking_page_loads(booking_client):
    response = booking_client.get("/book/1")

    assert response.status_code == 200
    assert b"Book Your Vehicle" in response.data


def test_booking_requires_login():
    client = ridesync.app.test_client()

    response = client.get("/book/1")

    assert response.status_code == 302
    assert "/login" in response.location


def test_successful_booking(booking_client):
    start_time = datetime.now() + timedelta(days=2)
    end_time = start_time + timedelta(hours=2)

    response = booking_client.post(
        "/book/1",
        data={
            "start_time": start_time.strftime("%Y-%m-%dT%H:%M"),
            "end_time": end_time.strftime("%Y-%m-%dT%H:%M"),
        },
    )

    assert response.status_code == 302

    connection = ridesync.get_db_connection()
    booking = connection.execute(
        "SELECT * FROM bookings WHERE user_id = 1"
    ).fetchone()
    connection.close()

    assert booking is not None
    assert booking["vehicle_id"] == 1
    assert booking["total_price"] == 200
    assert booking["status"] == "confirmed"


def test_booking_rejects_end_before_start(booking_client):
    start_time = datetime.now() + timedelta(days=2)
    end_time = start_time - timedelta(hours=1)

    booking_client.post(
        "/book/1",
        data={
            "start_time": start_time.strftime("%Y-%m-%dT%H:%M"),
            "end_time": end_time.strftime("%Y-%m-%dT%H:%M"),
        },
    )

    connection = ridesync.get_db_connection()
    count = connection.execute(
        "SELECT COUNT(*) FROM bookings"
    ).fetchone()[0]
    connection.close()

    assert count == 0


def test_overlapping_booking_is_rejected(booking_client):
    start_time = datetime.now() + timedelta(days=2)
    end_time = start_time + timedelta(hours=2)

    connection = ridesync.get_db_connection()
    connection.execute(
        """
        INSERT INTO bookings
            (user_id, vehicle_id, start_time, end_time, total_price)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            1,
            1,
            start_time.strftime("%Y-%m-%dT%H:%M"),
            end_time.strftime("%Y-%m-%dT%H:%M"),
            200,
        ),
    )
    connection.commit()
    connection.close()

    response = booking_client.post(
        "/book/1",
        data={
            "start_time": (start_time + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
            "end_time": (end_time + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
        },
    )

    assert response.status_code == 302

    connection = ridesync.get_db_connection()
    count = connection.execute(
        "SELECT COUNT(*) FROM bookings"
    ).fetchone()[0]
    connection.close()

    assert count == 1


def test_user_cannot_cancel_another_users_booking(booking_client):
    connection = ridesync.get_db_connection()

    connection.execute(
        """
        INSERT INTO users (name, username, email, phone, password, role)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("Other User", "otheruser", "other@example.com", "+919876543211", "testpass", "student"),
    )

    start_time = datetime.now() + timedelta(days=2)
    end_time = start_time + timedelta(hours=2)

    connection.execute(
        """
        INSERT INTO bookings
            (user_id, vehicle_id, start_time, end_time, total_price)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            2,
            1,
            start_time.strftime("%Y-%m-%dT%H:%M"),
            end_time.strftime("%Y-%m-%dT%H:%M"),
            200,
        ),
    )

    connection.commit()
    connection.close()

    response = booking_client.post("/cancel-booking/1")

    assert response.status_code == 302

    connection = ridesync.get_db_connection()
    booking = connection.execute(
        "SELECT status FROM bookings WHERE id = 1"
    ).fetchone()
    connection.close()

    assert booking["status"] == "confirmed"
