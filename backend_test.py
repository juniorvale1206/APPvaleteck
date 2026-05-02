"""Backend smoke test — Valeteck v14 Fase 2 do Motor de Comissionamento.

Escopo:
  A) GET /api/statement/me (mês atual) — técnico n1
  B) GET /api/statement/me (mês atual) — júnior
  C) GET /api/statement/me?month=2026-04
  D) GET /api/statement/me?month=invalido
  E) POST /api/checklists com service_type_code
  F) POST /api/checklists sem service_type_code (backward compat)
  G) Regressão leve (/auth/me, /gamification/meta, /gamification/profile,
     /inventory/me, /reference/service-catalog)
"""
import os
import re
import sys
from typing import Any

import requests

BASE_URL = os.environ.get(
    "BACKEND_BASE_URL",
    "https://installer-track-1.preview.emergentagent.com/api",
).rstrip("/")

TECNICO = ("tecnico@valeteck.com", "tecnico123")
JUNIOR = ("junior@valeteck.com", "junior123")

STATEMENT_REQUIRED_KEYS = {
    "month", "level", "total_os", "valid_os", "duplicates",
    "within_sla", "out_sla", "sla_compliance_pct",
    "gross_estimated", "penalty_total", "penalty_count",
    "net_estimated", "meta_target", "meta_reached",
    "meta_remaining", "by_service",
}

results: list[tuple[str, bool, str]] = []


def log(name: str, cond: bool, extra: str = "") -> bool:
    mark = "✅" if cond else "❌"
    msg = f"{mark} {name}" + (f" — {extra}" if extra else "")
    print(msg)
    results.append((name, cond, extra))
    return cond


def login(email: str, password: str) -> str:
    r = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=20,
    )
    assert r.status_code == 200, f"login {email} falhou: {r.status_code} {r.text[:200]}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"token ausente para {email}"
    return token


