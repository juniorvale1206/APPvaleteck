# Valeteck v8 — Backend regression for offline-first feature
# Goal: confirm POST /api/checklists still works (used by sync queue auto-flush)
import os
import time
import pytest
import requests

BASE_URL = (os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL") or "").rstrip("/")
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL/EXPO_BACKEND_URL must be set"

TECH = {"email": "tecnico@valeteck.com", "password": "tecnico123"}


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=TECH, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# Health & auth
class TestHealth:
    def test_health(self):
        r = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert r.status_code == 200

    def test_auth_me(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert r.json().get("email") == TECH["email"]


# Regression: POST /api/checklists (used by SyncProvider.syncNow + revisao online path)
class TestChecklistRegression:
    def _payload(self):
        return {
            "vehicle_type": "carro",
            "vehicle_brand": "TEST_BRAND",
            "vehicle_model": "TEST_MODEL",
            "vehicle_year": "2024",
            "vehicle_color": "Preto",
            "vehicle_vin": "",
            "vehicle_odometer": 12345,
            "nome": "TEST_Sync",
            "sobrenome": "v8",
            "placa": "ABC1D23",
            "telefone": "11999999999",
            "obs_iniciais": "TEST_v8 offline-first regression",
            "problems_client": [],
            "problems_client_other": "",
            "empresa": "Empresa Teste",
            "equipamento": "GS-100",
            "tipo_atendimento": "Instalação",
            "acessorios": [],
            "obs_tecnicas": "",
            "problems_technician": [],
            "problems_technician_other": "",
            "battery_state": "ok",
            "battery_voltage": 12.7,
            "imei": "111111111111111",
            "iccid": "8955010000000000000",
            "device_online": True,
            "device_tested_at": "",
            "device_test_message": "",
            "execution_started_at": "",
            "execution_ended_at": "",
            "execution_elapsed_sec": 0,
            "photos": [],
            "location": None,
            "location_available": False,
            "signature_base64": "",
            "appointment_id": "",
            "status": "rascunho",
        }

    def test_create_and_get(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/checklists", headers=auth_headers, json=self._payload(), timeout=20)
        assert r.status_code in (200, 201), r.text
        data = r.json()
        assert "id" in data and "numero" in data
        cid = data["id"]
        # GET to verify persistence
        g = requests.get(f"{BASE_URL}/api/checklists/{cid}", headers=auth_headers, timeout=15)
        assert g.status_code == 200
        body = g.json()
        assert body.get("nome") == "TEST_Sync"
        assert body.get("placa", "").upper().replace("-", "") == "ABC1D23"
        # cleanup
        requests.delete(f"{BASE_URL}/api/checklists/{cid}", headers=auth_headers, timeout=15)

    def test_create_enviado_status(self, auth_headers):
        # Mirrors what SyncProvider sends after offline → online
        p = self._payload()
        p["status"] = "enviado"
        r = requests.post(f"{BASE_URL}/api/checklists", headers=auth_headers, json=p, timeout=20)
        assert r.status_code in (200, 201), r.text
        data = r.json()
        assert data.get("status") in ("enviado", "sent")
        cid = data["id"]
        requests.delete(f"{BASE_URL}/api/checklists/{cid}", headers=auth_headers, timeout=15)

    def test_unauthorized(self):
        r = requests.post(f"{BASE_URL}/api/checklists", json=self._payload(), timeout=10)
        assert r.status_code in (401, 403)
