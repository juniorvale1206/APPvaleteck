"""Valeteck Backend Tests — Auth, Reference, Checklist CRUD, Antifraude"""
import os
import time
import requests
import pytest
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = None
fenv = Path("/app/frontend/.env")
if fenv.exists():
    for line in fenv.read_text().splitlines():
        if line.startswith("EXPO_PUBLIC_BACKEND_URL"):
            BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
            break
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL not found"

API = BASE_URL + "/api"
TIMEOUT = 30

# minimal valid base64 PNG
PNG_B64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="


@pytest.fixture(scope="session")
def s():
    return requests.Session()


@pytest.fixture(scope="session")
def token(s):
    r = s.post(f"{API}/auth/login", json={"email": "tecnico@valeteck.com", "password": "tecnico123"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data and "user" in data
    return data["token"]


@pytest.fixture(scope="session")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- Auth ----------
class TestAuth:
    def test_login_success(self, s):
        r = s.post(f"{API}/auth/login", json={"email": "tecnico@valeteck.com", "password": "tecnico123"}, timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["email"] == "tecnico@valeteck.com"
        assert d["user"]["role"] == "tecnico"
        assert isinstance(d["token"], str) and len(d["token"]) > 20

    def test_login_invalid(self, s):
        r = s.post(f"{API}/auth/login", json={"email": "tecnico@valeteck.com", "password": "wrong"}, timeout=TIMEOUT)
        assert r.status_code == 401

    def test_me(self, s, auth_headers):
        r = s.get(f"{API}/auth/me", headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json()["email"] == "tecnico@valeteck.com"

    def test_me_no_token(self, s):
        r = s.get(f"{API}/auth/me", timeout=TIMEOUT)
        assert r.status_code == 401


# ---------- Reference ----------
class TestReference:
    def test_companies(self, s):
        r = s.get(f"{API}/reference/companies", timeout=TIMEOUT)
        assert r.status_code == 200
        c = r.json()["companies"]
        for name in ["Rastremix", "GPS My", "GPS Joy", "Topy Pro", "Telensat", "Valeteck"]:
            assert name in c
        assert len(c) == 6

    def test_equipments(self, s):
        r = s.get(f"{API}/reference/equipments", timeout=TIMEOUT)
        assert r.status_code == 200 and len(r.json()["equipments"]) >= 1

    def test_accessories(self, s):
        r = s.get(f"{API}/reference/accessories", timeout=TIMEOUT)
        assert r.status_code == 200 and len(r.json()["accessories"]) >= 1

    def test_service_types(self, s):
        r = s.get(f"{API}/reference/service-types", timeout=TIMEOUT)
        assert r.status_code == 200 and "Instalação" in r.json()["service_types"]


def _full_payload(placa="ABC1D23", tipo="Instalação", status="enviado"):
    return {
        "nome": "TEST_João", "sobrenome": "TEST_Silva", "placa": placa,
        "telefone": "11999999999", "obs_iniciais": "ok",
        "empresa": "Valeteck", "equipamento": "Rastreador GPS XT-2000",
        "tipo_atendimento": tipo, "acessorios": ["Sirene"], "obs_tecnicas": "",
        "photos": [{"label": "Frente", "base64": PNG_B64}, {"label": "Traseira", "base64": PNG_B64}],
        "location": None, "location_available": False,
        "signature_base64": PNG_B64, "status": status,
    }


# ---------- Checklists ----------
created_ids = []


class TestChecklists:
    def test_create_rascunho_partial(self, s, auth_headers):
        r = s.post(f"{API}/checklists", json={"nome": "TEST_X", "sobrenome": "", "placa": "", "empresa": "", "equipamento": "", "status": "rascunho"}, headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "rascunho" and d["numero"].startswith("VT-")
        created_ids.append(d["id"])

    def test_send_missing_fields_400(self, s, auth_headers):
        p = _full_payload()
        p["nome"] = ""
        p["photos"] = []
        p["signature_base64"] = ""
        r = s.post(f"{API}/checklists", json=p, headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code == 400
        assert "obrigatório" in r.text.lower() or "obrigat" in r.text.lower()

    def test_send_invalid_plate(self, s, auth_headers):
        p = _full_payload(placa="XX9999")
        r = s.post(f"{API}/checklists", json=p, headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code == 400
        assert "placa" in r.text.lower()

    def test_plate_old_format(self, s, auth_headers):
        # ABC1234 old format should be valid
        p = _full_payload(placa="XYZ1234")
        r = s.post(f"{API}/checklists", json=p, headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        created_ids.append(r.json()["id"])

    def test_create_enviado_full(self, s, auth_headers):
        p = _full_payload(placa="QWE2A34")
        r = s.post(f"{API}/checklists", json=p, headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "enviado"
        assert d["numero"].startswith("VT-")
        assert d["alerts"] == []
        assert d["placa"] == "QWE2A34"  # normalized
        created_ids.append(d["id"])

        # verify GET persistence
        g = s.get(f"{API}/checklists/{d['id']}", headers=auth_headers, timeout=TIMEOUT)
        assert g.status_code == 200
        assert g.json()["nome"] == "TEST_João"

    def test_list_and_search(self, s, auth_headers):
        r = s.get(f"{API}/checklists", headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 1
        r2 = s.get(f"{API}/checklists?q=QWE2A34", headers=auth_headers, timeout=TIMEOUT)
        assert r2.status_code == 200
        assert any(c["placa"] == "QWE2A34" for c in r2.json())

    def test_edit_rascunho_and_block_enviado(self, s, auth_headers):
        # Create rascunho
        p = _full_payload(placa="DRA1F23", status="rascunho")
        r = s.post(f"{API}/checklists", json=p, headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code == 200
        cid = r.json()["id"]
        created_ids.append(cid)
        # Edit rascunho
        p["obs_iniciais"] = "edited"
        r2 = s.put(f"{API}/checklists/{cid}", json=p, headers=auth_headers, timeout=TIMEOUT)
        assert r2.status_code == 200 and r2.json()["obs_iniciais"] == "edited"
        # Promote to enviado
        p["status"] = "enviado"
        r3 = s.put(f"{API}/checklists/{cid}", json=p, headers=auth_headers, timeout=TIMEOUT)
        assert r3.status_code == 200 and r3.json()["status"] == "enviado"
        # Block edit on enviado
        r4 = s.put(f"{API}/checklists/{cid}", json=p, headers=auth_headers, timeout=TIMEOUT)
        assert r4.status_code == 400


# ---------- Antifraude ----------
class TestAntifraude:
    def test_duplicate_within_24h(self, s, auth_headers):
        plate = "DUP1A23"
        p1 = _full_payload(placa=plate, tipo="Instalação")
        r1 = s.post(f"{API}/checklists", json=p1, headers=auth_headers, timeout=TIMEOUT)
        assert r1.status_code == 200
        created_ids.append(r1.json()["id"])
        assert r1.json()["alerts"] == []
        # Second on same plate within 24h
        p2 = _full_payload(placa=plate, tipo="Instalação")
        r2 = s.post(f"{API}/checklists", json=p2, headers=auth_headers, timeout=TIMEOUT)
        assert r2.status_code == 200
        created_ids.append(r2.json()["id"])
        alerts = r2.json()["alerts"]
        assert any("duplicidade" in a.lower() or "24h" in a.lower() for a in alerts), alerts

    def test_garantia_alert(self, s, auth_headers):
        plate = "GAR2B34"
        # First Instalação
        r1 = s.post(f"{API}/checklists", json=_full_payload(placa=plate, tipo="Instalação"), headers=auth_headers, timeout=TIMEOUT)
        assert r1.status_code == 200
        created_ids.append(r1.json()["id"])
        # New Manutenção for same plate
        r2 = s.post(f"{API}/checklists", json=_full_payload(placa=plate, tipo="Manutenção"), headers=auth_headers, timeout=TIMEOUT)
        assert r2.status_code == 200
        created_ids.append(r2.json()["id"])
        alerts = r2.json()["alerts"]
        assert any("garantia" in a.lower() or "30 dias" in a.lower() for a in alerts), alerts


def teardown_module(module):
    """Best-effort cleanup of created TEST checklists (rascunho only deletable)."""
    try:
        r = requests.post(f"{API}/auth/login", json={"email": "tecnico@valeteck.com", "password": "tecnico123"}, timeout=10)
        token = r.json()["token"]
        h = {"Authorization": f"Bearer {token}"}
        for cid in created_ids:
            requests.delete(f"{API}/checklists/{cid}", headers=h, timeout=10)
    except Exception:
        pass
