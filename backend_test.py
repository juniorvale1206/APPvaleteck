"""Backend tests for Valeteck v11 (P0+P1 refactor).

Covers:
- Auth (login, /me, refresh rotation, logout, invalid refresh, access-type enforcement)
- Rate limiting on /auth/login
- Preserved endpoints (appointments, reference, inventory, device, earnings, rankings, gamification)
- Checklists CRUD + send-validation + PDF
- Health + root
- Partner webhook (valid + invalid secret)
"""
from __future__ import annotations

import base64
import io
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# --------------------------------------------------------------------------------------
# Base URL — always external /api via EXPO_PUBLIC_BACKEND_URL
# --------------------------------------------------------------------------------------
FRONTEND_ENV = Path("/app/frontend/.env")
BASE_URL: Optional[str] = None
for line in FRONTEND_ENV.read_text().splitlines():
    if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
        BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
        break

assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL not found in /app/frontend/.env"
API = f"{BASE_URL}/api"

TECH_EMAIL = "tecnico@valeteck.com"
TECH_PASSWORD = "tecnico123"
PARTNER_SECRET = "valeteck-partner-dev-secret"

# --------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------
RESULTS: List[Dict[str, Any]] = []


def record(name: str, ok: bool, detail: str = ""):
    tag = "PASS" if ok else "FAIL"
    RESULTS.append({"name": name, "ok": ok, "detail": detail})
    line = f"[{tag}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)


def req(method: str, path: str, **kw) -> requests.Response:
    url = path if path.startswith("http") else f"{API}{path}"
    kw.setdefault("timeout", 30)
    return requests.request(method, url, **kw)


# Simple 1x1 transparent PNG
_ONE_PX_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
)


def png_data_uri() -> str:
    return f"data:image/png;base64,{_ONE_PX_PNG_B64}"


# --------------------------------------------------------------------------------------
# 1) AUTH
# --------------------------------------------------------------------------------------
def test_auth_flow() -> Dict[str, str]:
    tokens: Dict[str, str] = {}

    # login
    r = req("POST", "/auth/login", json={"email": TECH_EMAIL, "password": TECH_PASSWORD})
    ok = r.status_code == 200
    body = r.json() if ok else {}
    must = ["token", "access_token", "refresh_token", "token_type", "expires_in", "user"]
    missing = [k for k in must if k not in body]
    shape_ok = ok and not missing and body.get("token_type") == "Bearer" and body.get("expires_in") == 1800
    record(
        "auth.login returns access+refresh tokens (expires_in=1800, type=Bearer)",
        shape_ok,
        "" if shape_ok else f"status={r.status_code} missing={missing} body_keys={list(body.keys())[:10]}",
    )
    if not shape_ok:
        return tokens
    tokens["access"] = body["access_token"]
    tokens["refresh"] = body["refresh_token"]
    tokens["user_id"] = body["user"]["id"]

    # /me with access
    r = req("GET", "/auth/me", headers={"Authorization": f"Bearer {tokens['access']}"})
    record(
        "auth.me with access_token → 200",
        r.status_code == 200 and r.json().get("email") == TECH_EMAIL,
        "" if r.status_code == 200 else f"status={r.status_code} body={r.text[:200]}",
    )

    # /me with refresh_token (type=refresh) must be 401
    r = req("GET", "/auth/me", headers={"Authorization": f"Bearer {tokens['refresh']}"})
    record(
        "auth.me with refresh_token → 401 (wrong token type)",
        r.status_code == 401,
        f"status={r.status_code}",
    )

    # refresh rotates
    time.sleep(1.1)  # ensure new JWT iat/exp (second-level resolution)
    r = req("POST", "/auth/refresh", json={"refresh_token": tokens["refresh"]})
    ok = r.status_code == 200
    body2 = r.json() if ok else {}
    rotated = (
        ok
        and body2.get("access_token")
        and body2.get("refresh_token")
        and body2["access_token"] != tokens["access"]
        and body2["refresh_token"] != tokens["refresh"]
        and body2.get("expires_in") == 1800
    )
    record(
        "auth.refresh returns new rotated access+refresh pair (expires_in=1800)",
        bool(rotated),
        "" if rotated else f"status={r.status_code} body={r.text[:300]}",
    )
    if rotated:
        tokens["access"] = body2["access_token"]
        tokens["refresh"] = body2["refresh_token"]

    # invalid refresh
    r = req("POST", "/auth/refresh", json={"refresh_token": "obviously-not-a-token"})
    record(
        "auth.refresh with invalid token → 401",
        r.status_code == 401,
        f"status={r.status_code}",
    )

    # logout
    r = req("POST", "/auth/logout", headers={"Authorization": f"Bearer {tokens['access']}"})
    record("auth.logout → 200", r.status_code == 200, f"status={r.status_code}")

    return tokens


