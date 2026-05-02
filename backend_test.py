"""Valeteck v14 — Fase 3A (Anti-fraude SLA server-side) + Fase 3B
(Motor Financeiro Pós-Aprovação) — Backend smoke test.

Base URL: https://installer-track-1.preview.emergentagent.com/api
"""
import os
import json
import time
import sys
from datetime import datetime

import requests

# ---- Config ----
FRONTEND_ENV = "/app/frontend/.env"
BASE_URL = None
with open(FRONTEND_ENV) as fh:
    for line in fh:
        if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().strip('"') + "/api"
if not BASE_URL:
    raise SystemExit("EXPO_PUBLIC_BACKEND_URL ausente em frontend/.env")
print(f"🔗 Base URL: {BASE_URL}")

USERS = {
    "admin": ("admin@valeteck.com", "admin123"),
    "tecnico": ("tecnico@valeteck.com", "tecnico123"),
    "junior": ("junior@valeteck.com", "junior123"),
    "n2": ("n2@valeteck.com", "n2tech123"),
}

results = []   # [(nome, ok, info)]


def log(name, ok, info=""):
    mark = "✅" if ok else "❌"
    results.append((name, ok, info))
    print(f"  {mark} {name}" + (f" — {info}" if info else ""))


def login(email, pwd):
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": pwd}, timeout=20)
    r.raise_for_status()
    return r.json()


def H(token):
    return {"Authorization": f"Bearer {token}"}


# =====================================================================
# SETUP — login de todos os papéis
# =====================================================================
print("\n===== SETUP =====")
tokens = {}
ids = {}
for key, (email, pwd) in USERS.items():
    try:
        data = login(email, pwd)
        tokens[key] = data["access_token"]
        ids[key] = data["user"]["id"]
        log(f"Login {key} ({email})", True,
            f"level={data['user'].get('level')} id={data['user']['id'][:8]}…")
    except Exception as e:
        log(f"Login {key} ({email})", False, str(e))
        sys.exit(1)

admin_tok = tokens["admin"]
tec_tok = tokens["tecnico"]
jun_tok = tokens["junior"]
n2_tok = tokens["n2"]


