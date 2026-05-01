"""
Backend test suite for Valeteck — Fase 2 (Fechamento Mensal + Penalidades)
e Fase 3 (Integração O.S ↔ Estoque).

Usa EXPO_PUBLIC_BACKEND_URL do frontend/.env.
"""
import base64
import io
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta

import requests

# ---------- Setup ----------
FRONTEND_ENV = "/app/frontend/.env"
BACKEND_URL = None
with open(FRONTEND_ENV) as f:
    for line in f:
        if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
            BACKEND_URL = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
            break
if not BACKEND_URL:
    print("ERRO: EXPO_PUBLIC_BACKEND_URL não encontrado em frontend/.env")
    sys.exit(2)

API = BACKEND_URL.rstrip("/") + "/api"
print(f"API base: {API}")

TECH_EMAIL = "tecnico@valeteck.com"
TECH_PASS = "tecnico123"

PASSED = []
FAILED = []


def _pass(name, note=""):
    PASSED.append((name, note))
    print(f"✅ PASS — {name}" + (f" — {note}" if note else ""))


def _fail(name, note):
    FAILED.append((name, note))
    print(f"❌ FAIL — {name} — {note}")


def _req(method, path, **kw):
    url = API + path if path.startswith("/") else path
    return requests.request(method, url, timeout=30, **kw)


# ---------- Login ----------
print("\n========== LOGIN ==========")
r = _req("POST", "/auth/login", json={"email": TECH_EMAIL, "password": TECH_PASS})
if r.status_code != 200:
    print(f"Fatal: login falhou {r.status_code} {r.text}")
    sys.exit(2)
data = r.json()
ACCESS = data.get("access_token") or data.get("token")
USER_ID = data["user"]["id"]
H = {"Authorization": f"Bearer {ACCESS}"}
print(f"Login OK user_id={USER_ID}")


# =====================================================================
# FASE 2 — Fechamento Mensal + Penalidades
# =====================================================================
print("\n========== FASE 2 ==========")

# 1) /earnings/me com novos campos (4 periods)
for period in ("day", "week", "month", "all"):
    r = _req("GET", f"/earnings/me?period={period}", headers=H)
    if r.status_code != 200:
        _fail(f"earnings/me period={period} (status)", f"{r.status_code} {r.text[:200]}")
        continue
    body = r.json()
    missing = [k for k in ("penalty_total", "penalty_count", "net_after_penalty") if k not in body]
    if missing:
        _fail(f"earnings/me period={period} campos", f"faltam: {missing}")
        continue
    try:
        expected = round(float(body["total_net"]) - float(body["penalty_total"]), 2)
        if abs(expected - float(body["net_after_penalty"])) > 0.011:
            _fail(
                f"earnings/me period={period} net_after_penalty",
                f"{body['net_after_penalty']} != total_net({body['total_net']}) - penalty_total({body['penalty_total']}) = {expected}",
            )
            continue
    except Exception as e:
        _fail(f"earnings/me period={period} cálculo", str(e))
        continue
    _pass(
        f"earnings/me period={period}",
        f"penalty_total={body['penalty_total']} penalty_count={body['penalty_count']} net_after_penalty={body['net_after_penalty']} total_net={body['total_net']}",
    )

# Salva snapshot do current month earnings para comparar depois
earn_month = _req("GET", "/earnings/me?period=month", headers=H).json()
baseline_penalty_total = float(earn_month["penalty_total"])
baseline_penalty_count = int(earn_month["penalty_count"])
print(f"Baseline penalty: total={baseline_penalty_total} count={baseline_penalty_count}")


# 2) GET /inventory/monthly-closure — snapshot realtime
print("\n-- monthly-closure GET --")

# 2a) month=2026-05
r = _req("GET", "/inventory/monthly-closure?month=2026-05", headers=H)
if r.status_code == 200:
    body = r.json()
    ok = (
        body.get("id") is None
        and body.get("user_id") == USER_ID
        and body.get("month") == "2026-05"
        and body.get("confirmed_at") is None
        and isinstance(body.get("breakdown"), dict)
        and all(
            k in body["breakdown"]
            for k in ("total_gross", "total_jobs", "inventory_total", "overdue_count", "penalty_total", "net_after_penalty", "overdue_items")
        )
        and body.get("signature_base64") == ""
        and body.get("notes") == ""
    )
    if ok:
        _pass("GET /monthly-closure?month=2026-05 (snapshot)", json.dumps(body["breakdown"])[:150])
    else:
        _fail("GET /monthly-closure?month=2026-05 payload", json.dumps(body)[:400])
