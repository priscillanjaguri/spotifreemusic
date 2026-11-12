from sqlalchemy import select

from app.models import User
from tests.conftest import register


def test_register_logs_in_and_never_stores_plaintext(client, db):
    res = register(client)
    assert res.status_code == 201
    assert "password" not in res.json()
    assert client.get("/api/v1/auth/me").json()["email"] == "ada@example.com"
    stored = db.scalar(select(User.password_hash).where(User.email == "ada@example.com"))
    assert stored.startswith("$argon2id$") and "correct-horse" not in stored


def test_session_cookie_is_httponly_and_samesite(client):
    cookie = register(client).headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_duplicate_email_any_case_is_rejected(client):
    register(client, "Ada@Example.com")
    assert register(client, "ada@example.com").status_code == 409


def test_weak_or_invalid_input_is_rejected(client):
    assert register(client, password="short").status_code == 422
    assert register(client, email="not-an-email").status_code == 422


def test_login_logout_flow(client):
    register(client)
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401
    bad = client.post("/api/v1/auth/login", json={"email": "ada@example.com", "password": "wrong-password"})
    assert bad.status_code == 401
    unknown = client.post("/api/v1/auth/login", json={"email": "who@example.com", "password": "wrong-password"})
    assert unknown.status_code == 401 and unknown.json() == bad.json()  # no account enumeration
    ok = client.post("/api/v1/auth/login", json={"email": "ADA@example.com", "password": "correct-horse-battery"})
    assert ok.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200


def test_tampered_cookie_is_rejected(client):
    register(client)
    client.cookies.set("tunewise_session", "garbage.token.value")
    assert client.get("/api/v1/auth/me").status_code == 401


def test_profile_and_preferences(client):
    register(client)
    assert client.patch("/api/v1/profile", json={"display_name": "Ada L."}).json()["display_name"] == "Ada L."
    prefs = client.patch("/api/v1/profile/preferences", json={"timezone": "Africa/Nairobi", "week_starts_on": 6})
    assert prefs.status_code == 200 and prefs.json()["timezone"] == "Africa/Nairobi"
    assert client.patch("/api/v1/profile/preferences", json={"timezone": "Mars/Base"}).status_code == 422
    assert client.patch("/api/v1/profile/preferences", json={"short_term_days": 400}).status_code == 422  # field limit
    # Cross-field rule: the short-term window must stay shorter than the long-term one (default 365).
    assert client.patch("/api/v1/profile/preferences", json={"short_term_days": 365}).status_code == 422
    assert client.get("/api/v1/profile/preferences").json()["short_term_days"] == 28  # rejected change not applied
    assert client.patch("/api/v1/profile/preferences", json={"short_term_days": 300}).status_code == 200


def test_delete_account_requires_password_and_removes_everything(client, db):
    from app.models import User, UserCollection
    register(client)
    song_id = client.get("/api/v1/songs/search?q=night").json()["results"][0]["id"]
    client.post("/api/v1/collection", json={"song_id": song_id})
    assert client.request("DELETE", "/api/v1/profile", json={"password": "wrong-password"}).status_code == 403
    assert client.request("DELETE", "/api/v1/profile", json={"password": "correct-horse-battery"}).status_code == 204
    assert db.query(User).count() == 0 and db.query(UserCollection).count() == 0
    assert client.get("/api/v1/auth/me").status_code == 401