def create_draft(token, plate="AAA0001", tipo="Instalação"):
    payload = {
        "nome": "Cliente",
        "sobrenome": "Teste",
        "placa": plate,
        "empresa": "Rastremix",
        "equipamento": "Módulo",
        "tipo_atendimento": tipo,
        "status": "rascunho",
    }
    r = requests.post(f"{BASE_URL}/checklists", json=payload, headers=H(token), timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"create_draft HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


# =====================================================================
# A) Fase 3A — Fluxo completo instalação (tecnico N1)
# =====================================================================
print("\n===== A) Fase 3A — Fluxo completo instalação =====")
try:
    draft = create_draft(tec_tok, plate="AAA0001", tipo="Instalação")
    cid_A = draft["id"]
    log("A1 POST /checklists rascunho", True, f"id={cid_A[:8]}…")

    r = requests.post(
        f"{BASE_URL}/checklists/{cid_A}/send-initial",
        json={"service_type_code": "instalacao_com_bloqueio"},
        headers=H(tec_tok), timeout=20,
    )
    ok = r.status_code == 200
    body = r.json() if ok else {}
    log("A2 send-initial HTTP 200", ok, f"status={r.status_code}" + (f" body={r.text[:200]}" if not ok else ""))
    if ok:
        log("A2.a phase=awaiting_equipment_photo", body.get("phase") == "awaiting_equipment_photo",
            f"phase={body.get('phase')}")
        log("A2.b checklist_sent_at preenchido", bool(body.get("checklist_sent_at")),
            f"sent_at={body.get('checklist_sent_at')}")
        log("A2.c sla_max_minutes=50", body.get("sla_max_minutes") == 50,
            f"sla_max={body.get('sla_max_minutes')}")

    r = requests.post(
        f"{BASE_URL}/checklists/{cid_A}/equipment-photo",
        json={"photo_base64": "data:image/png;base64,iVBORw0KGgo="},
        headers=H(tec_tok), timeout=20,
    )
    ok = r.status_code == 200
    body = r.json() if ok else {}
    log("A3 equipment-photo HTTP 200", ok, f"status={r.status_code}" + (f" body={r.text[:200]}" if not ok else ""))
    if ok:
        log("A3.a phase=in_execution", body.get("phase") == "in_execution", f"phase={body.get('phase')}")
        delay = body.get("equipment_photo_delay_sec")
        log("A3.b equipment_photo_delay_sec int >=0",
            isinstance(delay, int) and delay >= 0, f"delay={delay}")
        log("A3.c equipment_photo_flag=false (foto rápida)",
            body.get("equipment_photo_flag") is False, f"flag={body.get('equipment_photo_flag')}")

    r = requests.post(
        f"{BASE_URL}/checklists/{cid_A}/finalize",
        headers=H(tec_tok), timeout=20,
    )
    ok = r.status_code == 200
    body = r.json() if ok else {}
    log("A4 finalize HTTP 200", ok, f"status={r.status_code}" + (f" body={r.text[:200]}" if not ok else ""))
    if ok:
        log("A4.a phase=finalized", body.get("phase") == "finalized", f"phase={body.get('phase')}")
        total_sec = body.get("sla_total_sec")
        log("A4.b sla_total_sec int", isinstance(total_sec, int), f"sla_total_sec={total_sec}")
        log("A4.c sla_within=true (<50min)", body.get("sla_within") is True,
            f"sla_within={body.get('sla_within')}")
except Exception as e:
    log("A (fluxo)", False, str(e))


# =====================================================================
# B) Fase 3A — Regras de erro
# =====================================================================
print("\n===== B) Fase 3A — Regras de erro =====")

# B1) service_type_code inválido → 400
try:
    d = create_draft(tec_tok, plate="BBB0001")
    r = requests.post(
        f"{BASE_URL}/checklists/{d['id']}/send-initial",
        json={"service_type_code": "inexistente"}, headers=H(tec_tok), timeout=20,
    )
    log("B1 service_type_code inválido → 400", r.status_code == 400,
        f"got={r.status_code} {r.text[:160]}")
except Exception as e:
    log("B1", False, str(e))

# B2) N1 tentando acessório → 403
try:
    d = create_draft(tec_tok, plate="CCC0001")
    r = requests.post(
        f"{BASE_URL}/checklists/{d['id']}/send-initial",
        json={"service_type_code": "acessorio_smart_control"},
        headers=H(tec_tok), timeout=20,
    )
    ok_code = r.status_code == 403
    msg_ok = "N2" in (r.text or "")
    log("B2 N1 acessório → 403", ok_code,
        f"got={r.status_code} body={r.text[:180]}")
    log("B2.a mensagem cita N2", msg_ok, f"body={r.text[:160]}")
except Exception as e:
    log("B2", False, str(e))

# B3) Re-iniciar checklist já iniciado → 409
try:
    d = create_draft(tec_tok, plate="DDD0001")
    r1 = requests.post(
        f"{BASE_URL}/checklists/{d['id']}/send-initial",
        json={"service_type_code": "desinstalacao"}, headers=H(tec_tok), timeout=20,
    )
    log("B3.setup primeiro send-initial", r1.status_code == 200, f"got={r1.status_code}")
    r2 = requests.post(
        f"{BASE_URL}/checklists/{d['id']}/send-initial",
        json={"service_type_code": "desinstalacao"}, headers=H(tec_tok), timeout=20,
    )
    log("B3 re-iniciar → 409", r2.status_code == 409,
        f"got={r2.status_code} body={r2.text[:180]}")
except Exception as e:
    log("B3", False, str(e))

# B4) finalize sem send-initial → 409
try:
    d = create_draft(tec_tok, plate="EEE0001")
    r = requests.post(f"{BASE_URL}/checklists/{d['id']}/finalize", headers=H(tec_tok), timeout=20)
    log("B4 finalize sem send-initial → 409", r.status_code == 409,
        f"got={r.status_code} body={r.text[:180]}")
except Exception as e:
    log("B4", False, str(e))

# B5) equipment-photo sem send-initial → 409
try:
    d = create_draft(tec_tok, plate="FFF0001")
    r = requests.post(
        f"{BASE_URL}/checklists/{d['id']}/equipment-photo",
        json={"photo_base64": "data:image/png;base64,iVBORw0KGgo="},
        headers=H(tec_tok), timeout=20,
    )
    log("B5 equipment-photo sem send-initial → 409", r.status_code == 409,
        f"got={r.status_code} body={r.text[:180]}")
except Exception as e:
    log("B5", False, str(e))


# =====================================================================
# C) Fase 3A — Categoria não-instalação: desinstalacao
# =====================================================================
print("\n===== C) Fase 3A — Desinstalação direto em in_execution =====")
try:
    d = create_draft(tec_tok, plate="GGG0001", tipo="Desinstalação")
    r = requests.post(
        f"{BASE_URL}/checklists/{d['id']}/send-initial",
        json={"service_type_code": "desinstalacao"},
        headers=H(tec_tok), timeout=20,
    )
    ok = r.status_code == 200
    body = r.json() if ok else {}
    log("C1 send-initial desinstalacao HTTP 200", ok, f"status={r.status_code}")
    if ok:
        log("C2 phase=in_execution direto",
            body.get("phase") == "in_execution",
            f"phase={body.get('phase')}")
except Exception as e:
    log("C", False, str(e))


# =====================================================================
# D) Fase 3A — N2 + acessório (categoria acessorio NÃO ∈ INSTALL_CATEGORIES)
# =====================================================================
print("\n===== D) Fase 3A — N2 + acessorio_smart_control → in_execution direto =====")
try:
    d = create_draft(n2_tok, plate="HHH0001", tipo="Acessório")
    r = requests.post(
        f"{BASE_URL}/checklists/{d['id']}/send-initial",
        json={"service_type_code": "acessorio_smart_control"},
        headers=H(n2_tok), timeout=20,
    )
    ok = r.status_code == 200
    body = r.json() if ok else {}
    log("D1 send-initial acessorio (n2) HTTP 200", ok,
        f"status={r.status_code} body={r.text[:200]}")
    if ok:
        # categoria 'acessorio' não está em {instalacao, telemetria} → phase=in_execution direto
        log("D2 phase=in_execution direto (acessório ∉ INSTALL_CATEGORIES)",
            body.get("phase") == "in_execution",
            f"phase={body.get('phase')}")
except Exception as e:
    log("D", False, str(e))


# =====================================================================
# E) Fase 3B — Motor Financeiro via /admin/approve
# =====================================================================
print("\n===== E) Fase 3B — Motor Financeiro /admin/approve =====")

try:
    r = requests.get(f"{BASE_URL}/admin/pending-approvals", headers=H(admin_tok), timeout=20)
    ok = r.status_code == 200
    body = r.json() if ok else {}
    pending = body.get("pending", [])
    log("E1 GET /admin/pending-approvals", ok, f"count={len(pending)}")

    if not pending:
        log("E2 Aprovar OS do pool",
            True, "⚠️ observação: pool vazio — nada a aprovar")
    else:
        expected_keys = [
            "comp_base_value", "comp_sla_cut", "comp_warranty_zero",
            "comp_return_flagged", "comp_final_value",
            "comp_penalty_on_original", "comp_level_applied",
        ]
        to_test = pending[:2]
        approved_any = False
        for idx, item in enumerate(to_test):
            cid = item["id"]
            try:
                r2 = requests.post(
                    f"{BASE_URL}/admin/checklists/{cid}/approve",
                    headers=H(admin_tok), timeout=30,
                )
                ok2 = r2.status_code == 200
                body2 = r2.json() if ok2 else {}
                log(f"E2.{idx+1} approve {cid[:8]}… HTTP 200", ok2,
                    f"status={r2.status_code}" + (f" body={r2.text[:260]}" if not ok2 else ""))
                if ok2:
                    approved_any = True
                    comp = body2.get("compensation") or {}
                    missing = [k for k in expected_keys if k not in comp]
                    log(f"E2.{idx+1}.a compensation contém todas as chaves", not missing,
                        f"missing={missing} got={list(comp.keys())}")
                    msg = body2.get("message", "")
                    log(f"E2.{idx+1}.b message contém 💰",
                        "💰" in msg,
                        f"message={msg!r}")
                    final_v = comp.get("comp_final_value")
                    ok_val = False
                    if isinstance(final_v, (int, float)):
                        ok_val = f"{final_v:.2f}" in msg
                    log(f"E2.{idx+1}.c mensagem cita valor final",
                        ok_val,
                        f"final_v={final_v} msg={msg!r}")
            except Exception as e:
                log(f"E2.{idx+1} approve", False, str(e))

        if not approved_any:
            log("E3 Pelo menos 1 aprovação concluída", False,
                "Nenhuma aprovação teve sucesso — ver logs acima")
except Exception as e:
    log("E", False, str(e))


# =====================================================================
# F) Fase 3B — Extrato /statement/me com penalties
# =====================================================================
print("\n===== F) Fase 3B — /statement/me agregado =====")
try:
    r = requests.get(f"{BASE_URL}/statement/me", headers=H(tec_tok), timeout=20)
    ok = r.status_code == 200
    body = r.json() if ok else {}
    log("F1 GET /statement/me", ok, f"status={r.status_code}")
    if ok:
        required = ["gross_estimated", "penalty_total", "penalty_count", "net_estimated"]
        missing = [k for k in required if k not in body]
        log("F2 chaves obrigatórias presentes", not missing,
            f"missing={missing} has={[k for k in required if k in body]}")

        log("F3 gross_estimated é float",
            isinstance(body.get("gross_estimated"), (int, float)),
            f"type={type(body.get('gross_estimated')).__name__} v={body.get('gross_estimated')}")
        log("F4 penalty_total é float",
            isinstance(body.get("penalty_total"), (int, float)),
            f"type={type(body.get('penalty_total')).__name__} v={body.get('penalty_total')}")
        log("F5 penalty_count é int",
            isinstance(body.get("penalty_count"), int),
            f"type={type(body.get('penalty_count')).__name__} v={body.get('penalty_count')}")

        gross = float(body.get("gross_estimated", 0))
        pen = float(body.get("penalty_total", 0))
        net = float(body.get("net_estimated", 0))
        expected_net = round(gross - pen, 2)
        log("F6 net_estimated == gross - penalty_total",
            abs(net - expected_net) < 0.02,
            f"gross={gross} penalty={pen} net={net} expected={expected_net}")
except Exception as e:
    log("F", False, str(e))


# =====================================================================
# G) Regressão
# =====================================================================
print("\n===== G) Regressão =====")

try:
    r = requests.get(f"{BASE_URL}/auth/me", headers=H(tec_tok), timeout=20)
    ok = r.status_code == 200
    body = r.json() if ok else {}
    log("G1 GET /auth/me 200", ok, f"status={r.status_code}")
    if ok:
        log("G1.a inclui level", "level" in body, f"level={body.get('level')}")
        log("G1.b inclui tutor_id", "tutor_id" in body, f"tutor_id={body.get('tutor_id')}")
except Exception as e:
    log("G1", False, str(e))

try:
    r = requests.get(f"{BASE_URL}/gamification/meta", headers=H(tec_tok), timeout=20)
    log("G2 GET /gamification/meta 200", r.status_code == 200,
        f"status={r.status_code}")
except Exception as e:
    log("G2", False, str(e))

try:
    r = requests.get(f"{BASE_URL}/reference/service-catalog", headers=H(tec_tok), timeout=20)
    ok = r.status_code == 200
    body = r.json() if ok else {}
    if isinstance(body, list):
        items = body
    else:
        items = body.get("items", [])
    log("G3 GET /reference/service-catalog 200", ok, f"status={r.status_code}")
    log("G3.a 11 items", len(items) == 11, f"count={len(items)}")
except Exception as e:
    log("G3", False, str(e))

try:
    r = requests.get(f"{BASE_URL}/reference/service-catalog?level=n1", headers=H(tec_tok), timeout=20)
    ok = r.status_code == 200
    body = r.json() if ok else {}
    if isinstance(body, list):
        items = body
    else:
        items = body.get("items", [])
    log("G4 GET /reference/service-catalog?level=n1 200", ok, f"status={r.status_code}")
    log("G4.a 9 items (sem acessórios)", len(items) == 9, f"count={len(items)}")
    has_acess = any(it.get("category") == "acessorio" for it in items)
    log("G4.b nenhum item com category=acessorio", not has_acess, f"has_acessorio={has_acess}")
except Exception as e:
    log("G4", False, str(e))


# =====================================================================
# SUMMARY
# =====================================================================
print("\n" + "=" * 70)
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
print(f"RESULTADO: {passed}/{len(results)} PASS  |  {failed} FALHAS")
if failed:
    print("\n❌ FALHAS:")
    for n, ok, info in results:
        if not ok:
            print(f"  - {n}: {info}")
print("=" * 70)
sys.exit(0 if failed == 0 else 1)