# --------------------------------------------------------------------------------------
# 2) RATE LIMITING
# --------------------------------------------------------------------------------------
def test_rate_limit_login():
    """13 rapid POSTs to /auth/login — at least one must be 429.

    Uses a persistent Session so the TCP connection is reused — SlowAPI keys
    by `request.client.host` and a shared connection guarantees same key.
    """
    # wait ~65s to ensure a fresh 10/min window from whatever earlier tests did
    time.sleep(65)
    s = requests.Session()
    statuses: List[int] = []
    for i in range(13):
        r = s.post(
            f"{API}/auth/login",
            json={"email": f"rl-burst-{i}@valeteck.com", "password": "wrong"},
            timeout=10,
        )
        statuses.append(r.status_code)
    has_429 = any(st == 429 for st in statuses)
    record(
        "rate_limit: /auth/login returns 429 after burst (>10/min)",
        has_429,
        f"statuses={statuses}",
    )


# --------------------------------------------------------------------------------------
# 3) PRESERVED ENDPOINTS
# --------------------------------------------------------------------------------------
def test_reference_endpoints(_tokens):
    # these are public (no auth) in reference.py
    endpoints = {
        "companies": ("/reference/companies", "companies"),
        "equipments": ("/reference/equipments", "equipments"),
        "accessories": ("/reference/accessories", "accessories"),
        "service-types": ("/reference/service-types", "service_types"),
        "battery-states": ("/reference/battery-states", "battery_states"),
        "problems": ("/reference/problems", None),  # returns {client,technician}
    }
    for name, (path, key) in endpoints.items():
        r = req("GET", path)
        ok = r.status_code == 200
        body = r.json() if ok else {}
        if key:
            ok = ok and isinstance(body.get(key), list) and len(body[key]) > 0
        else:
            ok = ok and isinstance(body.get("client"), list) and isinstance(body.get("technician"), list)
        record(
            f"reference.{name}",
            ok,
            "" if ok else f"status={r.status_code} body={str(body)[:200]}",
        )


def test_appointments(tokens) -> Dict[str, Any]:
    h = {"Authorization": f"Bearer {tokens['access']}"}
    ctx: Dict[str, Any] = {}

    r = req("GET", "/appointments", headers=h)
    ok = r.status_code == 200
    docs = r.json() if ok else []
    ok_count = ok and isinstance(docs, list) and len(docs) >= 6
    record(
        "appointments.list returns >=6 docs for técnico demo",
        ok_count,
        "" if ok_count else f"status={r.status_code} count={len(docs) if isinstance(docs, list) else 'n/a'}",
    )
    if not ok_count:
        return ctx
    ctx["first_id"] = docs[0]["id"]

    # get single
    r = req("GET", f"/appointments/{ctx['first_id']}", headers=h)
    record(
        "appointments.get by id",
        r.status_code == 200 and r.json().get("id") == ctx["first_id"],
        f"status={r.status_code}",
    )

    # accept a doc whose status is agendado
    agendado = next((d for d in docs if d.get("status") == "agendado"), None)
    if agendado:
        r = req(
            "POST",
            f"/appointments/{agendado['id']}/accept",
            headers=h,
            json={},
        )
        ok = r.status_code == 200 and r.json().get("status") == "aceita"
        record("appointments.accept (agendado→aceita)", ok, f"status={r.status_code} body={r.text[:200]}")
        ctx["accepted_id"] = agendado["id"]
    else:
        record("appointments.accept", False, "no 'agendado' doc available to accept")

    # refuse another agendado (not the one accepted)
    refuse_target = next(
        (d for d in docs if d.get("status") == "agendado" and d["id"] != ctx.get("accepted_id")),
        None,
    )
    if refuse_target:
        r = req(
            "POST",
            f"/appointments/{refuse_target['id']}/refuse",
            headers=h,
            json={"reason": "teste"},
        )
        ok = r.status_code == 200 and r.json().get("status") == "recusada"
        record("appointments.refuse (reason=teste)", ok, f"status={r.status_code} body={r.text[:200]}")
    else:
        record("appointments.refuse", False, "no second 'agendado' doc available")

    # seed-new generates a random OS
    r = req("POST", "/appointments/seed-new", headers=h, json={})
    ok = r.status_code == 200 and r.json().get("status") == "agendado" and r.json().get("id")
    record(
        "appointments.seed-new generates new OS",
        ok,
        f"status={r.status_code} body={r.text[:200]}",
    )
    return ctx


