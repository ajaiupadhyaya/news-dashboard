import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import login, require_auth
from app.main import app

client = TestClient(app)


def test_login_returns_open_token_when_unconfigured(monkeypatch):
    monkeypatch.delenv("DASHBOARD_TOKEN", raising=False)
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    assert login("anything") == "open"


def test_login_rejects_wrong_password(monkeypatch):
    monkeypatch.setenv("DASHBOARD_PASSWORD", "secret")
    monkeypatch.setenv("DASHBOARD_TOKEN", "tok-1")
    with pytest.raises(HTTPException) as exc:
        login("wrong")
    assert exc.value.status_code == 401


def test_login_returns_token_on_correct_password(monkeypatch):
    monkeypatch.setenv("DASHBOARD_PASSWORD", "secret")
    monkeypatch.setenv("DASHBOARD_TOKEN", "tok-1")
    assert login("secret") == "tok-1"


def test_require_auth_passes_when_disabled(monkeypatch):
    monkeypatch.delenv("DASHBOARD_TOKEN", raising=False)
    require_auth(authorization=None)  # must not raise


def test_require_auth_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "tok-1")
    with pytest.raises(HTTPException) as exc:
        require_auth(authorization=None)
    assert exc.value.status_code == 401


def test_require_auth_accepts_valid_token(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "tok-1")
    require_auth(authorization="Bearer tok-1")  # must not raise


def test_login_route_and_status(monkeypatch):
    monkeypatch.setenv("DASHBOARD_PASSWORD", "secret")
    monkeypatch.setenv("DASHBOARD_TOKEN", "tok-1")
    resp = client.post("/api/auth/login", json={"password": "secret"})
    assert resp.status_code == 200
    assert resp.json() == {"token": "tok-1"}
    status = client.get("/api/auth/status")
    assert status.json() == {"auth_enabled": True}


def test_login_rejects_half_configured_auth(monkeypatch):
    monkeypatch.setenv("DASHBOARD_TOKEN", "tok-1")
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    with pytest.raises(HTTPException) as exc:
        login("anything")
    assert exc.value.status_code == 500
