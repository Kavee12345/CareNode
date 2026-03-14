"""Tests for /api/v1/health/* endpoints."""
import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


TIMELINE_URL = "/api/v1/health/timeline"
EVENTS_URL = "/api/v1/health/events"
RX_URL = "/api/v1/health/prescriptions"


def event_payload(**overrides) -> dict:
    base = {
        "event_type": "symptom",
        "title": "Headache",
        "event_date": str(date.today()),
    }
    base.update(overrides)
    return base


def rx_payload(**overrides) -> dict:
    base = {"medication_name": "Ibuprofen", "dosage": "400mg", "frequency": "twice daily"}
    base.update(overrides)
    return base


# ── Timeline ──────────────────────────────────────────────────────────────────

class TestTimeline:
    async def test_timeline_empty(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.get(TIMELINE_URL, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_timeline_shows_own_events(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        await client.post(EVENTS_URL, json=event_payload(title="Fever"), headers=headers)
        await client.post(EVENTS_URL, json=event_payload(title="Fatigue"), headers=headers)

        resp = await client.get(TIMELINE_URL, headers=headers)
        titles = [e["title"] for e in resp.json()]
        assert "Fever" in titles
        assert "Fatigue" in titles

    async def test_timeline_filter_by_event_type(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        await client.post(EVENTS_URL, json=event_payload(event_type="symptom", title="Cough"), headers=headers)
        await client.post(EVENTS_URL, json=event_payload(event_type="lab_result", title="CBC"), headers=headers)

        resp = await client.get(f"{TIMELINE_URL}?event_type=symptom", headers=headers)
        types = [e["event_type"] for e in resp.json()]
        assert all(t == "symptom" for t in types)
        titles = [e["title"] for e in resp.json()]
        assert "Cough" in titles
        assert "CBC" not in titles

    async def test_timeline_filter_by_date_range(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        today = date.today()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)

        await client.post(
            EVENTS_URL,
            json=event_payload(title="Recent", event_date=str(today)),
            headers=headers,
        )
        await client.post(
            EVENTS_URL,
            json=event_payload(title="Old", event_date=str(last_week)),
            headers=headers,
        )

        resp = await client.get(
            f"{TIMELINE_URL}?start_date={yesterday}",
            headers=headers,
        )
        titles = [e["title"] for e in resp.json()]
        assert "Recent" in titles
        assert "Old" not in titles

    async def test_timeline_limit(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        for i in range(5):
            await client.post(EVENTS_URL, json=event_payload(title=f"Event {i}"), headers=headers)

        resp = await client.get(f"{TIMELINE_URL}?limit=3", headers=headers)
        assert len(resp.json()) <= 3

    async def test_timeline_requires_auth(self, client: AsyncClient):
        resp = await client.get(TIMELINE_URL)
        assert resp.status_code == 403

    async def test_timeline_does_not_show_other_users_events(
        self, client: AsyncClient, auth_headers
    ):
        headers_a, _, __ = auth_headers

        email_b = f"b_{uuid.uuid4().hex[:6]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email_b, "password": "Pass123!"})
        login_b = await client.post("/api/v1/auth/login", json={"email": email_b, "password": "Pass123!"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        await client.post(
            EVENTS_URL, json=event_payload(title="User B Secret Event"), headers=headers_b
        )

        resp = await client.get(TIMELINE_URL, headers=headers_a)
        titles = [e["title"] for e in resp.json()]
        assert "User B Secret Event" not in titles


# ── Health Events ─────────────────────────────────────────────────────────────

class TestHealthEvents:
    async def test_create_event_success(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        resp = await client.post(
            EVENTS_URL,
            json=event_payload(
                event_type="lab_result",
                title="Blood glucose",
                description="Fasting glucose 95 mg/dL",
                severity="low",
            ),
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Blood glucose"
        assert data["event_type"] == "lab_result"
        assert "id" in data

    async def test_create_event_minimal_fields(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        resp = await client.post(
            EVENTS_URL,
            json={"event_type": "symptom", "title": "Nausea", "event_date": str(date.today())},
            headers=headers,
        )
        assert resp.status_code == 201

    async def test_create_event_requires_auth(self, client: AsyncClient):
        resp = await client.post(EVENTS_URL, json=event_payload())
        assert resp.status_code == 403

    async def test_delete_event_success(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        create_resp = await client.post(EVENTS_URL, json=event_payload(), headers=headers)
        event_id = create_resp.json()["id"]

        resp = await client.delete(f"{EVENTS_URL}/{event_id}", headers=headers)
        assert resp.status_code == 204

        # Should no longer appear in timeline
        timeline_resp = await client.get(TIMELINE_URL, headers=headers)
        ids = [e["id"] for e in timeline_resp.json()]
        assert event_id not in ids

    async def test_delete_nonexistent_event(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.delete(f"{EVENTS_URL}/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    async def test_cannot_delete_other_users_event(self, client: AsyncClient, auth_headers):
        headers_a, _, __ = auth_headers

        email_b = f"b_{uuid.uuid4().hex[:6]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email_b, "password": "Pass123!"})
        login_b = await client.post("/api/v1/auth/login", json={"email": email_b, "password": "Pass123!"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        create_resp = await client.post(EVENTS_URL, json=event_payload(), headers=headers_b)
        event_id = create_resp.json()["id"]

        resp = await client.delete(f"{EVENTS_URL}/{event_id}", headers=headers_a)
        assert resp.status_code == 404


# ── Prescriptions ─────────────────────────────────────────────────────────────

class TestPrescriptions:
    async def test_list_prescriptions_empty(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.get(RX_URL, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_prescription_success(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        resp = await client.post(RX_URL, json=rx_payload(), headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["medication_name"] == "Ibuprofen"
        assert data["status"] == "active"
        assert "id" in data

    async def test_create_prescription_minimal(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.post(RX_URL, json={"medication_name": "Aspirin"}, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["medication_name"] == "Aspirin"

    async def test_list_prescriptions_shows_created(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        await client.post(RX_URL, json=rx_payload(medication_name="Metformin"), headers=headers)
        await client.post(RX_URL, json=rx_payload(medication_name="Lisinopril"), headers=headers)

        resp = await client.get(RX_URL, headers=headers)
        names = [r["medication_name"] for r in resp.json()]
        assert "Metformin" in names
        assert "Lisinopril" in names

    async def test_list_prescriptions_filter_by_status(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        create_resp = await client.post(RX_URL, json=rx_payload(medication_name="OldMed"), headers=headers)
        rx_id = create_resp.json()["id"]

        await client.patch(f"{RX_URL}/{rx_id}", json={"status": "discontinued"}, headers=headers)
        await client.post(RX_URL, json=rx_payload(medication_name="ActiveMed"), headers=headers)

        resp = await client.get(f"{RX_URL}?status=active", headers=headers)
        names = [r["medication_name"] for r in resp.json()]
        assert "ActiveMed" in names
        assert "OldMed" not in names

    async def test_update_prescription_success(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        create_resp = await client.post(RX_URL, json=rx_payload(), headers=headers)
        rx_id = create_resp.json()["id"]

        resp = await client.patch(
            f"{RX_URL}/{rx_id}",
            json={"dosage": "200mg", "status": "discontinued", "notes": "Side effects"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dosage"] == "200mg"
        assert data["status"] == "discontinued"
        assert data["notes"] == "Side effects"

    async def test_update_prescription_partial(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        create_resp = await client.post(
            RX_URL, json=rx_payload(dosage="400mg", frequency="twice daily"), headers=headers
        )
        rx_id = create_resp.json()["id"]

        resp = await client.patch(f"{RX_URL}/{rx_id}", json={"dosage": "800mg"}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["dosage"] == "800mg"
        assert data["frequency"] == "twice daily"  # unchanged

    async def test_update_nonexistent_prescription(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.patch(f"{RX_URL}/{uuid.uuid4()}", json={"status": "active"}, headers=headers)
        assert resp.status_code == 404

    async def test_delete_prescription_success(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        create_resp = await client.post(RX_URL, json=rx_payload(), headers=headers)
        rx_id = create_resp.json()["id"]

        resp = await client.delete(f"{RX_URL}/{rx_id}", headers=headers)
        assert resp.status_code == 204

        list_resp = await client.get(RX_URL, headers=headers)
        ids = [r["id"] for r in list_resp.json()]
        assert rx_id not in ids

    async def test_delete_nonexistent_prescription(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.delete(f"{RX_URL}/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    async def test_cannot_update_other_users_prescription(self, client: AsyncClient, auth_headers):
        headers_a, _, __ = auth_headers

        email_b = f"b_{uuid.uuid4().hex[:6]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email_b, "password": "Pass123!"})
        login_b = await client.post("/api/v1/auth/login", json={"email": email_b, "password": "Pass123!"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        create_resp = await client.post(RX_URL, json=rx_payload(), headers=headers_b)
        rx_id = create_resp.json()["id"]

        resp = await client.patch(f"{RX_URL}/{rx_id}", json={"status": "discontinued"}, headers=headers_a)
        assert resp.status_code == 404

    async def test_cannot_delete_other_users_prescription(self, client: AsyncClient, auth_headers):
        headers_a, _, __ = auth_headers

        email_b = f"b_{uuid.uuid4().hex[:6]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email_b, "password": "Pass123!"})
        login_b = await client.post("/api/v1/auth/login", json={"email": email_b, "password": "Pass123!"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        create_resp = await client.post(RX_URL, json=rx_payload(), headers=headers_b)
        rx_id = create_resp.json()["id"]

        resp = await client.delete(f"{RX_URL}/{rx_id}", headers=headers_a)
        assert resp.status_code == 404

    async def test_list_only_own_prescriptions(self, client: AsyncClient, auth_headers):
        headers_a, _, __ = auth_headers

        email_b = f"b_{uuid.uuid4().hex[:6]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email_b, "password": "Pass123!"})
        login_b = await client.post("/api/v1/auth/login", json={"email": email_b, "password": "Pass123!"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        await client.post(RX_URL, json=rx_payload(medication_name="User B Drug"), headers=headers_b)

        resp = await client.get(RX_URL, headers=headers_a)
        names = [r["medication_name"] for r in resp.json()]
        assert "User B Drug" not in names

    async def test_prescriptions_requires_auth(self, client: AsyncClient):
        resp = await client.get(RX_URL)
        assert resp.status_code == 403
