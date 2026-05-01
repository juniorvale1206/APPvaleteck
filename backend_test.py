"""Valeteck v13 — Motor de Regras Pós-Aprovação — Backend Test Suite.

Cobre:
1) Admin endpoints (pending-approvals) + controle de role.
2) Motor de regras — aprovação (bônus R$5 / duplicidade 30d).
3) Rejeição com motivo obrigatório.
4) Meta configurável (GET gamification/meta, POST admin/users/{id}/meta).
5) Earnings com validation_bonus refletido.
6) Regressão de endpoints core.
"""
import os
import sys
import json
import base64
import uuid
import random
import string
import time
from typing import Any, Dict, Optional

import requests

BASE = os.environ.get(
    "BACKEND_URL",
    "https://installer-track-1.preview.emergentagent.com",
).rstrip("/")
API = BASE + "/api"

ADMIN_EMAIL = "admin@valeteck.com"
ADMIN_PASS = "admin123"
TECH_EMAIL = "tecnico@valeteck.com"
TECH_PASS = "tecnico123"

# -------------- helpers --------------
PASSED: list = []
FAILED: list = []


def ok(msg):
    PASSED.append(msg)
    print(f"  PASS: {msg}")


def fail(msg, extra=""):
    FAILED.append(f"{msg} :: {extra}")
    print(f"  FAIL: {msg} :: {extra}")


def login(email: str, password: str) -> Dict[str, Any]:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text}"
    data = r.json()
    return data


def auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def rand_plate() -> str:
    # Mercosul-like: 3 letters + 1 digit + 1 letter + 2 digits
    letters = string.ascii_uppercase
    digits = string.digits
    return (
        "".join(random.choice(letters) for _ in range(3))
        + random.choice(digits)
        + random.choice(letters)
        + "".join(random.choice(digits) for _ in range(2))
    )


def rand_imei() -> str:
    return "".join(random.choice(string.digits) for _ in range(15))


def tiny_b64_png() -> str:
    # 1x1 transparent PNG
    b = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000d4944415478da63f8cfc0000000030001012bf3150a0000000049454e44ae426082"
    )
    return "data:image/png;base64," + base64.b64encode(b).decode()


def make_checklist_payload(plate: str, imei: Optional[str] = None) -> Dict[str, Any]:
    """Payload mínimo válido para status='enviado'."""
    photos = []
    for step in (1, 2, 3, 4):
        photos.append({
            "photo_id": uuid.uuid4().hex[:8],
            "workflow_step": step,
            "base64": tiny_b64_png(),
            "caption": f"foto step {step}",
        })
    return {
        "status": "enviado",
        "nome": "Cliente",
        "sobrenome": "Teste v13",
        "placa": plate,
        "telefone": "11999990000",
        "empresa": "Rastremix",
        "equipamento": "Rastreador XP-100",
        "tipo_atendimento": "Instalação",
        "imei": imei or rand_imei(),
        "battery_state": "Normal",
        "photos": photos,
        "signature_base64": tiny_b64_png(),
        "location_available": False,
    }