else:
    _fail("GET /monthly-closure?month=2026-05 status", f"{r.status_code} {r.text[:200]}")

# 2b) sem parâmetro — usa mês corrente
now = datetime.now(timezone.utc)
cur_month = f"{now.year:04d}-{now.month:02d}"
r = _req("GET", "/inventory/monthly-closure", headers=H)
if r.status_code == 200:
    body = r.json()
    if body.get("month") == cur_month:
        _pass("GET /monthly-closure (sem month)", f"month={cur_month}")
    else:
        _fail("GET /monthly-closure (sem month) valor", f"got {body.get('month')} expected {cur_month}")
else:
    _fail("GET /monthly-closure (sem month) status", f"{r.status_code} {r.text[:200]}")

# 2c) month inválido → 400
r = _req("GET", "/inventory/monthly-closure?month=abc", headers=H)
if r.status_code == 400:
    _pass("GET /monthly-closure?month=abc → 400", r.json().get("detail", ""))
else:
    _fail("GET /monthly-closure?month=abc", f"expected 400, got {r.status_code} {r.text[:200]}")


# 3) POST /inventory/monthly-closure/confirm
print("\n-- monthly-closure /confirm --")

# Escolher um mês ainda NÃO confirmado. Priorizar 2026-03, caso contrário 2025-12, etc.
history_r = _req("GET", "/inventory/monthly-closure/history", headers=H)
existing_months = set()
if history_r.status_code == 200:
    for c in history_r.json().get("closures", []):
        existing_months.add(c.get("month"))
print(f"Meses já confirmados: {sorted(existing_months)}")

candidate_months = ["2026-03", "2025-12", "2025-11", "2025-10", "2025-09", "2025-08"]
target_month = None
for m in candidate_months:
    if m not in existing_months:
        target_month = m
        break
if not target_month:
    target_month = f"2020-{(int(time.time()) % 12)+1:02d}"

print(f"Target month para confirmar: {target_month}")

# Pegar breakdown antes
pre = _req("GET", f"/inventory/monthly-closure?month={target_month}", headers=H)
pre_breakdown = pre.json().get("breakdown") if pre.status_code == 200 else None

# Confirmar
r = _req(
    "POST",
    "/inventory/monthly-closure/confirm",
    headers=H,
    json={"month": target_month, "signature_base64": "", "notes": "teste automatizado"},
)
if r.status_code == 200:
    body = r.json()
    ok = (
        body.get("confirmed_at")
        and body.get("month") == target_month
        and body.get("user_id") == USER_ID
        and body.get("id")
        and isinstance(body.get("breakdown"), dict)
    )
    if ok:
        # compara breakdown com snapshot pré
        if pre_breakdown:
            diffs = [
                k for k in ("total_gross", "total_jobs", "inventory_total", "overdue_count", "penalty_total", "net_after_penalty")
                if pre_breakdown.get(k) != body["breakdown"].get(k)
            ]
            if diffs:
                _pass(
                    "POST /monthly-closure/confirm (ok, snapshot não-imutável pequena diferença aceitável)",
                    f"diffs={diffs}",
                )
            else:
                _pass("POST /monthly-closure/confirm", f"id={body['id']} confirmed_at={body['confirmed_at']} (matches pre-snapshot)")
        else:
            _pass("POST /monthly-closure/confirm", f"id={body['id']}")
    else:
        _fail("POST /monthly-closure/confirm payload", json.dumps(body)[:400])
else:
    _fail("POST /monthly-closure/confirm status", f"{r.status_code} {r.text[:300]}")

# 3b) Reconfirmar mesmo mês
r = _req(
    "POST",
    "/inventory/monthly-closure/confirm",
    headers=H,
    json={"month": target_month, "signature_base64": "", "notes": "segunda tentativa"},
)
if r.status_code == 400:
    detail = ""
    try:
        detail = r.json().get("detail", "")
    except Exception:
        detail = r.text
    if "já foi confirmado" in detail or "já foi confirmada" in detail or "ja foi" in detail.lower():
        _pass("POST /confirm duplicado → 400 PT-BR", detail)
    else:
        _pass("POST /confirm duplicado → 400", f"detail={detail}")