def test_inventory(tokens):
    h = {"Authorization": f"Bearer {tokens['access']}"}
    r = req("GET", "/inventory/me", headers=h)
    ok = r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 6
    record(
        "inventory.me returns >=6 seeded items",
        ok,
        f"status={r.status_code} count={len(r.json()) if ok else 'n/a'}",
    )
    if not ok:
        return
    item = r.json()[0]
    r = req(
        "POST",
        f"/inventory/{item['id']}/transfer",
        headers=h,
        json={"new_status": "with_tech"},
    )
    record(
        "inventory.transfer with valid new_status",
        r.status_code == 200 and r.json().get("status") == "with_tech",
        f"status={r.status_code} body={r.text[:200]}",
    )


def test_device(tokens):
    h = {"Authorization": f"Bearer {tokens['access']}"}
    # valid IMEI
    r = req("POST", "/device/test", headers=h, json={"imei": "123456789012345"})
    ok = r.status_code == 200 and "online" in r.json() and "message" in r.json()
    record("device.test with valid IMEI (15 digits)", ok, f"status={r.status_code} body={r.text[:200]}")
    # invalid IMEI
    r = req("POST", "/device/test", headers=h, json={"imei": "12345"})
    record(
        "device.test with invalid IMEI → 400",
        r.status_code == 400,
        f"status={r.status_code}",
    )


def test_earnings(tokens):
    h = {"Authorization": f"Bearer {tokens['access']}"}
    for p in ("day", "week", "month", "all"):
        r = req("GET", f"/earnings/me?period={p}", headers=h)
        body = r.json() if r.status_code == 200 else {}
        ok = (
            r.status_code == 200
            and body.get("period") == p
            and "total_net" in body
            and "jobs" in body
            and "price_table" in body
        )
        record(
            f"earnings.me period={p}",
            ok,
            "" if ok else f"status={r.status_code} body_keys={list(body.keys())[:10]}",
        )
    r = req("GET", "/earnings/price-table", headers=h)
    body = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and "price_table" in body and "sla_fast_minutes" in body
    record("earnings.price-table", ok, f"status={r.status_code}")


def test_rankings(tokens):
    h = {"Authorization": f"Bearer {tokens['access']}"}
    r = req("GET", "/rankings/weekly", headers=h)
    body = r.json() if r.status_code == 200 else {}
    ok = (
        r.status_code == 200
        and "top_earners" in body
        and "top_fast" in body
        and body.get("period") == "week"
    )
    record("rankings.weekly", ok, f"status={r.status_code}")


def test_gamification(tokens):
    h = {"Authorization": f"Bearer {tokens['access']}"}
    r = req("GET", "/gamification/profile", headers=h)
    body = r.json() if r.status_code == 200 else {}
    required = ["level", "achievements", "weekly_history", "total_xp", "unlocked_count", "achievements_total"]
    missing = [k for k in required if k not in body]
    ok = r.status_code == 200 and not missing
    record(
        "gamification.profile has level/achievements/weekly_history/total_xp/unlocked_count/achievements_total",
        ok,
        "" if ok else f"status={r.status_code} missing={missing}",
    )