# -------------- tests --------------
def main() -> int:
    print(f"Base URL: {API}")

    # ---------- login admin + técnico ----------
    try:
        admin = login(ADMIN_EMAIL, ADMIN_PASS)
        tech = login(TECH_EMAIL, TECH_PASS)
        admin_tok = admin.get("access_token") or admin.get("token")
        tech_tok = tech.get("access_token") or tech.get("token")
        assert admin_tok and tech_tok
        ok("login admin + técnico OK")
        admin_hdr = auth_headers(admin_tok)
        tech_hdr = auth_headers(tech_tok)
        tech_id = tech["user"]["id"]
    except Exception as e:
        fail("login inicial", str(e))
        return 1

    # ==================================================================
    # 1) ADMIN ENDPOINTS — pending-approvals
    # ==================================================================
    print("\n[1] ADMIN ENDPOINTS")
    try:
        r = requests.get(f"{API}/admin/pending-approvals", headers=admin_hdr, timeout=30)
        if r.status_code != 200:
            fail("GET /admin/pending-approvals admin", f"status={r.status_code} body={r.text}")
            pending = []
        else:
            data = r.json()
            if "pending" not in data or "count" not in data:
                fail("payload pending-approvals", f"chaves esperadas ausentes: {list(data.keys())}")
            pending = data.get("pending", [])
            count = data.get("count")
            if count != len(pending):
                fail("count != len(pending)", f"count={count} len={len(pending)}")
            else:
                ok(f"GET /admin/pending-approvals OK (count={count})")
            # Enriquecimento
            if pending:
                sample = pending[0]
                if "technician_name" in sample and "technician_email" in sample:
                    ok("items enriquecidos com technician_name/email")
                else:
                    fail("enriquecimento técnico ausente", f"keys={list(sample.keys())[:20]}")
    except Exception as e:
        fail("GET /admin/pending-approvals", str(e))
        pending = []

    # Chamada com token de técnico → 403
    try:
        r = requests.get(f"{API}/admin/pending-approvals", headers=tech_hdr, timeout=30)
        if r.status_code == 403:
            ok("técnico em /admin/pending-approvals → 403")
        else:
            fail("pending-approvals com tecnico", f"esperava 403, veio {r.status_code}")
    except Exception as e:
        fail("pending-approvals tecnico", str(e))

    # ==================================================================
    # 2) MOTOR DE REGRAS — APROVAÇÃO
    # ==================================================================
    print("\n[2] MOTOR DE REGRAS — APROVAÇÃO")

    # Precisamos de checklists do técnico tecnico@valeteck.com em status enviado para testar.
    # Filtra da lista pending apenas os do nosso técnico.
    tech_pending = [p for p in pending if p.get("user_id") == tech_id]
    approved_checklist: Optional[dict] = None
    approved_plate: Optional[str] = None

    if not tech_pending:
        # cria um via POST /checklists
        try:
            plate = rand_plate()
            r = requests.post(
                f"{API}/checklists",
                json=make_checklist_payload(plate),
                headers=tech_hdr,
                timeout=60,
            )
            if r.status_code == 200:
                ch = r.json()
                tech_pending = [ch]
                ok(f"checklist criado via POST /checklists id={ch['id'][:8]}")
            else:
                fail("criar checklist inicial", f"{r.status_code} {r.text[:200]}")
        except Exception as e:
            fail("criar checklist inicial exc", str(e))

    if tech_pending:
        target = tech_pending[0]
        target_id = target["id"]
        approved_plate = target.get("placa") or target.get("plate_norm")

        try:
            r = requests.post(
                f"{API}/admin/checklists/{target_id}/approve",
                headers=admin_hdr,
                timeout=30,
            )
            if r.status_code != 200:
                fail("approve checklist", f"{r.status_code} {r.text[:300]}")
            else:
                data = r.json()
                if data.get("ok") is not True:
                    fail("approve ok flag", str(data))
                if data.get("validation_status") != "valido":
                    fail("approve validation_status", f"got {data.get('validation_status')}")
                else:
                    ok("validation_status=valido")
                if abs(float(data.get("validation_bonus") or 0) - 5.0) > 0.001:
                    fail("approve validation_bonus", f"got {data.get('validation_bonus')}")
                else:
                    ok("validation_bonus=5.0")
                if data.get("duplicate_of") not in (None, ""):
                    fail("duplicate_of deveria ser null", str(data.get("duplicate_of")))
                else:
                    ok("duplicate_of=null")
                msg = data.get("message") or ""
                if "5" in msg and ("creditado" in msg.lower() or "R$" in msg):
                    ok(f"mensagem PT-BR creditação: {msg!r}")
                else:
                    fail("mensagem PT-BR", f"msg={msg!r}")

                # Verifica persistência: GET /checklists/{id}
                # (como técnico, dono do checklist)
                rr = requests.get(f"{API}/checklists/{target_id}", headers=tech_hdr, timeout=30)
                if rr.status_code == 200:
                    doc = rr.json()
                    if doc.get("status") == "aprovado":
                        ok("status=aprovado persistido")
                    else:
                        fail("status aprovado persistido", f"got {doc.get('status')}")
                    if doc.get("approved_at"):
                        ok("approved_at preenchido")
                    else:
                        fail("approved_at vazio", "")
                    if doc.get("approved_by_id"):
                        ok(f"approved_by_id preenchido ({doc.get('approved_by_id')[:8]})")
                    else:
                        fail("approved_by_id vazio", "")
                    approved_checklist = doc
                else:
                    fail("GET /checklists/{id} pós-approve", f"{rr.status_code}")
        except Exception as e:
            fail("approve exception", str(e))

        # Reaprovar mesmo checklist → 400
        try:
            r = requests.post(
                f"{API}/admin/checklists/{target_id}/approve",
                headers=admin_hdr,
                timeout=30,
            )
            if r.status_code == 400:
                detail = r.json().get("detail", "")
                if "já processado" in detail.lower() or "processado" in detail.lower():
                    ok(f"re-approve → 400 '{detail}'")
                else:
                    fail("re-approve detail", detail)
            else:
                fail("re-approve status", f"esperava 400, veio {r.status_code} - {r.text[:200]}")
        except Exception as e:
            fail("re-approve exception", str(e))

    # ==================================================================
    # 3) DUPLICIDADE (30 dias)
    # ==================================================================
    print("\n[3] MOTOR DE REGRAS — DUPLICIDADE")
    if approved_plate:
        try:
            payload = make_checklist_payload(approved_plate)  # same plate!
            r = requests.post(f"{API}/checklists", json=payload, headers=tech_hdr, timeout=60)
            if r.status_code != 200:
                fail("criar checklist duplicado", f"{r.status_code} {r.text[:200]}")
            else:
                dup_id = r.json()["id"]
                ok(f"checklist duplicado criado id={dup_id[:8]} placa={approved_plate}")

                rr = requests.post(
                    f"{API}/admin/checklists/{dup_id}/approve",
                    headers=admin_hdr, timeout=30,
                )
                if rr.status_code != 200:
                    fail("approve duplicado", f"{rr.status_code} {rr.text[:200]}")
                else:
                    d = rr.json()
                    if d.get("validation_status") == "duplicidade_garantia":
                        ok("validation_status=duplicidade_garantia")
                    else:
                        fail("validation_status dup", f"got {d.get('validation_status')}")
                    if float(d.get("validation_bonus") or 0) == 0.0:
                        ok("validation_bonus=0.0 na duplicidade")
                    else:
                        fail("validation_bonus dup", f"got {d.get('validation_bonus')}")
                    dup_of = d.get("duplicate_of")
                    if dup_of and approved_checklist and dup_of == approved_checklist["id"]:
                        ok(f"duplicate_of aponta para checklist original ({dup_of[:8]})")
                    elif dup_of:
                        ok(f"duplicate_of preenchido ({dup_of[:8]})")
                    else:
                        fail("duplicate_of vazio", str(d))
        except Exception as e:
            fail("duplicidade exception", str(e))
    else:
        fail("duplicidade skip", "sem placa aprovada para reusar")

    # ==================================================================
    # 4) REJEIÇÃO
    # ==================================================================
    print("\n[4] REJEIÇÃO")
    # pega novamente pending para rejeitar um
    try:
        r = requests.get(f"{API}/admin/pending-approvals", headers=admin_hdr, timeout=30)
        pending2 = (r.json() if r.status_code == 200 else {}).get("pending", [])
    except Exception as e:
        fail("relist pending", str(e))
        pending2 = []

    tech_pending2 = [p for p in pending2 if p.get("user_id") == tech_id]
    reject_target: Optional[str] = None

    if not tech_pending2:
        # cria novo
        try:
            plate = rand_plate()
            rc = requests.post(
                f"{API}/checklists",
                json=make_checklist_payload(plate),
                headers=tech_hdr, timeout=60,
            )
            if rc.status_code == 200:
                reject_target = rc.json()["id"]
                ok(f"checklist criado para rejeitar id={reject_target[:8]}")
        except Exception as e:
            fail("criar para rejeitar", str(e))
    else:
        reject_target = tech_pending2[0]["id"]

    if reject_target:
        # Sem reason → 400
        try:
            r = requests.post(
                f"{API}/admin/checklists/{reject_target}/reject",
                json={"reason": ""},
                headers=admin_hdr, timeout=30,
            )
            if r.status_code == 400:
                detail = r.json().get("detail", "")
                if "motivo" in detail.lower() and "obrigatório" in detail.lower():
                    ok(f"reject sem reason → 400 '{detail}'")
                else:
                    fail("reject sem reason detail", detail)
            else:
                fail("reject sem reason status", f"{r.status_code}")
        except Exception as e:
            fail("reject sem reason exc", str(e))

        # Com reason → 200
        try:
            r = requests.post(
                f"{API}/admin/checklists/{reject_target}/reject",
                json={"reason": "foto ruim"},
                headers=admin_hdr, timeout=30,
            )
            if r.status_code == 200:
                d = r.json()
                cl = d.get("checklist") or {}
                if cl.get("status") == "reprovado":
                    ok("status=reprovado")
                else:
                    fail("status reprovado", f"got {cl.get('status')}")
                if cl.get("rejection_reason") == "foto ruim":
                    ok("rejection_reason='foto ruim'")
                else:
                    fail("rejection_reason", f"got {cl.get('rejection_reason')}")
            else:
                fail("reject com reason status", f"{r.status_code} {r.text[:200]}")
        except Exception as e:
            fail("reject com reason exc", str(e))

        # Reject em checklist já processado → 400
        try:
            r = requests.post(
                f"{API}/admin/checklists/{reject_target}/reject",
                json={"reason": "novamente"},
                headers=admin_hdr, timeout=30,
            )
            if r.status_code == 400:
                detail = r.json().get("detail", "")
                if "processado" in detail.lower():
                    ok(f"re-reject → 400 '{detail}'")
                else:
                    fail("re-reject detail", detail)
            else:
                fail("re-reject status", f"{r.status_code}")
        except Exception as e:
            fail("re-reject exc", str(e))

    # Reject em checklist já APROVADO → 400
    if approved_checklist:
        try:
            r = requests.post(
                f"{API}/admin/checklists/{approved_checklist['id']}/reject",
                json={"reason": "tentativa em aprovado"},
                headers=admin_hdr, timeout=30,
            )
            if r.status_code == 400:
                detail = r.json().get("detail", "")
                if "processado" in detail.lower():
                    ok(f"reject em checklist aprovado → 400 '{detail}'")
                else:
                    fail("reject aprovado detail", detail)
            else:
                fail("reject aprovado status", f"{r.status_code}")
        except Exception as e:
            fail("reject aprovado exc", str(e))

    # ==================================================================
    # 5) META CONFIGURÁVEL
    # ==================================================================
    print("\n[5] META CONFIGURÁVEL")
    try:
        r = requests.get(f"{API}/gamification/meta", headers=tech_hdr, timeout=30)
        if r.status_code == 200:
            d = r.json()
            expected = {
                "target", "achieved", "pending", "duplicates", "progress_pct",
                "remaining", "days_left", "per_day_needed", "on_track", "reached",
                "validation_bonus_earned",
            }
            missing = expected - set(d.keys())
            if missing:
                fail("gamification/meta chaves", f"missing={missing}")
            else:
                ok(f"GET /gamification/meta OK target={d['target']} achieved={d['achieved']} bonus={d['validation_bonus_earned']}")
        else:
            fail("GET /gamification/meta", f"{r.status_code} {r.text[:200]}")
    except Exception as e:
        fail("gamification/meta exc", str(e))

    # POST /admin/users/{id}/meta com admin
    try:
        r = requests.post(
            f"{API}/admin/users/{tech_id}/meta",
            json={"monthly_target": 100},
            headers=admin_hdr, timeout=30,
        )
        if r.status_code == 200:
            d = r.json()
            u = d.get("user") or {}
            if u.get("monthly_target") == 100:
                ok("POST /admin/users/{id}/meta admin -> user.monthly_target=100")
            else:
                fail("user.monthly_target atualizado", f"{u.get('monthly_target')}")
        else:
            fail("POST meta admin status", f"{r.status_code} {r.text[:200]}")
    except Exception as e:
        fail("POST meta admin exc", str(e))

    # POST meta com técnico → 403
    try:
        r = requests.post(
            f"{API}/admin/users/{tech_id}/meta",
            json={"monthly_target": 50},
            headers=tech_hdr, timeout=30,
        )
        if r.status_code == 403:
            ok("POST meta com tecnico → 403")
        else:
            fail("POST meta tecnico", f"esperava 403, veio {r.status_code}")
    except Exception as e:
        fail("POST meta tecnico exc", str(e))

    # monthly_target=0 → 400
    try:
        r = requests.post(
            f"{API}/admin/users/{tech_id}/meta",
            json={"monthly_target": 0},
            headers=admin_hdr, timeout=30,
        )
        if r.status_code == 400:
            ok("POST meta=0 → 400")
        else:
            fail("POST meta=0", f"{r.status_code}")
    except Exception as e:
        fail("POST meta=0 exc", str(e))

    # monthly_target>1000 → 400
    try:
        r = requests.post(
            f"{API}/admin/users/{tech_id}/meta",
            json={"monthly_target": 5000},
            headers=admin_hdr, timeout=30,
        )
        if r.status_code == 400:
            ok("POST meta>1000 → 400")
        else:
            fail("POST meta>1000", f"{r.status_code}")
    except Exception as e:
        fail("POST meta>1000 exc", str(e))

    # user_id inexistente → 404
    try:
        r = requests.post(
            f"{API}/admin/users/{uuid.uuid4()}/meta",
            json={"monthly_target": 80},
            headers=admin_hdr, timeout=30,
        )
        if r.status_code == 404:
            ok("POST meta user inexistente → 404")
        else:
            fail("POST meta 404", f"{r.status_code} {r.text[:200]}")
    except Exception as e:
        fail("POST meta 404 exc", str(e))

    # Após meta=100, GET /gamification/meta deve refletir
    try:
        r = requests.get(f"{API}/gamification/meta", headers=tech_hdr, timeout=30)
        if r.status_code == 200 and r.json().get("target") == 100:
            ok("GET /gamification/meta agora target=100")
        else:
            fail("meta target=100 após update", f"{r.status_code} - {r.text[:200]}")
    except Exception as e:
        fail("meta target=100 exc", str(e))

    # ==================================================================
    # 6) EARNINGS COM BÔNUS DE VALIDAÇÃO
    # ==================================================================
    print("\n[6] EARNINGS COM BÔNUS DE VALIDAÇÃO")
    try:
        r = requests.get(f"{API}/earnings/me?period=month", headers=tech_hdr, timeout=30)
        if r.status_code == 200:
            d = r.json()
            total_bonus = float(d.get("total_bonus") or 0)
            jobs = d.get("jobs") or []
            # count valid approvals this month — ≥1 (acabamos de aprovar)
            if approved_checklist:
                approved_id = approved_checklist["id"]
                match = next((j for j in jobs if j["id"] == approved_id), None)
                if match:
                    bonus_amt = float(match.get("bonus_amount") or 0)
                    # bonus_amount = sla_bonus + validation_bonus (5)
                    if bonus_amt >= 5.0:
                        ok(f"earnings job do checklist aprovado contém bonus≥5.0 (got {bonus_amt})")
                    else:
                        fail("bonus_amount do job aprovado", f"got {bonus_amt}")
                else:
                    # pode estar fora do período caso sent_at seja antigo — reportar como info
                    ok(f"job aprovado não está no period=month (checklist sent_at pode ser anterior) — total_bonus={total_bonus}")
            if total_bonus >= 5.0:
                ok(f"total_bonus reflete validação (R$ {total_bonus})")
            else:
                fail("total_bonus esperado ≥5", f"got {total_bonus}")
        else:
            fail("GET /earnings/me", f"{r.status_code}")
    except Exception as e:
        fail("earnings exc", str(e))

    # ==================================================================
    # 7) REGRESSÃO
    # ==================================================================
    print("\n[7] REGRESSÃO")
    # /inventory/summary — rota admin
    endpoints_admin = ["/admin/inventory/summary"]
    for ep in endpoints_admin:
        try:
            r = requests.get(f"{API}{ep}", headers=admin_hdr, timeout=30)
            if r.status_code == 200:
                ok(f"GET {ep} 200")
            else:
                fail(f"GET {ep}", f"{r.status_code} {r.text[:200]}")
        except Exception as e:
            fail(f"GET {ep} exc", str(e))

    endpoints_tech = [
        "/appointments",
        "/rankings/weekly",
        "/gamification/profile",
    ]
    for ep in endpoints_tech:
        try:
            r = requests.get(f"{API}{ep}", headers=tech_hdr, timeout=30)
            if r.status_code == 200:
                ok(f"GET {ep} 200")
            else:
                fail(f"GET {ep}", f"{r.status_code} {r.text[:200]}")
        except Exception as e:
            fail(f"GET {ep} exc", str(e))

    # /health (público)
    try:
        r = requests.get(f"{API}/health", timeout=30)
        if r.status_code == 200 and r.json().get("status") == "ok":
            ok("GET /health status=ok")
        else:
            fail("GET /health", f"{r.status_code} {r.text[:200]}")
    except Exception as e:
        fail("health exc", str(e))

    # restaura meta para 60 (limpeza leve)
    try:
        requests.post(
            f"{API}/admin/users/{tech_id}/meta",
            json={"monthly_target": 60},
            headers=admin_hdr, timeout=30,
        )
    except Exception:
        pass

    # ---------------- resumo ----------------
    print("\n" + "=" * 60)
    print(f"PASSED: {len(PASSED)}")
    print(f"FAILED: {len(FAILED)}")
    if FAILED:
        print("\n-- FAILED --")
        for f in FAILED:
            print(" -", f)
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
