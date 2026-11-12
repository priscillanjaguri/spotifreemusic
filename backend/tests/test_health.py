from fastapi.testclient import TestClient

from app.main import app


def test_health_reports_database_ok(engine):
    client = TestClient(app)
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}


def test_openapi_docs_are_served(engine):
    client = TestClient(app)
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200