# --------------------------------------------------------------------------------------
# 4) CHECKLISTS CRUD
# --------------------------------------------------------------------------------------
def minimal_draft_payload() -> Dict[str, Any]:
    return {
        "nome": "Carlos",
        "sobrenome": "Braga",
        "placa": "BRA2E19",
        "empresa": "Valeteck",
        "equipamento": "Rastreador GPS XT-2000",
        "status": "rascunho",
    }


def full_send_payload() -> Dict[str, Any]:
    photos = [
        {
            "label": f"step-{s}",
            "base64": png_data_uri(),
            "workflow_step": s,
            "photo_id": f"p-{s}",
        }
        for s in (1, 2, 3, 4)
    ]
    return {
        "nome": "Mariana",
        "sobrenome": "Azevedo",
        "placa": "RIO9J12",
        "empresa": "Rastremix",
        "equipamento": "Rastreador GPS Plus",
        "tipo_atendimento": "Instalação",
        "vehicle_type": "carro",
        "battery_state": "Em bom estado",
        "imei": "012345678901234",
        "iccid": "89551010000000012345",
        "photos": photos,
        "signature_base64": png_data_uri(),
        "status": "enviado",
    }


def test_checklists_crud(tokens):
    h = {"Authorization": f"Bearer {tokens['access']}"}

    # Create draft
    r = req("POST", "/checklists", headers=h, json=minimal_draft_payload())
    ok = r.status_code == 200 and r.json().get("status") == "rascunho"
    created_id = r.json().get("id") if ok else None
    record(
        "checklists.create (rascunho minimal payload)",
        ok,
        "" if ok else f"status={r.status_code} body={r.text[:400]}",
    )
    if not created_id:
        return

    # list
    r = req("GET", "/checklists", headers=h)
    ok = r.status_code == 200 and isinstance(r.json(), list) and any(d["id"] == created_id for d in r.json())
    record("checklists.list contains the created draft", ok, f"status={r.status_code}")

    # list with ?q=BRA
    r = req("GET", "/checklists?q=BRA", headers=h)
    ok = r.status_code == 200 and isinstance(r.json(), list)
    record(
        "checklists.list?q=BRA returns list (may include our BRA2E19 draft)",
        ok and any("BRA" in (d.get("placa", "") or "") for d in r.json()),
        f"status={r.status_code} matches={sum(1 for d in r.json() if 'BRA' in (d.get('placa','') or ''))}",
    )

    # get by id
    r = req("GET", f"/checklists/{created_id}", headers=h)
    record(
        "checklists.get by id",
        r.status_code == 200 and r.json().get("id") == created_id,
        f"status={r.status_code}",
    )

    # update
    upd = minimal_draft_payload()
    upd["obs_tecnicas"] = "atualizado via teste automatizado"
    r = req("PUT", f"/checklists/{created_id}", headers=h, json=upd)
    ok = r.status_code == 200 and r.json().get("obs_tecnicas") == "atualizado via teste automatizado"
    record("checklists.update draft", ok, f"status={r.status_code} body={r.text[:200]}")

    # delete
    r = req("DELETE", f"/checklists/{created_id}", headers=h)
    record("checklists.delete draft", r.status_code == 200, f"status={r.status_code}")

    # send without photos → 400
    bad = minimal_draft_payload()
    bad["status"] = "enviado"
    r = req("POST", "/checklists", headers=h, json=bad)
    ok = r.status_code == 400 and "obrigat" in r.text.lower()
    record(
        "checklists.create status=enviado without photos → 400 with PT-BR validation",
        ok,
        f"status={r.status_code} body={r.text[:300]}",
    )

    # send with full payload → 200
    r = req("POST", "/checklists", headers=h, json=full_send_payload())
    if r.status_code != 200:
        record(
            "checklists.create status=enviado with 4 photos + signature + IMEI → 200",
            False,
            f"status={r.status_code} body={r.text[:400]}",
        )
        return
    sent_id = r.json()["id"]
    record(
        "checklists.create status=enviado with 4 photos + signature + IMEI → 200",
        True,
        f"id={sent_id}",
    )

    # PDF download
    r = req("GET", f"/checklists/{sent_id}/pdf", headers=h)
    ctype = r.headers.get("content-type", "")
    size = len(r.content)
    ok = r.status_code == 200 and "application/pdf" in ctype and size > 1000 and r.content[:4] == b"%PDF"
    record(
        "checklists.pdf returns application/pdf bytes (>1KB, %PDF magic)",
        ok,
        f"status={r.status_code} ctype={ctype} size={size}",
    )


