"""Tests for auth, tenant scoping and the receptionist brain."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.receptionist import detect_intent


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_signup_login_and_me(client: TestClient) -> None:
    r = client.post(
        "/api/auth/signup",
        json={
            "business_name": "Acme Plumbing",
            "slug": "acme-plumbing",
            "vertical": "hvac",
            "email": "a@acme.com",
            "password": "secret12345",
        },
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]

    r2 = client.post(
        "/api/auth/login", json={"email": "a@acme.com", "password": "secret12345"}
    )
    assert r2.status_code == 200
    assert r2.json()["tenant_id"] == r.json()["tenant_id"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["slug"] == "acme-plumbing"


def test_duplicate_slug_rejected(client: TestClient) -> None:
    body = {
        "business_name": "X",
        "slug": "dup",
        "email": "x@x.com",
        "password": "password123",
    }
    assert client.post("/api/auth/signup", json=body).status_code == 201
    body["email"] = "y@y.com"
    assert client.post("/api/auth/signup", json=body).status_code == 409


def test_requires_auth(client: TestClient) -> None:
    assert client.get("/api/contacts").status_code == 401


def test_agent_default_created(auth_client: TestClient) -> None:
    r = auth_client.get("/api/agent")
    assert r.status_code == 200
    agents = r.json()
    assert len(agents) == 1
    assert agents[0]["name"] == "Receptionist"


def test_detect_intent() -> None:
    assert detect_intent("I want to book an appointment") == "booking"
    assert detect_intent("how much do you charge?") == "pricing"
    assert detect_intent("when are you open") == "hours"
    assert detect_intent("this is an emergency, water everywhere") == "emergency"
    assert detect_intent("can I speak to a real person") == "human_handoff"
    assert detect_intent("hello there") == "general"


def test_simulate_booking_creates_appointment(auth_client: TestClient) -> None:
    r = auth_client.post(
        "/api/calls/simulate",
        json={"tenant_slug": "test-dental", "text": "I'd like to book a cleaning at 3pm"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["intent"] == "booking"
    assert data["action"] == "appointment_created"

    appts = auth_client.get("/api/appointments").json()
    assert len(appts) == 1
    assert appts[0]["source"] == "voice"


def test_simulate_emergency_escalates(auth_client: TestClient) -> None:
    r = auth_client.post(
        "/api/calls/simulate",
        json={"tenant_slug": "test-dental", "text": "emergency! my tooth is broken"},
    )
    assert r.json()["intent"] == "emergency"
    assert r.json()["action"] == "human_handoff"


def test_analytics_summary(auth_client: TestClient) -> None:
    auth_client.post(
        "/api/calls/simulate", json={"tenant_slug": "test-dental", "text": "book me in"}
    )
    r = auth_client.get("/api/analytics/summary?avg_job_value=200")
    assert r.status_code == 200
    data = r.json()
    assert data["bookings"] >= 1
    assert data["estimated_revenue_recovered"] >= 200.0
