"""Valeteck v2 backend tests — agenda, vehicle_type, battery, problems multi-select."""
import os
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") if os.environ.get("EXPO_PUBLIC_BACKEND_URL") else None
# fallback to frontend env file
if not BASE_URL:
    from pathlib import Path
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
            break

TECH_EMAIL = "tecnico@valeteck.com"
TECH_PASSWORD = "tecnico123"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": TECH_EMAIL, "password": TECH_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ----------------- Agenda -----------------
class TestAgenda:
    def test_list_appointments_returns_3(self, headers):
        r = requests.get(f"{BASE_URL}/api/appointments", headers=headers, timeout=15)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 3, f"expected >=3 OS, got {len(items)}"
        nums = sorted([a["numero_os"] for a in items])
        assert "OS-2026-0001" in nums and "OS-2026-0002" in nums and "OS-2026-0003" in nums
        # vehicle_type populated
        for a in items:
            assert a.get("vehicle_type") in ("carro", "moto")
            assert a["status"] in ("agendado", "em_andamento", "concluido")
            assert a["empresa"]
            assert a["endereco"]
            assert a["scheduled_at"]

    def test_get_appointment_detail(self, headers):
        r = requests.get(f"{BASE_URL}/api/appointments", headers=headers, timeout=15)
        first_id = r.json()[0]["id"]
        r2 = requests.get(f"{BASE_URL}/api/appointments/{first_id}", headers=headers, timeout=15)
        assert r2.status_code == 200
        d = r2.json()
        assert d["id"] == first_id
        assert d["numero_os"].startswith("OS-")

    def test_get_appointment_404(self, headers):
        r = requests.get(f"{BASE_URL}/api/appointments/does-not-exist", headers=headers, timeout=15)
        assert r.status_code == 404

    def test_appointments_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/appointments", timeout=15)
        assert r.status_code == 401


