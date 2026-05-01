"""Valeteck v5 — Backend tests for /api/earnings/me and /api/earnings/price-table"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

TECH_EMAIL = os.environ.get("TECH_EMAIL", "tecnico@valeteck.com")
TECH_PASSWORD = os.environ.get("TECH_PASSWORD", "tecnico123")

EXPECTED_COMPANIES = {"Rastremix", "GPS My", "GPS Joy", "Topy Pro", "Telensat", "Valeteck"}
EXPECTED_TYPES = {"Instalação", "Manutenção", "Retirada", "Garantia"}


# ------- Fixtures -------
@pytest.fixture(scope="module")
def tech_token():
    r = requests.post(f"{API}/auth/login", json={"email": TECH_EMAIL, "password": TECH_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def tech_headers(tech_token):
    return {"Authorization": f"Bearer {tech_token}", "Content-Type": "application/json"}


# ------- Price Table -------
class TestPriceTable:
    def test_price_table_public(self):
        r = requests.get(f"{API}/earnings/price-table", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "price_table" in d and "default" in d
        assert d["sla_fast_minutes"] == 30
        assert d["sla_fast_bonus_pct"] == 0.2
        companies = set(d["price_table"].keys())
        assert EXPECTED_COMPANIES.issubset(companies), f"missing companies: {EXPECTED_COMPANIES - companies}"
        for c in EXPECTED_COMPANIES:
            types_present = set(d["price_table"][c].keys())
            assert EXPECTED_TYPES.issubset(types_present), f"{c} missing types: {EXPECTED_TYPES - types_present}"
            for t in EXPECTED_TYPES:
                v = d["price_table"][c][t]
                assert isinstance(v, (int, float)) and v > 0


# ------- Earnings /me auth + validation -------
class TestEarningsAuth:
    def test_unauthorized_returns_401(self):
        r = requests.get(f"{API}/earnings/me", timeout=15)
        assert r.status_code in (401, 403), f"expected 401, got {r.status_code}"

    def test_invalid_period_returns_400(self, tech_headers):
        r = requests.get(f"{API}/earnings/me?period=invalid", headers=tech_headers, timeout=15)
        assert r.status_code == 400


# ------- Earnings shape per period -------
@pytest.mark.parametrize("period", ["day", "week", "month", "all"])
def test_earnings_shape(tech_headers, period):
    r = requests.get(f"{API}/earnings/me?period={period}", headers=tech_headers, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    # shape
    for k in ["period", "total_base", "total_bonus", "total_net",
              "count", "avg_elapsed_min", "fast_count",
              "breakdown_by_company", "breakdown_by_type", "jobs", "price_table"]:
        assert k in d, f"missing key {k}"
    assert d["period"] == period
    assert isinstance(d["jobs"], list)
    assert isinstance(d["breakdown_by_company"], dict)
    assert isinstance(d["breakdown_by_type"], dict)
    # price_table correctness
    assert EXPECTED_COMPANIES.issubset(set(d["price_table"].keys()))
    # numeric sanity
    assert d["total_net"] == round(d["total_base"] + d["total_bonus"], 2) or abs(d["total_net"] - (d["total_base"] + d["total_bonus"])) < 0.02
    assert d["count"] == len(d["jobs"])


class TestEarningsBusinessRules:
    def test_month_returns_data_if_jobs_exist(self, tech_headers):
        r = requests.get(f"{API}/earnings/me?period=all", headers=tech_headers, timeout=20)
        assert r.status_code == 200
        d = r.json()
        # v5 context: técnico já tem ~12 checklists enviados
        assert d["count"] >= 1, f"Expected sent checklists for tecnico; got count={d['count']}"
        assert d["total_net"] > 0
        # jobs shape
        j = d["jobs"][0]
        for k in ["id", "numero", "empresa", "tipo_atendimento", "nome", "sobrenome",
                  "placa", "base_amount", "bonus_amount", "total_amount",
                  "elapsed_sec", "elapsed_min", "sla_fast"]:
            assert k in j, f"job missing {k}"

    def test_sla_bonus_logic_per_job(self, tech_headers):
        """For each job, verify: elapsed<1800 → bonus≈base*0.2 & sla_fast=True;
        elapsed==0 OR elapsed>=1800 → bonus==0 & sla_fast=False."""
        r = requests.get(f"{API}/earnings/me?period=all", headers=tech_headers, timeout=20)
        d = r.json()
        fast_actual = 0
        for j in d["jobs"]:
            base = j["base_amount"]
            bonus = j["bonus_amount"]
            elapsed = j["elapsed_sec"]
            fast = j["sla_fast"]
            if elapsed > 0 and elapsed < 1800:
                assert fast is True, f"job {j['id']} elapsed={elapsed} should be sla_fast"
                expected_bonus = round(base * 0.2, 2)
                assert abs(bonus - expected_bonus) < 0.02, f"bonus mismatch job {j['id']}: got {bonus} expected {expected_bonus}"
                fast_actual += 1
            else:
                assert fast is False, f"job {j['id']} elapsed={elapsed} should NOT be sla_fast"
                assert bonus == 0.0, f"job {j['id']} should have no bonus; got {bonus}"
            # total = base + bonus
            assert abs(j["total_amount"] - (base + bonus)) < 0.02
        assert d["fast_count"] == fast_actual, f"fast_count mismatch: {d['fast_count']} != {fast_actual}"

    def test_day_subset_of_week_subset_of_month_subset_of_all(self, tech_headers):
        counts = {}
        for p in ["day", "week", "month", "all"]:
            r = requests.get(f"{API}/earnings/me?period={p}", headers=tech_headers, timeout=20)
            assert r.status_code == 200
            counts[p] = r.json()["count"]
        assert counts["day"] <= counts["week"] <= counts["month"] <= counts["all"], counts

    def test_drafts_not_included(self, tech_headers):
        """Criar um rascunho e garantir que ele NÃO aparece no earnings."""
        draft_payload = {
            "empresa": "Valeteck",
            "numero": "TEST_V5_DRAFT",
            "nome": "TEST_V5",
            "sobrenome": "Draft",
            "telefone": "(11) 90000-0000",
            "placa": "TST0V5",
            "veiculo": "Teste",
            "data_agendamento": "2026-01-15T10:00:00Z",
            "endereco": "rua x",
            "cidade": "SP",
            "estado": "SP",
            "cep": "00000-000",
            "equipamento": "Teste",
            "numero_serie": "SN-TEST-V5",
            "acessorios": [],
            "tipo_atendimento": "Instalação",
            "observacoes": "draft v5",
            "status": "rascunho",
        }
        cr = requests.post(f"{API}/checklists", json=draft_payload, headers=tech_headers, timeout=20)
        assert cr.status_code in (200, 201), cr.text
        draft_id = cr.json()["id"]
        try:
            r = requests.get(f"{API}/earnings/me?period=all", headers=tech_headers, timeout=20)
            d = r.json()
            ids = {j["id"] for j in d["jobs"]}
            assert draft_id not in ids, "Draft checklist must NOT appear in earnings"
        finally:
            requests.delete(f"{API}/checklists/{draft_id}", headers=tech_headers, timeout=15)

    def test_breakdown_by_company_sum_matches_total_net(self, tech_headers):
        r = requests.get(f"{API}/earnings/me?period=all", headers=tech_headers, timeout=20)
        d = r.json()
        sum_company = round(sum(d["breakdown_by_company"].values()), 2)
        assert abs(sum_company - d["total_net"]) < 0.05, (sum_company, d["total_net"])
        sum_type = round(sum(d["breakdown_by_type"].values()), 2)
        assert abs(sum_type - d["total_net"]) < 0.05, (sum_type, d["total_net"])
