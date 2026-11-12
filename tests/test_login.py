
import pytest
import app as ridesync
import sqlite3
from werkzeug.security import generate_password_hash


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_path = tmp_path / "test.db"

    monkeypatch.setattr(ridesync, "DATABASE", str(database_path))

    ridesync.app.config["TESTING"] = True

    ridesync.init_db()

    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        INSERT INTO users (name, email, password, role)
        VALUES (?, ?, ?, ?)
        """,
        (
            "Test User",
            "login_test@example.com",
            generate_password_hash("TestPass123!"),
            "user",
        ),
    )
    connection.commit()
    connection.close()

    with ridesync.app.test_client() as test_client:
        yield test_client


def test_login_with_valid_credentials(client):
    response = client.post(
        "/login",
        data={
            "identifier": "login_test@example.com",
            "password": "TestPass123!",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_login_with_wrong_password(client):
    response = client.post(
        "/login",
        data={
            "identifier": "login_test@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 200
    assert b"Invalid email or password." in response.data


def test_login_with_unknown_email(client):
    response = client.post(
        "/login",
        data={
            "identifier": "unknown@example.com",
            "password": "TestPass123!",
        },
    )

    assert response.status_code == 200
    assert b"Invalid email or password." in response.data


def test_successful_login_creates_session(client):
    response = client.post(
        "/login",
        data={
            "identifier": "login_test@example.com",
            "password": "TestPass123!",
        },
    )

    assert response.status_code == 302

    with client.session_transaction() as session:
        assert session["user_name"] == "Test User"
        assert session["role"] == "user"
