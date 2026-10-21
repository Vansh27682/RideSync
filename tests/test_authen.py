import app as ridesync


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
    database_path = tmp_path / "test_ridesync.db"
    monkeypatch.setattr(ridesync, "DATABASE", str(database_path))

    ridesync.init_db()
    ridesync.app.config["TESTING"] = True

    client = ridesync.app.test_client()
    response = client.post(
        "/register",
        data={
            "name": "Test User",
            "username": "testuser123",
            "email": "testuser@example.com",
            "phone": "9876543210",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    connection = ridesync.get_db_connection()
    user = connection.execute(
        "SELECT username, email, phone, password_hash FROM users "
        "WHERE username = ?",
        ("testuser123",),
    ).fetchone()
    connection.close()

    assert user is not None
    assert user["email"] == "testuser@example.com"
    assert user["phone"] == "+919876543210"
    assert ridesync.check_password_hash(
        user["password_hash"], "TestPass123!"
    )