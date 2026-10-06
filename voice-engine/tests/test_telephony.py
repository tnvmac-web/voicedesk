"""Tests for telephony webhooks incl. missed-call text-back."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_inbound_call_returns_greeting(auth_client: TestClient) -> None:
    # Give the tenant a phone number so routing matches.
    me = auth_client.get("/api/auth/me").json()
    r = auth_client.post(
        "/telephony/voice",
        data={"From": "+15551112222", "To": "", "CallSid": "CA123"},
    )
    assert r.status_code == 200
    assert "Thank you for calling" in r.text
    assert me["name"] in r.text or "Test Dental" in r.text


def test_missed_call_triggers_textback(auth_client: TestClient) -> None:
    auth_client.post("/telephony/voice", data={"From": "+15551112222", "To": "", "CallSid": "CA999"})
    r = auth_client.post(
        "/telephony/status",
        data={
            "CallSid": "CA999",
            "CallStatus": "no-answer",
            "CallDuration": "0",
            "From": "+15551112222",
            "To": "",
        },
    )
    assert r.status_code == 200
    assert r.json()["textback_sent"] == "true"

    convs = auth_client.get("/api/conversations").json()
    assert len(convs) >= 1


def test_whatsapp_verify_handshake(client: TestClient) -> None:
    r = client.get(
        "/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.challenge": "42", "hub.verify_token": "voicedesk-verify"},
    )
    assert r.status_code == 200
    assert r.text == "42"


def test_whatsapp_inbound_stores_message(auth_client: TestClient) -> None:
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"from": "+15559998888", "text": {"body": "Do you have openings Friday?"}}
                            ]
                        }
                    }
                ]
            }
        ]
    }
    r = auth_client.post("/webhooks/whatsapp", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "received"

    convs = auth_client.get("/api/conversations").json()
    assert any(c["channel"] == "whatsapp" for c in convs)
    detail = auth_client.get(f"/api/conversations/{convs[0]['id']}").json()
    assert any("Friday" in m["body"] for m in detail["messages"])
