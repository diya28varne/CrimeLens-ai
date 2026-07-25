"""Health live endpoint unit test (no external deps)."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_live() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-Id" in response.headers
