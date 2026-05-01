"""Valeteck v4 backend tests — device/test mock, photo workflow_step, IMEI/ICCID/SLA persistence."""
import os
import pytest
import requests
from pathlib import Path

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL")
if not BASE_URL:
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().strip('"')
            break
BASE_URL = BASE_URL.rstrip("/")

TECH_EMAIL = "tecnico@valeteck.com"
TECH_PASSWORD = "tecnico123"

VALID_IMEI = "123456789012345"
VALID_IMEI_2 = "987654321098765"

# 1x1 transparent PNG
PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA"
    "60e6kgAAAABJRU5ErkJggg=="
)
SIG_B64 = "data:image/png;base64," + PNG_B64


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": TECH_EMAIL, "password": TECH_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ----------------- Device test (mock) -----------------
class TestDeviceTest:
    def test_valid_imei_returns_payload(self, headers):
        r = requests.post(f"{BASE_URL}/api/device/test",
                          headers=headers, json={"imei": VALID_IMEI}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("online"), bool)
        assert isinstance(d.get("latency_ms"), int)
        assert d["latency_ms"] >= 0
        assert isinstance(d.get("message"), str) and len(d["message"]) > 0
        assert d.get("tested_at")

    def test_invalid_imei_short_returns_400(self, headers):
        r = requests.post(f"{BASE_URL}/api/device/test",
                          headers=headers, json={"imei": "12345"}, timeout=15)
        assert r.status_code == 400

    def test_invalid_imei_non_digit_returns_400(self, headers):
        r = requests.post(f"{BASE_URL}/api/device/test",
                          headers=headers, json={"imei": "12345678901234A"}, timeout=15)
        assert r.status_code == 400

    def test_empty_imei_returns_400(self, headers):
        r = requests.post(f"{BASE_URL}/api/device/test",
                          headers=headers, json={"imei": ""}, timeout=15)
        assert r.status_code == 400

    def test_determinism_same_imei_same_result(self, headers):
        r1 = requests.post(f"{BASE_URL}/api/device/test",
                           headers=headers, json={"imei": VALID_IMEI}, timeout=15).json()
        r2 = requests.post(f"{BASE_URL}/api/device/test",
                           headers=headers, json={"imei": VALID_IMEI}, timeout=15).json()
        assert r1["online"] == r2["online"]
        assert r1["latency_ms"] == r2["latency_ms"]

    def test_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/device/test",
                          json={"imei": VALID_IMEI}, timeout=15)
        assert r.status_code == 401


# ----------------- Photo workflow_step validation -----------------
def _base_payload(status="rascunho", photos=None, imei="", iccid="",
                  device_online=None, device_tested_at="", device_test_message="",
                  exec_started="", exec_ended="", exec_elapsed=0,
                  vbrand="", vmodel="", vyear="", vcolor="", vvin="", vodom=None):
    return {
        "vehicle_type": "carro",
        "vehicle_brand": vbrand,
        "vehicle_model": vmodel,
        "vehicle_year": vyear,
        "vehicle_color": vcolor,
        "vehicle_vin": vvin,
        "vehicle_odometer": vodom,
        "nome": "TEST_Joao",
        "sobrenome": "TEST_Silva",
        "placa": "ABC1D23",
        "telefone": "(11) 99999-0000",
        "obs_iniciais": "",
        "problems_client": [],
        "empresa": "Valeteck",
        "equipamento": "Rastreador GPS XT-2000",
        "tipo_atendimento": "Instalação",
        "acessorios": [],
        "obs_tecnicas": "",
        "problems_technician": [],
        "battery_state": "Nova",
        "battery_voltage": 12.5,
        "imei": imei,
        "iccid": iccid,
        "device_online": device_online,
        "device_tested_at": device_tested_at,
        "device_test_message": device_test_message,
        "execution_started_at": exec_started,
        "execution_ended_at": exec_ended,
        "execution_elapsed_sec": exec_elapsed,
        "photos": photos if photos is not None else [],
        "location": None,
        "location_available": False,
        "signature_base64": SIG_B64,
        "appointment_id": "",
        "status": status,
    }


def _all_steps_photos():
    return [
        {"label": f"g{step}-{i}", "base64": PNG_B64,
         "workflow_step": step, "photo_id": f"step{step}_p{i}"}
        for step in (1, 2, 3, 4) for i in (1, 2)
    ]