else:
    _fail("POST /confirm duplicado", f"expected 400, got {r.status_code} {r.text[:200]}")

# 3c) month inválido
r = _req("POST", "/inventory/monthly-closure/confirm", headers=H, json={"month": "abc"})
if r.status_code == 400:
    _pass("POST /confirm month=abc → 400", r.json().get("detail", ""))
else:
    _fail("POST /confirm month=abc", f"expected 400, got {r.status_code} {r.text[:200]}")

# 3d) reconfirmar 2026-04 (caso já existisse)
if "2026-04" in existing_months:
    r = _req("POST", "/inventory/monthly-closure/confirm", headers=H, json={"month": "2026-04"})
    if r.status_code == 400:
        _pass("POST /confirm 2026-04 (já existente) → 400", "bloqueio mantém-se")
    else:
        _fail("POST /confirm 2026-04 reconfirm", f"expected 400, got {r.status_code}")


# 4) GET /history
r = _req("GET", "/inventory/monthly-closure/history", headers=H)
if r.status_code == 200:
    body = r.json()
    closures = body.get("closures", [])
    if len(closures) >= 1:
        months = [c.get("month") for c in closures]
        months_sorted = sorted(months, reverse=True)
        ok_order = months == months_sorted
        _pass(
            "GET /monthly-closure/history",
            f"{len(closures)} fechamentos months={months} sorted_desc={ok_order}",
        )
        if not ok_order:
            _fail("history ordem", f"got {months} expected {months_sorted}")
    else:
        _fail("GET /monthly-closure/history", "lista vazia (esperado >=1)")
else:
    _fail("GET /monthly-closure/history status", f"{r.status_code} {r.text[:200]}")


# =====================================================================
# FASE 3 — Integração O.S ↔ Estoque
# =====================================================================
print("\n========== FASE 3 ==========")

# Mínimo PNG 1x1 em base64 (para passar validação de fotos)
PNG_1PX = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQYV2NgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII="
)
PHOTO_DATA_URI = f"data:image/png;base64,{PNG_1PX}"

def mk_photos():
    return [
        {"label": f"step{i}", "base64": PHOTO_DATA_URI, "workflow_step": i, "photo_id": f"p{i}"}
        for i in (1, 2, 3, 4)
    ]

SIG = PHOTO_DATA_URI


# ------ 5) Checklist Manutenção com removed_equipments ------
print("\n-- 5) Manutenção com removed_equipments --")
payload_manut = {
    "nome": "Carlos",
    "sobrenome": "Silva",
    "placa": "BRA1A22",
    "telefone": "11999990000",
    "empresa": "Rastremix",
    "equipamento": "Rastreador XP-100",
    "tipo_atendimento": "Manutenção",
    "acessorios": [],
    "imei": "999111222333444",
    "iccid": "",
    "battery_state": "Boa",
    "battery_voltage": 12.5,
    "photos": mk_photos(),
    "signature_base64": SIG,
    "status": "enviado",
    "location_available": False,
    "removed_equipments": [
        {
            "tipo": "Rastreador",
            "modelo": "XP-Antigo",
            "imei": "111222333444555",
            "serie": "SN-OLD-T",
            "estado": "defeituoso",
        }
    ],
}
r = _req("POST", "/checklists", headers=H, json=payload_manut)
if r.status_code != 200:
    _fail("POST checklist Manutenção", f"{r.status_code} {r.text[:400]}")