# --------------------------------------------------------------------------------------
# 5) HEALTH
# --------------------------------------------------------------------------------------
def test_health_and_root():
    r = req("GET", "/health")
    body = r.json() if r.status_code == 200 else {}
    ok = (
        r.status_code == 200
        and body.get("status") == "ok"
        and body.get("services", {}).get("api") == "ok"
        and body.get("services", {}).get("database") == "ok"
        and body.get("services", {}).get("cloudinary") == "disabled"
    )
    record(
        "system.health status=ok + services.{api,database}=ok + cloudinary=disabled",
        ok,
        "" if ok else f"status={r.status_code} body={r.text[:300]}",
    )

    r = req("GET", "/")
    body = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and body.get("app") == "Valeteck" and body.get("status") == "ok"
    record("system.root returns {app:Valeteck,status:ok}", ok, f"status={r.status_code} body={r.text[:200]}")


# --------------------------------------------------------------------------------------
# 6) PARTNER WEBHOOK
# --------------------------------------------------------------------------------------
def test_partner_webhook():
    payload = {
        "partner": "rastremix",
        "user_email": TECH_EMAIL,
        "numero_os": f"OS-PART-{uuid.uuid4().hex[:6].upper()}",
        "cliente_nome": "Ricardo",
        "cliente_sobrenome": "Lima",
        "placa": "PTN1A23",
        "endereco": "Rua Teste Partner, 100 - São Paulo/SP",
        "scheduled_at": "2026-06-01T14:00:00+00:00",
        "vehicle_type": "carro",
        "prioridade": "normal",
        "telefone": "(11) 91234-5678",
        "tempo_estimado_min": 60,
        "observacoes": "webhook test",
        "comissao": 150.0,
        "secret": PARTNER_SECRET,
    }
    r = req("POST", "/partners/webhook/appointments", json=payload)
    ok = r.status_code == 200 and r.json().get("ok") is True and r.json().get("appointment_id")
    record(
        "partners.webhook with valid secret → 200 + appointment_id",
        ok,
        f"status={r.status_code} body={r.text[:300]}",
    )

    bad = dict(payload)
    bad["secret"] = "wrong-secret"
    bad["numero_os"] = f"OS-PART-{uuid.uuid4().hex[:6].upper()}"
    r = req("POST", "/partners/webhook/appointments", json=bad)
    record(
        "partners.webhook with invalid secret → 401",
        r.status_code == 401,
        f"status={r.status_code} body={r.text[:200]}",
    )


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
def main():
    print(f"==> Base API: {API}")
    print("=" * 80)
    # Run health+root and rate-limit FIRST.
    # Because /auth/login is rate-limited to 10/min, doing the 13-burst would
    # consume the quota; we want to ensure a successful login after the limit
    # resets. Strategy: do the normal auth flow FIRST (uses 1 request), then
    # do the burst AT THE END.
    test_health_and_root()
    tokens = test_auth_flow()
    if not tokens:
        print("\nCannot continue without tokens. Aborting.")
        return summarize()

    # Preserved endpoints
    test_reference_endpoints(tokens)
    test_appointments(tokens)
    test_inventory(tokens)
    test_device(tokens)
    test_earnings(tokens)
    test_rankings(tokens)
    test_gamification(tokens)

    # Checklists CRUD (heavy)
    test_checklists_crud(tokens)

    # Partner webhook
    test_partner_webhook()

    # Rate limit LAST (will burn /auth/login quota)
    test_rate_limit_login()

    summarize()


def summarize():
    print("=" * 80)
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["ok"])
    failed = [r for r in RESULTS if not r["ok"]]
    print(f"PASSED: {passed}/{total}")
    if failed:
        print("\nFAILED:")
        for r in failed:
            print(f"  - {r['name']}: {r['detail']}")
    print("=" * 80)
    # Exit code for CI-friendliness
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