class TestChecklistV4:
    created_ids = []

    def test_create_draft_with_workflow_photos_persists_step_and_photo_id(self, headers):
        photos = _all_steps_photos()
        r = requests.post(f"{BASE_URL}/api/checklists",
                          headers=headers,
                          json=_base_payload(status="rascunho", photos=photos), timeout=15)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        TestChecklistV4.created_ids.append(cid)

        # GET to verify persistence
        g = requests.get(f"{BASE_URL}/api/checklists/{cid}", headers=headers, timeout=15)
        assert g.status_code == 200
        body = g.json()
        # Photos must contain workflow_step and photo_id
        ws = sorted({p.get("workflow_step") for p in body["photos"]})
        assert ws == [1, 2, 3, 4], f"workflow_step not persisted, got {ws}"
        ids = {p.get("photo_id") for p in body["photos"]}
        assert "step1_p1" in ids and "step4_p2" in ids, ids

    def test_send_missing_workflow_groups_returns_400(self, headers):
        # Photos only in groups 1 and 2 (>=2 photos but missing 3 and 4)
        photos = [
            {"label": "g1-1", "base64": PNG_B64, "workflow_step": 1, "photo_id": "a"},
            {"label": "g2-1", "base64": PNG_B64, "workflow_step": 2, "photo_id": "b"},
        ]
        r = requests.post(f"{BASE_URL}/api/checklists",
                          headers=headers,
                          json=_base_payload(status="enviado", photos=photos), timeout=15)
        assert r.status_code == 400, r.text
        assert "grupos" in r.text.lower() or "faltantes" in r.text.lower()

    def test_send_with_all_4_groups_succeeds(self, headers):
        r = requests.post(f"{BASE_URL}/api/checklists",
                          headers=headers,
                          json=_base_payload(status="enviado", photos=_all_steps_photos(),
                                             imei=VALID_IMEI, iccid="89551234567890123456",
                                             device_online=True,
                                             device_tested_at="2026-01-15T10:00:00+00:00",
                                             device_test_message="ok",
                                             exec_started="2026-01-15T09:30:00+00:00",
                                             exec_ended="2026-01-15T10:05:00+00:00",
                                             exec_elapsed=2100,
                                             vbrand="Honda", vmodel="Civic", vyear="2022",
                                             vcolor="Preto", vvin="1HGCM82633A004352",
                                             vodom=45230),
                          timeout=15)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        TestChecklistV4.created_ids.append(cid)
        # GET to verify all v4 fields persisted (this is the main bug check)
        g = requests.get(f"{BASE_URL}/api/checklists/{cid}", headers=headers, timeout=15).json()
        assert g["imei"] == VALID_IMEI, f"imei not persisted on POST: got {g.get('imei')!r}"
        assert g["iccid"] == "89551234567890123456", f"iccid: got {g.get('iccid')!r}"
        assert g["device_online"] is True
        assert g["device_test_message"] == "ok"
        assert g["execution_started_at"] == "2026-01-15T09:30:00+00:00"
        assert g["execution_ended_at"] == "2026-01-15T10:05:00+00:00"
        assert g["execution_elapsed_sec"] == 2100
        assert g["vehicle_brand"] == "Honda"
        assert g["vehicle_model"] == "Civic"
        assert g["vehicle_year"] == "2022"
        assert g["vehicle_color"] == "Preto"
        assert g["vehicle_vin"] == "1HGCM82633A004352"
        assert g["vehicle_odometer"] == 45230

    def test_send_with_invalid_imei_returns_400(self, headers):
        r = requests.post(f"{BASE_URL}/api/checklists",
                          headers=headers,
                          json=_base_payload(status="enviado", photos=_all_steps_photos(),
                                             imei="12345"),
                          timeout=15)
        assert r.status_code == 400
        assert "imei" in r.text.lower()

    def test_update_persists_v4_fields(self, headers):
        # Create draft minimal then update with all v4 fields
        r = requests.post(f"{BASE_URL}/api/checklists",
                          headers=headers,
                          json=_base_payload(status="rascunho"), timeout=15)
        assert r.status_code == 200
        cid = r.json()["id"]
        TestChecklistV4.created_ids.append(cid)
        upd = _base_payload(status="rascunho", imei=VALID_IMEI_2, iccid="ICCID999",
                            exec_started="2026-01-15T08:00:00+00:00",
                            exec_elapsed=1800,
                            vbrand="Yamaha", vmodel="Fazer", vyear="2024",
                            vcolor="Vermelho", vvin="VINTEST", vodom=1200)
        r2 = requests.put(f"{BASE_URL}/api/checklists/{cid}", headers=headers,
                          json=upd, timeout=15)
        assert r2.status_code == 200, r2.text
        g = requests.get(f"{BASE_URL}/api/checklists/{cid}", headers=headers, timeout=15).json()
        assert g["imei"] == VALID_IMEI_2
        assert g["iccid"] == "ICCID999"
        assert g["execution_started_at"] == "2026-01-15T08:00:00+00:00"
        assert g["execution_elapsed_sec"] == 1800
        assert g["vehicle_brand"] == "Yamaha"

    @classmethod
    def teardown_class(cls):
        # Best-effort cleanup of drafts only
        try:
            r = requests.post(f"{BASE_URL}/api/auth/login",
                              json={"email": TECH_EMAIL, "password": TECH_PASSWORD},
                              timeout=10)
            tk = r.json().get("token")
            h = {"Authorization": f"Bearer {tk}"}
            for cid in cls.created_ids:
                requests.delete(f"{BASE_URL}/api/checklists/{cid}",
                                headers=h, timeout=10)
        except Exception:
            pass
