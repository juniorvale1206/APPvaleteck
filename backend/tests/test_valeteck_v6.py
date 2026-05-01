"""Valeteck v6 backend tests — accept/refuse appointments + delay/penalty fields."""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://installer-track-1.preview.emergentagent.com").rstrip("/")
TECH_EMAIL = "tecnico@valeteck.com"
TECH_PASS = "tecnico123"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": TECH_EMAIL, "password": TECH_PASS}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------------- Listing & new fields ----------------
class TestAppointmentsListing:
    def test_list_returns_six_with_new_fields(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/appointments", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 6
        # Validate v6 fields exist on every appointment
        required = {"vehicle_brand", "vehicle_model", "vehicle_year", "observacoes", "comissao", "delay_min", "penalty_amount"}
        for a in items:
            missing = required - set(a.keys())
            assert not missing, f"OS {a.get('numero_os')} missing fields {missing}"

    def test_delay_and_penalty_computation(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/appointments", headers=auth_headers, timeout=15)
        items = r.json()
        # OS-2026-0001 is seeded with scheduled_at in the past => delay_min > 120 => penalty 100
        os1 = next((a for a in items if a["numero_os"] == "OS-2026-0001"), None)
        assert os1 is not None
        assert os1["delay_min"] > 120, f"expected delay>120, got {os1['delay_min']}"
        assert os1["penalty_amount"] == 100.0

    def test_future_scheduled_no_penalty(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/appointments", headers=auth_headers, timeout=15)
        items = r.json()
        # Future-scheduled OS (e.g., OS-2026-0003) should have delay_min=0, penalty=0
        os3 = next((a for a in items if a["numero_os"] == "OS-2026-0003"), None)
        assert os3 is not None
        assert os3["delay_min"] == 0
        assert os3["penalty_amount"] == 0.0


# ---------------- Accept ----------------
class TestAcceptAppointment:
    def _find_agendado(self, auth_headers, prefer_numero=None):
        items = requests.get(f"{BASE_URL}/api/appointments", headers=auth_headers, timeout=15).json()
        if prefer_numero:
            for a in items:
                if a["numero_os"] == prefer_numero and a["status"] == "agendado":
                    return a
        for a in items:
            if a["status"] == "agendado":
                return a
        return None

    def test_accept_changes_status_to_aceita(self, auth_headers):
        target = self._find_agendado(auth_headers, prefer_numero="OS-2026-0004")
        if target is None:
            pytest.skip("No 'agendado' appointment available to accept")
        r = requests.post(f"{BASE_URL}/api/appointments/{target['id']}/accept", headers=auth_headers, json={}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "aceita"
        assert body["accepted_at"]
        # Verify GET reflects the change (persistence)
        r2 = requests.get(f"{BASE_URL}/api/appointments/{target['id']}", headers=auth_headers, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["status"] == "aceita"

    def test_accept_already_accepted_returns_400(self, auth_headers):
        items = requests.get(f"{BASE_URL}/api/appointments", headers=auth_headers, timeout=15).json()
        accepted = next((a for a in items if a["status"] == "aceita"), None)
        if accepted is None:
            pytest.skip("No 'aceita' appointment available — run accept test first")
        r = requests.post(f"{BASE_URL}/api/appointments/{accepted['id']}/accept", headers=auth_headers, json={}, timeout=15)
        assert r.status_code == 400

    def test_accept_unknown_id_returns_404(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/appointments/does-not-exist/accept", headers=auth_headers, json={}, timeout=15)
        assert r.status_code == 404


# ---------------- Refuse ----------------
class TestRefuseAppointment:
    def _find_agendado(self, auth_headers, prefer_numero=None):
        items = requests.get(f"{BASE_URL}/api/appointments", headers=auth_headers, timeout=15).json()
        if prefer_numero:
            for a in items:
                if a["numero_os"] == prefer_numero and a["status"] == "agendado":
                    return a
        for a in items:
            if a["status"] == "agendado":
                return a
        return None

    def test_refuse_requires_non_empty_reason(self, auth_headers):
        target = self._find_agendado(auth_headers)
        if target is None:
            pytest.skip("No agendado")
        r = requests.post(f"{BASE_URL}/api/appointments/{target['id']}/refuse", headers=auth_headers, json={"reason": "   "}, timeout=15)
        assert r.status_code == 400

    def test_refuse_without_reason_field_returns_422(self, auth_headers):
        target = self._find_agendado(auth_headers)
        if target is None:
            pytest.skip("No agendado")
        r = requests.post(f"{BASE_URL}/api/appointments/{target['id']}/refuse", headers=auth_headers, json={}, timeout=15)
        assert r.status_code in (400, 422)

    def test_refuse_persists_reason_and_status(self, auth_headers):
        target = self._find_agendado(auth_headers, prefer_numero="OS-2026-0006")
        if target is None:
            pytest.skip("No agendado")
        reason = "TEST_v6: cliente cancelou"
        r = requests.post(f"{BASE_URL}/api/appointments/{target['id']}/refuse", headers=auth_headers, json={"reason": reason}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "recusada"
        assert body["refuse_reason"] == reason
        assert body["refused_at"]
        # GET verifies persistence
        r2 = requests.get(f"{BASE_URL}/api/appointments/{target['id']}", headers=auth_headers, timeout=15).json()
        assert r2["status"] == "recusada"
        assert r2["refuse_reason"] == reason


# ---------------- Auth guard ----------------
class TestAuthGuard:
    def test_accept_unauthenticated(self):
        r = requests.post(f"{BASE_URL}/api/appointments/x/accept", json={}, timeout=10)
        assert r.status_code == 401

    def test_refuse_unauthenticated(self):
        r = requests.post(f"{BASE_URL}/api/appointments/x/refuse", json={"reason": "x"}, timeout=10)
        assert r.status_code == 401