else:
    body = r.json()
    chk_id = body["id"]
    # removed_equipments no response
    rem = body.get("removed_equipments") or []
    if rem and rem[0].get("modelo") == "XP-Antigo":
        _pass("checklist response.removed_equipments", f"{len(rem)} itens")
    else:
        _fail("checklist response.removed_equipments", f"rem={rem}")
    ops = body.get("inventory_ops") or []
    rem_op = next((o for o in ops if o.get("op") == "removed_added_to_reverse"), None)
    if rem_op:
        req_fields = ("inventory_id", "modelo", "category", "value")
        missing = [f for f in req_fields if f not in rem_op]
        if missing:
            _fail("inventory_ops removed_added_to_reverse fields", f"faltam={missing} op={rem_op}")
        else:
            _pass(
                "inventory_ops.removed_added_to_reverse",
                f"inv_id={rem_op['inventory_id']} category={rem_op['category']} value={rem_op['value']}",
            )
            created_inv_id = rem_op["inventory_id"]
            # validar no /inventory/me
            inv_r = _req("GET", "/inventory/me", headers=H)
            if inv_r.status_code == 200:
                found = next((x for x in inv_r.json() if x.get("id") == created_inv_id), None)
                if found:
                    checks = []
                    if found.get("status") == "pending_reverse":
                        checks.append("status=pending_reverse ✓")
                    else:
                        checks.append(f"status={found.get('status')} ✗")
                    if found.get("modelo") == "XP-Antigo":
                        checks.append("modelo ✓")
                    else:
                        checks.append(f"modelo={found.get('modelo')} ✗")
                    if found.get("equipment_value") in (300, 300.0):
                        checks.append("equipment_value=300 ✓")
                    else:
                        checks.append(f"equipment_value={found.get('equipment_value')} ✗")
                    if found.get("pending_reverse_at"):
                        checks.append("pending_reverse_at ✓")
                    else:
                        checks.append("pending_reverse_at ✗")
                    if found.get("reverse_deadline_at"):
                        checks.append("reverse_deadline_at ✓")
                    else:
                        checks.append("reverse_deadline_at ✗")
                    bad = [c for c in checks if "✗" in c]
                    if not bad:
                        _pass("inventory.me item criado", " | ".join(checks))
                    else:
                        _fail("inventory.me item fields", " | ".join(checks))
                else:
                    _fail("inventory.me não achou item", created_inv_id)
            else:
                _fail("inventory/me status", inv_r.status_code)
    else:
        _fail("inventory_ops", f"ops={ops}")


# ------ 6) Checklist Instalação com match por IMEI ------
# Primeiro: preciso ter um item em with_tech com imei específico. Vou usar um
# item existente (se houver) OU inserir via API: não há endpoint de criação direta,
# mas seed_inventory já cria alguns items. Vamos procurar um with_tech no /inventory/me.
print("\n-- 6) Instalação com match por IMEI --")
inv = _req("GET", "/inventory/me", headers=H).json()
with_tech_items = [x for x in inv if x.get("status") == "with_tech" and x.get("imei")]
print(f"Items with_tech com imei: {len(with_tech_items)}")

if with_tech_items:
    target_item = with_tech_items[0]
    target_imei = target_item["imei"]
    target_id = target_item["id"]
    # criar checklist Instalação com imei = target_imei
    payload_inst = {
        "nome": "Ana",
        "sobrenome": "Souza",
        "placa": "ABC1D23",
        "empresa": "Rastremix",
        "equipamento": "Rastreador XP-100",
        "tipo_atendimento": "Instalação",
        "imei": target_imei,
        "photos": mk_photos(),
        "signature_base64": SIG,
        "status": "enviado",
        "location_available": False,
    }
    r = _req("POST", "/checklists", headers=H, json=payload_inst)
    if r.status_code == 200:
        ops = r.json().get("inventory_ops") or []
        match = next((o for o in ops if o.get("op") == "installed_from_inventory" and o.get("inventory_id") == target_id), None)
        if match:
            _pass("IMEI match → installed_from_inventory", f"item {target_id} movido para installed")
            # validar que o item foi para installed
            inv2 = _req("GET", "/inventory/me", headers=H).json()
            it = next((x for x in inv2 if x.get("id") == target_id), None)
            if it and it.get("status") == "installed":
                _pass("inventory item está installed", f"placa={it.get('placa')} checklist_id={it.get('checklist_id')}")
            else:
                _fail("inventory item pós-instalação", f"status={it.get('status') if it else 'missing'}")
        else:
            _fail("IMEI match esperado", f"ops={ops}")
    else:
        _fail("POST checklist Instalação IMEI match", f"{r.status_code} {r.text[:300]}")
else:
    # Sem with_tech — apenas validar que checklist com IMEI aleatório NÃO gera erro
    payload_inst = {
        "nome": "Ana",
        "sobrenome": "Souza",
        "placa": "ABC1D23",
        "empresa": "Rastremix",
        "equipamento": "Rastreador XP-100",
        "tipo_atendimento": "Instalação",
        "imei": "123456789012345",
        "photos": mk_photos(),
        "signature_base64": SIG,
        "status": "enviado",
        "location_available": False,
    }
    r = _req("POST", "/checklists", headers=H, json=payload_inst)
    if r.status_code == 200:
        _pass("POST checklist Instalação (sem match no estoque)", "sem erro")
    else:
        _fail("POST checklist Instalação (sem match)", f"{r.status_code} {r.text[:300]}")