# ----------------- Reference (v2) -----------------
class TestReferenceV2:
    def test_accessories_carro_21(self, headers):
        r = requests.get(f"{BASE_URL}/api/reference/accessories",
                         params={"vehicle_type": "carro"}, headers=headers, timeout=15)
        assert r.status_code == 200
        acc = r.json()["accessories"]
        assert len(acc) == 21, f"expected 21 acessórios carro, got {len(acc)}"

    def test_accessories_moto_17(self, headers):
        r = requests.get(f"{BASE_URL}/api/reference/accessories",
                         params={"vehicle_type": "moto"}, headers=headers, timeout=15)
        assert r.status_code == 200
        acc = r.json()["accessories"]
        assert len(acc) == 17, f"expected 17 acessórios moto, got {len(acc)}"

    def test_accessories_no_param_union(self, headers):
        r = requests.get(f"{BASE_URL}/api/reference/accessories", headers=headers, timeout=15)
        assert r.status_code == 200
        acc = r.json()["accessories"]
        # union (dedup) — should be > 21
        assert len(acc) > 21

    def test_battery_states(self, headers):
        r = requests.get(f"{BASE_URL}/api/reference/battery-states", headers=headers, timeout=15)
        assert r.status_code == 200
        st = r.json()["battery_states"]
        assert st == ["Nova", "Em bom estado", "Usada", "Apresentando falhas"]

    def test_problems_lists(self, headers):
        r = requests.get(f"{BASE_URL}/api/reference/problems", headers=headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "client" in d and "technician" in d
        assert len(d["client"]) == 11, f"expected 11 client problems, got {len(d['client'])}"
        assert len(d["technician"]) == 10, f"expected 10 tech problems, got {len(d['technician'])}"


# ----------------- Checklist v2 fields & appointment link -----------------
class TestChecklistV2:
    def _base_payload(self, appointment_id=None):
        return {
            "vehicle_type": "carro",
            "nome": "TEST_V2",
            "sobrenome": "Tester",
            "placa": "TST1A23",
            "telefone": "11999999999",
            "obs_iniciais": "",
            "problems_client": ["Bateria fraca", "Não liga"],
            "problems_client_other": "Faz barulho estranho",
            "empresa": "Rastremix",
            "equipamento": "Rastreador GPS XT-2000",
            "tipo_atendimento": "Instalação",
            "acessorios": ["Painel", "Buzina e sirene"],
            "obs_tecnicas": "",
            "problems_technician": ["Fiação danificada", "Bateria abaixo de 11V"],
            "problems_technician_other": "Conector ressecado",
            "battery_state": "Usada",
            "battery_voltage": 12.1,
            "photos": [],
            "location": None,
            "location_available": False,
            "signature_base64": "",
            "appointment_id": appointment_id or "",
            "status": "rascunho",
        }

    def test_create_checklist_v2_fields_persist(self, headers):
        r = requests.post(f"{BASE_URL}/api/checklists", headers=headers,
                          json=self._base_payload(), timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["vehicle_type"] == "carro"
        assert d["battery_state"] == "Usada"
        assert d["battery_voltage"] == 12.1
        assert "Bateria fraca" in d["problems_client"]
        assert d["problems_client_other"] == "Faz barulho estranho"
        assert "Fiação danificada" in d["problems_technician"]
        assert d["problems_technician_other"] == "Conector ressecado"
        cid = d["id"]
        # GET verify persistence
        r2 = requests.get(f"{BASE_URL}/api/checklists/{cid}", headers=headers, timeout=15)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["vehicle_type"] == "carro"
        assert d2["battery_voltage"] == 12.1
        # cleanup
        requests.delete(f"{BASE_URL}/api/checklists/{cid}", headers=headers, timeout=15)

    def test_appointment_status_em_andamento_on_rascunho(self, headers):
        # Find an agendado OS
        appts = requests.get(f"{BASE_URL}/api/appointments", headers=headers, timeout=15).json()
        target = next((a for a in appts if a["status"] == "agendado"), appts[0])
        aid = target["id"]
        payload = self._base_payload(appointment_id=aid)
        payload["status"] = "rascunho"
        r = requests.post(f"{BASE_URL}/api/checklists", headers=headers, json=payload, timeout=15)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        # Verify appointment now em_andamento
        r2 = requests.get(f"{BASE_URL}/api/appointments/{aid}", headers=headers, timeout=15)
        assert r2.status_code == 200
        d = r2.json()
        assert d["status"] == "em_andamento", f"expected em_andamento, got {d['status']}"
        assert d["checklist_id"] == cid
        # cleanup checklist
        requests.delete(f"{BASE_URL}/api/checklists/{cid}", headers=headers, timeout=15)

    def test_appointment_status_concluido_on_enviado(self, headers):
        # Use second agendado/em_andamento OS
        appts = requests.get(f"{BASE_URL}/api/appointments", headers=headers, timeout=15).json()
        target = next((a for a in appts if a["status"] in ("agendado", "em_andamento") and not a.get("checklist_id")), None)
        if not target:
            # fallback — use any not concluido
            target = next((a for a in appts if a["status"] != "concluido"), appts[1])
        aid = target["id"]
        payload = self._base_payload(appointment_id=aid)
        # Build minimal valid 'enviado' payload
        payload["status"] = "enviado"
        payload["photos"] = [
            {"label": "p1", "base64": "iVBORw0KGgoAAAANS"},
            {"label": "p2", "base64": "iVBORw0KGgoAAAANS"},
        ]
        payload["signature_base64"] = "data:image/png;base64,iVBOR"
        r = requests.post(f"{BASE_URL}/api/checklists", headers=headers, json=payload, timeout=15)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        # Verify appointment now concluido
        r2 = requests.get(f"{BASE_URL}/api/appointments/{aid}", headers=headers, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["status"] == "concluido"
        # enviado checklists cannot be deleted; leave it
