import json

from fastapi.testclient import TestClient

from app.main import app
from app.logging_config import JsonFormatter, request_id_ctx

client = TestClient(app)


def test_response_has_request_id_header():
    resp = client.get("/health")
    assert resp.headers.get("X-Request-ID")


def test_request_id_echoed_when_supplied():
    resp = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert resp.headers["X-Request-ID"] == "abc123"


def test_json_formatter_emits_request_id():
    import logging

    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", None, None)
    token = request_id_ctx.set("rid-9")
    try:
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_ctx.reset(token)
    assert payload["message"] == "hello"
    assert payload["request_id"] == "rid-9"
    assert payload["level"] == "INFO"