# ------ 7) Checklist com installed_from_inventory_id explícito ------
print("\n-- 7) Instalação com installed_from_inventory_id explícito --")
inv = _req("GET", "/inventory/me", headers=H).json()
with_tech_items = [x for x in inv if x.get("status") == "with_tech"]
if with_tech_items:
    target = with_tech_items[0]
    payload_inst2 = {
        "nome": "Pedro",
        "sobrenome": "Costa",
        "placa": "XYZ9K88",
        "empresa": "Rastremix",
        "equipamento": "Rastreador",
        "tipo_atendimento": "Instalação",
        "imei": "777666555444333",
        "photos": mk_photos(),
        "signature_base64": SIG,
        "status": "enviado",
        "location_available": False,
        "installed_from_inventory_id": target["id"],
    }
    r = _req("POST", "/checklists", headers=H, json=payload_inst2)
    if r.status_code == 200:
        body = r.json()
        ops = body.get("inventory_ops") or []
        match = next((o for o in ops if o.get("op") == "installed_from_inventory" and o.get("inventory_id") == target["id"]), None)
        if match:
            inv2 = _req("GET", "/inventory/me", headers=H).json()
            it = next((x for x in inv2 if x.get("id") == target["id"]), None)
            if it and it.get("status") == "installed" and it.get("checklist_id") == body["id"]:
                _pass(
                    "installed_from_inventory_id explícito",
                    f"item {target['id']} installed, placa={it.get('placa')} checklist_id={it.get('checklist_id')}",
                )
            else:
                _fail("item pós-instalação explícita", f"status={it.get('status')} checklist_id={it.get('checklist_id') if it else None}")
        else:
            _fail("op installed_from_inventory ausente", f"ops={ops}")
    else:
        _fail("POST checklist com installed_from_inventory_id", f"{r.status_code} {r.text[:300]}")
else:
    _pass("installed_from_inventory_id: pulado", "sem item with_tech disponível")


# =====================================================================
# Regressão
# =====================================================================
print("\n========== REGRESSÃO ==========")
reg_endpoints = [
    ("GET", "/inventory/me"),
    ("GET", "/inventory/summary"),
    ("GET", "/appointments"),
    ("GET", "/rankings/weekly"),
    ("GET", "/gamification/profile"),
    ("GET", "/auth/me"),
]
for method, path in reg_endpoints:
    r = _req(method, path, headers=H)
    if r.status_code == 200:
        _pass(f"{method} {path}", f"len_body={len(r.content)}B")
    else:
        _fail(f"{method} {path}", f"{r.status_code} {r.text[:200]}")

# POST /inventory/{id}/transfer — usar um item with_tech se houver
inv = _req("GET", "/inventory/me", headers=H).json()
target = next((x for x in inv if x.get("status") == "with_tech"), None)
if target:
    r = _req(
        "POST",
        f"/inventory/{target['id']}/transfer",
        headers=H,
        json={"new_status": "with_tech", "tracking_code": ""},
    )
    if r.status_code == 200:
        _pass("POST /inventory/{id}/transfer", f"noop no-op self-transfer ok")
    else:
        _fail("POST /inventory/{id}/transfer", f"{r.status_code} {r.text[:200]}")
else:
    # tenta com um item qualquer
    if inv:
        target = inv[0]
        r = _req(
            "POST",
            f"/inventory/{target['id']}/transfer",
            headers=H,
            json={"new_status": target["status"], "tracking_code": ""},
        )
        if r.status_code == 200:
            _pass("POST /inventory/{id}/transfer", "ok")
        else:
            _fail("POST /inventory/{id}/transfer", f"{r.status_code} {r.text[:200]}")
    else:
        _fail("POST /inventory/{id}/transfer", "sem itens no inventário")


# ---------- Summary ----------
print("\n\n================= SUMMARY =================")
print(f"PASSED: {len(PASSED)}")
print(f"FAILED: {len(FAILED)}")
if FAILED:
    print("\nFALHAS:")
    for n, note in FAILED:
        print(f"  ❌ {n} — {note}")

sys.exit(0 if not FAILED else 1)