def H(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def run_section_A(token_tec: str):
    print("\n=== A) GET /statement/me (mês atual) — tecnico (n1) ===")
    r = requests.get(f"{BASE_URL}/statement/me", headers=H(token_tec), timeout=20)
    log("A1 HTTP 200", r.status_code == 200, f"status={r.status_code} body={r.text[:300]}")
    if r.status_code != 200:
        return None
    data = r.json()
    missing = STATEMENT_REQUIRED_KEYS - set(data.keys())
    log("A2 todas as chaves presentes", not missing,
        f"faltam={sorted(missing)}" if missing else "OK")
    log("A3 level == 'n1'", data.get("level") == "n1", f"level={data.get('level')}")
    log("A4 meta_target == 60", data.get("meta_target") == 60,
        f"meta_target={data.get('meta_target')}")
    m = data.get("month", "")
    log("A5 month formato YYYY-MM", bool(re.fullmatch(r"\d{4}-\d{2}", m)), f"month={m}")
    log("A6 total_os >= 0", isinstance(data.get("total_os"), int) and data["total_os"] >= 0,
        f"total_os={data.get('total_os')}")
    log("A7 by_service é lista", isinstance(data.get("by_service"), list),
        f"type={type(data.get('by_service')).__name__}")
    return data


def run_section_B():
    print("\n=== B) GET /statement/me — junior ===")
    token = login(*JUNIOR)
    r = requests.get(f"{BASE_URL}/statement/me", headers=H(token), timeout=20)
    log("B1 HTTP 200", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")
    if r.status_code != 200:
        return
    data = r.json()
    log("B2 level == 'junior'", data.get("level") == "junior",
        f"level={data.get('level')}")
    log("B3 meta_target == 30", data.get("meta_target") == 30,
        f"meta_target={data.get('meta_target')}")


def run_section_C(token_tec: str):
    print("\n=== C) GET /statement/me?month=2026-04 ===")
    r = requests.get(
        f"{BASE_URL}/statement/me",
        params={"month": "2026-04"},
        headers=H(token_tec),
        timeout=20,
    )
    log("C1 HTTP 200 mesmo em mês passado",
        r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")
    if r.status_code == 200:
        data = r.json()
        log("C2 month == '2026-04'", data.get("month") == "2026-04",
            f"month={data.get('month')}")


def run_section_D(token_tec: str):
    print("\n=== D) GET /statement/me?month=invalido ===")
    r = requests.get(
        f"{BASE_URL}/statement/me",
        params={"month": "invalido"},
        headers=H(token_tec),
        timeout=20,
    )
    log("D1 HTTP 400 p/ month inválido", r.status_code == 400,
        f"status={r.status_code} body={r.text[:200]}")
    try:
        body = r.json()
        msg = str(body.get("detail", ""))
        log("D2 mensagem PT-BR com 'month'", "month" in msg.lower() or "invalid" in msg.lower(),
            f"detail={msg}")
    except Exception as e:
        log("D2 resposta JSON", False, str(e))


def run_section_E(token_tec: str):
    print("\n=== E) POST /checklists com service_type_code ===")
    payload = {
        "nome": "Teste",
        "sobrenome": "SLA",
        "placa": "TST1234",
        "telefone": "",
        "empresa": "Rastremix",
        "equipamento": "Rastreador",
        "tipo_atendimento": "Instalação",
        "service_type_code": "instalacao_com_bloqueio",
        "execution_elapsed_sec": 1500,   # 25 min — dentro dos 50 min do SLA
        "status": "rascunho",
    }
    r = requests.post(
        f"{BASE_URL}/checklists",
        json=payload,
        headers=H(token_tec),
        timeout=20,
    )
    log("E1 POST HTTP 200", r.status_code == 200,
        f"status={r.status_code} body={r.text[:400]}")
    if r.status_code != 200:
        return None
    data = r.json()
    cid = data.get("id")
    log("E2 id retornado", bool(cid), f"id={cid}")

    # GET confirmando snapshot SLA
    g = requests.get(f"{BASE_URL}/checklists/{cid}", headers=H(token_tec), timeout=20)
    log("E3 GET /checklists/{id} HTTP 200", g.status_code == 200,
        f"status={g.status_code} body={g.text[:200]}")
    if g.status_code != 200:
        return cid
    doc = g.json()
    log("E4 service_type_code == instalacao_com_bloqueio",
        doc.get("service_type_code") == "instalacao_com_bloqueio",
        f"got={doc.get('service_type_code')}")
    log("E5 service_type_name == 'Instalação C/ Bloqueio'",
        doc.get("service_type_name") == "Instalação C/ Bloqueio",
        f"got={doc.get('service_type_name')}")
    log("E6 sla_max_minutes == 50", doc.get("sla_max_minutes") == 50,
        f"got={doc.get('sla_max_minutes')}")
    log("E7 sla_base_value == 5.0", float(doc.get("sla_base_value") or 0) == 5.0,
        f"got={doc.get('sla_base_value')}")
    log("E8 sla_within == true", doc.get("sla_within") is True,
        f"got={doc.get('sla_within')}")
    return cid


def run_section_F(token_tec: str):
    print("\n=== F) POST /checklists SEM service_type_code (backward compat) ===")
    payload = {
        "nome": "Legado",
        "sobrenome": "Sem SLA",
        "placa": "LEG5678",
        "empresa": "Rastremix",
        "equipamento": "Rastreador",
        "tipo_atendimento": "Instalação",
        "status": "rascunho",
    }
    r = requests.post(f"{BASE_URL}/checklists", json=payload, headers=H(token_tec), timeout=20)
    log("F1 POST HTTP 200 sem service_type_code",
        r.status_code == 200, f"status={r.status_code} body={r.text[:400]}")
    if r.status_code != 200:
        return
    data = r.json()
    log("F2 service_type_code defaults '' ",
        (data.get("service_type_code") or "") == "",
        f"got={data.get('service_type_code')!r}")
    log("F3 service_type_name defaults '' ",
        (data.get("service_type_name") or "") == "",
        f"got={data.get('service_type_name')!r}")
    log("F4 sla_max_minutes defaults 0",
        (data.get("sla_max_minutes") or 0) == 0,
        f"got={data.get('sla_max_minutes')!r}")
    log("F5 sla_base_value defaults 0.0",
        float(data.get("sla_base_value") or 0.0) == 0.0,
        f"got={data.get('sla_base_value')!r}")
    log("F6 sla_within defaults None/null",
        data.get("sla_within") is None,
        f"got={data.get('sla_within')!r}")


def run_section_G(token_tec: str):
    print("\n=== G) Regressão leve ===")
    ep = [
        ("/auth/me", {}, 200),
        ("/gamification/meta", {}, 200),
        ("/gamification/profile", {}, 200),
        ("/inventory/me", {}, 200),
        ("/reference/service-catalog", {}, 200),
    ]
    for path, params, expected in ep:
        r = requests.get(
            f"{BASE_URL}{path}", params=params, headers=H(token_tec), timeout=20
        )
        log(f"G {path}", r.status_code == expected,
            f"status={r.status_code}")
        if path == "/auth/me" and r.status_code == 200:
            me = r.json()
            log("G /auth/me.level presente", "level" in me,
                f"keys={sorted(me.keys())[:8]}")
            log("G /auth/me.tutor_id presente (pode ser null)",
                "tutor_id" in me, f"tutor_id={me.get('tutor_id')!r}")

    def _items(resp):
        data = resp.json()
        if isinstance(data, dict):
            return data.get("items", data.get("catalog", []))
        return data if isinstance(data, list) else []

    # catalog counts
    r = requests.get(f"{BASE_URL}/reference/service-catalog",
                     headers=H(token_tec), timeout=20)
    if r.status_code == 200:
        items = _items(r)
        log("G catalog default == 11 itens",
            len(items) == 11, f"len={len(items)}")

    r = requests.get(
        f"{BASE_URL}/reference/service-catalog",
        params={"level": "junior"},
        headers=H(token_tec), timeout=20,
    )
    log("G catalog?level=junior HTTP 200", r.status_code == 200,
        f"status={r.status_code}")
    if r.status_code == 200:
        items = _items(r)
        log("G catalog?level=junior == 9 itens",
            len(items) == 9, f"len={len(items)}")


def main() -> int:
    print(f"BASE_URL = {BASE_URL}")
    print("Logging in as tecnico…")
    token_tec = login(*TECNICO)

    # A: mês atual tecnico
    run_section_A(token_tec)
    # B: junior
    run_section_B()
    # C: mês específico
    run_section_C(token_tec)
    # D: mês inválido
    run_section_D(token_tec)
    # E: POST checklists com service_type_code
    run_section_E(token_tec)
    # F: POST checklists sem service_type_code
    run_section_F(token_tec)
    # G: regressão leve
    run_section_G(token_tec)

    print("\n=== RESULT SUMMARY ===")
    ok = sum(1 for _, c, _ in results if c)
    total = len(results)
    print(f"PASS: {ok}/{total}")
    failures = [(n, e) for n, c, e in results if not c]
    if failures:
        print("\nFAILURES:")
        for name, extra in failures:
            print(f"  - {name}: {extra}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
