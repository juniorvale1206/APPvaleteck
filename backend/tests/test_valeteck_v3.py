"""Valeteck v3 backend tests — agenda v3 (6 OS), new fields (prioridade, telefone,
tempo_estimado_min, created_at) and POST /api/appointments/seed-new."""
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


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": TECH_EMAIL, "password": TECH_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ----------------- Agenda v3 -----------------
class TestAgendaV3:
    def test_list_returns_at_least_6_with_v3_fields(self, headers):
        r = requests.get(f"{BASE_URL}/api/appointments", headers=headers, timeout=15)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 6, f"expected >=6 OS, got {len(items)}"
        # Required v3 fields present on every doc
        valid_prio = {"alta", "normal", "baixa"}
        for a in items:
            assert a.get("prioridade") in valid_prio, f"invalid prioridade: {a.get('prioridade')}"
            assert "telefone" in a
            assert isinstance(a.get("tempo_estimado_min"), int)
            assert a.get("tempo_estimado_min") > 0
            assert a.get("created_at"), "created_at missing"
            assert a.get("vehicle_type") in ("carro", "moto")

    def test_seeded_numeros_os_present(self, headers):
        r = requests.get(f"{BASE_URL}/api/appointments", headers=headers, timeout=15)
        nums = [a["numero_os"] for a in r.json()]
        for expected in ["OS-2026-0001", "OS-2026-0002", "OS-2026-0003",
                         "OS-2026-0004", "OS-2026-0005", "OS-2026-0006"]:
            assert expected in nums, f"missing {expected}"

    def test_prioridade_variety(self, headers):
        r = requests.get(f"{BASE_URL}/api/appointments", headers=headers, timeout=15)
        prios = {a["prioridade"] for a in r.json()}
        # at least 2 distinct priorities must exist in the seed
        assert len(prios) >= 2


# ----------------- seed-new -----------------
class TestSeedNew:
    def test_seed_new_creates_and_persists(self, headers):
        # Snapshot before
        before = requests.get(f"{BASE_URL}/api/appointments", headers=headers, timeout=15).json()
        before_ids = {a["id"] for a in before}
        # Call seed-new
        r = requests.post(f"{BASE_URL}/api/appointments/seed-new", headers=headers, timeout=15)
        assert r.status_code == 200, r.text
        new_doc = r.json()
        # AppointmentOut schema checks
        assert new_doc["id"]
        assert new_doc["numero_os"].startswith("OS-2026-")
        assert new_doc["status"] == "agendado"
        assert new_doc["prioridade"] in ("alta", "normal", "baixa")
        assert isinstance(new_doc["tempo_estimado_min"], int)
        assert new_doc["telefone"].startswith("(11)")
        assert new_doc["created_at"]
        assert new_doc["vehicle_type"] in ("carro", "moto")
        assert new_doc["id"] not in before_ids
        # Verify persisted via GET
        r2 = requests.get(f"{BASE_URL}/api/appointments/{new_doc['id']}",
                          headers=headers, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["numero_os"] == new_doc["numero_os"]
        # Verify list count increased
        after = requests.get(f"{BASE_URL}/api/appointments", headers=headers, timeout=15).json()
        assert len(after) == len(before) + 1

    def test_seed_new_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/appointments/seed-new", timeout=15)
        assert r.status_code == 401
