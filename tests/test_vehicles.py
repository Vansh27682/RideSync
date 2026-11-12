import app as ridesync


def test_vehicles_redirects_when_not_logged_in():
    ridesync.app.config["TESTING"] = True

    client = ridesync.app.test_client()
    response = client.get("/vehicles", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]