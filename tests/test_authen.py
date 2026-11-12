
import app as ridesync


def setup_test_database(tmp_path, monkeypatch):
    database_path = tmp_path / "test_ridesync.db"
    monkeypatch.setattr(ridesync, "DATABASE", str(database_path))
    ridesync.init_db()
    ridesync.app.config["TESTING"] = True

    return ridesync.app.test_client()


def registration_data(role="customer", admin_code=""):
    return {
        "name": "Test User",
        "username": "testuser123",
        "email": "testuser@example.com",
        "phone": "9876543210",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "role": role,
        "admin_code": admin_code,
    }


def test_login_page_loads():
    ridesync.app.config["TESTING"] = True

    client = ridesync.app.test_client()
    response = client.get("/login")

    assert response.status_code == 200


def test_register_page_loads():
    ridesync.app.config["TESTING"] = True

    client = ridesync.app.test_client()
    response = client.get("/register")

    assert response.status_code == 200


def test_register_rejects_empty_form():
    ridesync.app.config["TESTING"] = True

    client = ridesync.app.test_client()
    response = client.post("/register", data={})

    assert response.status_code == 200
    assert b"All fields are required." in response.data


def test_successful_registration(tmp_path, monkeypatch):
    client = setup_test_database(tmp_path, monkeypatch)

    response = client.post(
        "/register",
        data=registration_data(),
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    connection = ridesync.get_db_connection()
    user = connection.execute(
        "SELECT username, email, phone, password, role FROM users "
        "WHERE username = ?",
        ("testuser123",),
    ).fetchone()
    connection.close()

    assert user is not None
    assert user["email"] == "testuser@example.com"
    assert user["phone"] == "+919876543210"
    assert user["role"] == "customer"
    assert ridesync.check_password_hash(
        user["password"], "TestPass123!"
    )


def test_successful_admin_registration(tmp_path, monkeypatch):
    client = setup_test_database(tmp_path, monkeypatch)
    monkeypatch.setenv("RIDESYNC_ADMIN_CODE", "TestAdmin@123")

    response = client.post(
        "/register",
        data=registration_data("admin", "TestAdmin@123"),
        follow_redirects=False,
    )

    assert response.status_code == 302

    connection = ridesync.get_db_connection()
    user = connection.execute(
        "SELECT role FROM users WHERE username = ?",
        ("testuser123",),
    ).fetchone()
    connection.close()

    assert user is not None
    assert user["role"] == "admin"


def test_admin_registration_rejects_wrong_code(tmp_path, monkeypatch):
    client = setup_test_database(tmp_path, monkeypatch)
    monkeypatch.setenv("RIDESYNC_ADMIN_CODE", "TestAdmin@123")

    response = client.post(
        "/register",
        data=registration_data("admin", "WrongCode123"),
    )

    assert response.status_code == 200
    assert b"Invalid admin registration code." in response.data

    connection = ridesync.get_db_connection()
    user = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        ("testuser123",),
    ).fetchone()
    connection.close()

    assert user is None


def test_admin_registration_rejected_when_secret_missing(tmp_path, monkeypatch):
    client = setup_test_database(tmp_path, monkeypatch)
    monkeypatch.delenv("RIDESYNC_ADMIN_CODE", raising=False)

    response = client.post(
        "/register",
        data=registration_data("admin", "TestAdmin@123"),
    )

    assert response.status_code == 200
    assert b"Admin registration is currently unavailable." in response.data


def test_invalid_role_is_rejected(tmp_path, monkeypatch):
    client = setup_test_database(tmp_path, monkeypatch)

    response = client.post(
        "/register",
        data=registration_data("superadmin"),
    )

    assert response.status_code == 200
    assert b"Invalid account type selected." in response.data


def test_admin_registration_rejects_empty_code(tmp_path, monkeypatch):
    client = setup_test_database(tmp_path, monkeypatch)
    monkeypatch.setenv("RIDESYNC_ADMIN_CODE", "TestAdmin@123")

    response = client.post(
        "/register",
        data=registration_data("admin", ""),
    )

    assert response.status_code == 200
    assert b"Invalid admin registration code." in response.data
