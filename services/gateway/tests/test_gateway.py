"""Integration tests for NIYAM Gateway API endpoints."""
import pytest
import hmac
import hashlib
import json
from fastapi.testclient import TestClient
from services.gateway.main import app

client = TestClient(app)


def test_gateway_health_and_metrics():
    """Verify gateway metrics endpoint returns compliance stats."""
    res = client.get("/audit/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "total_evaluations" in data
    assert "compliance_rate" in data
    assert data["zero_unrecorded_failures"] is True


def test_csv_audit_export():
    """Verify CSV export endpoint returns RFC-4180 CSV with headers."""
    res = client.get("/audit/export?format=csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "attachment; filename=" in res.headers.get("content-disposition", "")
    content = res.text
    assert "Timestamp,Log ID,Agent ID,User ID,Action" in content


def test_chaos_toggle_lifecycle():
    """Verify chaos mode toggle sets circuit state to OPEN and restores to CLOSED."""
    # Toggle on
    res_on = client.post("/chaos/toggle", json={"enabled": True})
    assert res_on.status_code == 200
    assert res_on.json()["chaos_mode"] is True

    # Check status
    res_status = client.get("/chaos/status")
    assert res_status.status_code == 200
    assert res_status.json()["chaos_mode"] is True

    # Toggle off (restore)
    res_off = client.post("/chaos/toggle", json={"enabled": False})
    assert res_off.status_code == 200
    assert res_off.json()["chaos_mode"] is False


def test_razorpay_webhook_hmac_verification():
    """Verify Razorpay webhook processes valid HMAC-SHA256 signatures."""
    webhook_secret = "test_webhook_secret_key_892374".encode("utf-8")
    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_webhook_12345",
                    "amount": 45000,
                    "currency": "INR",
                    "status": "captured",
                    "notes": {
                        "agent_id": "agent_shopper_01",
                        "user_id": "usr_rahul_982"
                    }
                }
            }
        }
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    valid_signature = hmac.new(webhook_secret, body_bytes, hashlib.sha256).hexdigest()

    # Valid signature
    res = client.post(
        "/webhooks/razorpay",
        content=body_bytes,
        headers={"X-Razorpay-Signature": valid_signature, "Content-Type": "application/json"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["event"] == "payment.captured"

    # Invalid signature should be rejected with 400
    res_invalid = client.post(
        "/webhooks/razorpay",
        content=body_bytes,
        headers={"X-Razorpay-Signature": "tampered_signature_hex", "Content-Type": "application/json"}
    )
    assert res_invalid.status_code == 400
