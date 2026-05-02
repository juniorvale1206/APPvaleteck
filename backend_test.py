"""Valeteck v14 - Fase 1 do Motor de Comissionamento — smoke test.

Valida:
  A) Login + UserOut (level + tutor_id) para admin, tecnico, n2, n3, junior.
  B) GET /auth/me com token do junior: level='junior' e tutor_id==id do n3.
  C) GET /reference/service-catalog sem filtro → 11 itens + keys esperadas.
  D) GET /reference/service-catalog?level=junior (e ?level=n1) → 9 itens, sem categoria "acessorio".
  E) GET /reference/service-catalog?level=n2 → 11 itens (incluindo acessórios).
  F) Regressão com técnico (tecnico@valeteck.com): /auth/me, /appointments,
     /gamification/meta (target=60), /gamification/profile, /inventory/me.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Optional

import requests

BASE = "https://installer-track-1.preview.emergentagent.com/api"

USERS = [
    {"email": "admin@valeteck.com",   "password": "admin123",   "role": "admin",   "level": None,     "expect_tutor": False},
    {"email": "tecnico@valeteck.com", "password": "tecnico123", "role": "tecnico", "level": "n1",     "expect_tutor": False},
    {"email": "n2@valeteck.com",      "password": "n2tech123",  "role": "tecnico", "level": "n2",     "expect_tutor": False},
    {"email": "n3@valeteck.com",      "password": "n3tech123",  "role": "tecnico", "level": "n3",     "expect_tutor": False},
    {"email": "junior@valeteck.com",  "password": "junior123",  "role": "tecnico", "level": "junior", "expect_tutor": True},
]

PASS = "\u2705"
FAIL = "\u274c"

results: list[tuple[str, bool, str]] = []


def mark(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    print(f"{PASS if ok else FAIL} {label} :: {detail}")


def post_login(email: str, password: str) -> Optional[dict[str, Any]]:
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password}, timeout=20)
    if r.status_code != 200:
        return None
    return r.json()


def get_with_token(path: str, token: str) -> requests.Response:
    return requests.get(f"{BASE}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=20)


# -------------------- A) Login + UserOut --------------------
print("\n========== A) LOGIN + USEROUT ==========")
tokens: dict[str, str] = {}
ids: dict[str, str] = {}
user_payloads: dict[str, dict[str, Any]] = {}

for spec in USERS:
    email = spec["email"]
    payload = post_login(email, spec["password"])
    if payload is None:
        mark(f"login::{email}", False, "status != 200")
        continue
    user = payload.get("user") or {}
    access = payload.get("access_token")
    mark(f"login::{email} → 200", access is not None and "user" in payload,
         f"access_len={len(access) if access else 0}, keys={list(payload.keys())}")
    # role
    mark(f"user.role == {spec['role']} ({email})", user.get("role") == spec["role"],
         f"got role={user.get('role')!r}")
    # level
    level_ok = user.get("level") == spec["level"]
    # Admin: accept missing or None
    if spec["level"] is None and "level" not in user:
        level_ok = True
    mark(f"user.level == {spec['level']!r} ({email})", level_ok,
         f"got level={user.get('level')!r}")
    # tutor_id
    if spec["expect_tutor"]:
        mark(f"user.tutor_id != null ({email})", bool(user.get("tutor_id")),
             f"got tutor_id={user.get('tutor_id')!r}")
    else:
        tid = user.get("tutor_id")
        mark(f"user.tutor_id is null ({email})", tid is None,
             f"got tutor_id={tid!r}")
    if access:
        tokens[email] = access
    if user.get("id"):
        ids[email] = user["id"]
    user_payloads[email] = user

# Cross-validation: junior.tutor_id == n3.id
junior = user_payloads.get("junior@valeteck.com") or {}
n3_id = ids.get("n3@valeteck.com")
mark(
    "junior.tutor_id == n3.id",
    junior.get("tutor_id") == n3_id and n3_id is not None,
    f"junior.tutor_id={junior.get('tutor_id')!r}, n3.id={n3_id!r}",
)

# -------------------- B) /auth/me com token do junior --------------------
print("\n========== B) /AUTH/ME (JUNIOR) ==========")
jtoken = tokens.get("junior@valeteck.com")
if not jtoken:
    mark("/auth/me junior (pré-req)", False, "sem token")
else:
    r = get_with_token("/auth/me", jtoken)
    ok = r.status_code == 200
    me_user = r.json() if ok else {}
    mark("/auth/me status 200", ok, f"status={r.status_code}")
    mark("/auth/me level == junior", me_user.get("level") == "junior",
         f"got level={me_user.get('level')!r}")
    mark("/auth/me tutor_id != null", bool(me_user.get("tutor_id")),
         f"got tutor_id={me_user.get('tutor_id')!r}")
    mark("/auth/me tutor_id == n3.id", me_user.get("tutor_id") == n3_id,
         f"tutor={me_user.get('tutor_id')!r} n3={n3_id!r}")

# -------------------- C) /reference/service-catalog sem filtro --------------------
# NOTA: endpoint exige auth? vamos usar admin para ser seguro
print("\n========== C) /REFERENCE/SERVICE-CATALOG (sem filtro) ==========")
admin_token = tokens.get("admin@valeteck.com")
headers_admin = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
r = requests.get(f"{BASE}/reference/service-catalog", headers=headers_admin, timeout=20)
mark("GET /reference/service-catalog → 200", r.status_code == 200, f"status={r.status_code}")
items: list[dict[str, Any]] = []
if r.status_code == 200:
    body = r.json()
    items = body.get("items", [])
    mark("service-catalog retorna exatamente 11 itens", len(items) == 11, f"got {len(items)}")
    # Checar keys do primeiro item
    if items:
        expected_keys = {"code", "name", "category", "max_minutes", "base_value", "level_restriction"}
        missing = expected_keys - set(items[0].keys())
        mark("item possui todas as keys esperadas", not missing,
             f"missing={missing}, keys={list(items[0].keys())}")

    # Verificar itens chave
    by_code = {it["code"]: it for it in items}

    des = by_code.get("desinstalacao", {})
    ok_des = (des.get("max_minutes") == 20 and float(des.get("base_value", 0)) == 2.00
              and des.get("category") == "desinstalacao" and des.get("level_restriction") is None)
    mark("desinstalacao {max_minutes=20, base_value=2.00, category=desinstalacao, level_restriction=null}",
         ok_des, f"got {des}")

    sensor = by_code.get("acessorio_sensor_estacionamento", {})
    ok_sensor = (sensor.get("max_minutes") == 60 and float(sensor.get("base_value", 0)) == 10.00
                 and sensor.get("category") == "acessorio" and sensor.get("level_restriction") == "n2")
    mark("acessorio_sensor_estacionamento {max_minutes=60, base_value=10.00, category=acessorio, level_restriction=n2}",
         ok_sensor, f"got {sensor}")

    bloq_part = by_code.get("instalacao_bloq_antifurto_partida", {})
    ok_bloq = (bloq_part.get("max_minutes") == 70 and float(bloq_part.get("base_value", 0)) == 7.00)
    mark("instalacao_bloq_antifurto_partida {max_minutes=70, base_value=7.00}",
         ok_bloq, f"got {bloq_part}")

# -------------------- D) level=junior / level=n1 --------------------
print("\n========== D) /REFERENCE/SERVICE-CATALOG?level=junior & ?level=n1 ==========")
for lvl in ("junior", "n1"):
    r = requests.get(f"{BASE}/reference/service-catalog", params={"level": lvl}, headers=headers_admin, timeout=20)
    mark(f"GET service-catalog?level={lvl} → 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        lst = r.json().get("items", [])
        mark(f"level={lvl} retorna 9 itens", len(lst) == 9, f"got {len(lst)}")
        cats = {it.get("category") for it in lst}
        mark(f"level={lvl} sem category=acessorio", "acessorio" not in cats, f"categories={cats}")

# -------------------- E) level=n2 --------------------
print("\n========== E) /REFERENCE/SERVICE-CATALOG?level=n2 ==========")
r = requests.get(f"{BASE}/reference/service-catalog", params={"level": "n2"}, headers=headers_admin, timeout=20)
mark("GET service-catalog?level=n2 → 200", r.status_code == 200, f"status={r.status_code}")
if r.status_code == 200:
    lst = r.json().get("items", [])
    mark("level=n2 retorna 11 itens", len(lst) == 11, f"got {len(lst)}")
    acc_count = sum(1 for it in lst if it.get("category") == "acessorio")
    mark("level=n2 inclui acessórios (>=2)", acc_count >= 2, f"acessorios count={acc_count}")

# -------------------- F) Regressão com técnico --------------------
print("\n========== F) REGRESSÃO (tecnico) ==========")
ttoken = tokens.get("tecnico@valeteck.com")
if not ttoken:
    mark("regressão pré-req token tecnico", False, "sem token")
else:
    # /auth/me
    r = get_with_token("/auth/me", ttoken)
    mark("GET /auth/me → 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        u = r.json()
        mark("tecnico.level == n1", u.get("level") == "n1", f"level={u.get('level')!r}")

    # /appointments
    r = get_with_token("/appointments", ttoken)
    mark("GET /appointments → 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        body = r.json()
        # aceita list ou {appointments:[...]}
        count = len(body) if isinstance(body, list) else len(body.get("appointments", []) or body.get("items", []))
        mark("appointments retornou lista não-vazia", count > 0, f"count={count}")

    # /gamification/meta → target=60
    r = get_with_token("/gamification/meta", ttoken)
    mark("GET /gamification/meta → 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        meta = r.json()
        mark("gamification/meta.target == 60", meta.get("target") == 60, f"target={meta.get('target')!r}")

    # /gamification/profile
    r = get_with_token("/gamification/profile", ttoken)
    mark("GET /gamification/profile → 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        prof = r.json()
        lvl = prof.get("level") or {}
        # Aceita formato {level:{number, name}} ou camelCase
        has_num = isinstance(lvl, dict) and ("number" in lvl or "level_number" in lvl)
        has_name = isinstance(lvl, dict) and ("name" in lvl or "level_name" in lvl)
        mark("profile.level possui number", has_num, f"level={lvl!r}")
        mark("profile.level possui name", has_name, f"level={lvl!r}")

    # /inventory ou /inventory/me
    r = get_with_token("/inventory", ttoken)
    if r.status_code == 404:
        r = get_with_token("/inventory/me", ttoken)
        mark("GET /inventory/me → 200 (fallback)", r.status_code == 200, f"status={r.status_code}")
    else:
        mark("GET /inventory → 200", r.status_code == 200, f"status={r.status_code}")

# -------------------- SUMMARY --------------------
print("\n========== SUMMARY ==========")
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"PASS: {passed}/{total}")
fails = [(lbl, det) for lbl, ok, det in results if not ok]
if fails:
    print("\nFailed assertions:")
    for lbl, det in fails:
        print(f"  {FAIL} {lbl} :: {det}")
    sys.exit(1)
print("All PASS ✅")
