"""Backend smoke test — Valeteck v14 Fase 4 (Bônus Mensais por Nível).

Tests:
  A) GET /inventory/monthly-closure (junior) — breakdown.level + breakdown.bonuses
  B) GET /inventory/monthly-closure (n3) — guilhotina ativada
  C) GET /inventory/monthly-closure (tecnico/n1) — bonus_n1n2_retroactive
  D) GET /inventory/monthly-closure (n2)
  E) Regressão: total_gross == /statement/me.gross_estimated
                penalty_total = inventario + retorno30d
                net_after_penalty = gross + bonus_total - penalty_total
  F) GET /inventory/monthly-closure/pdf (junior) — application/pdf, no 500
"""
import os
import sys

import requests

BASE_URL = os.environ.get(
    "BACKEND_URL", "https://installer-track-1.preview.emergentagent.com"
).rstrip("/")
API = f"{BASE_URL}/api"

USERS = {
    "junior": ("junior@valeteck.com", "junior123"),
    "n1": ("tecnico@valeteck.com", "tecnico123"),
    "n2": ("n2@valeteck.com", "n2tech123"),
    "n3": ("n3@valeteck.com", "n3tech123"),
}

REQUIRED_BONUS_KEYS = {
    "valid_os", "within_sla_os", "returns_30d",
    "tutee_total_os", "tutees_hit_goal", "tutees_with_returns",
    "bonus_junior_meta", "bonus_junior_zero_returns",
    "bonus_n1n2_retroactive",
    "bonus_n3_residual", "bonus_n3_tutoria",
    "bonus_total",
}


class Reporter:
    def __init__(self):
        self.passes = 0
        self.fails = []

    def ok(self, msg):
        self.passes += 1
        print(f"  OK  {msg}")

    def fail(self, msg):
        self.fails.append(msg)
        print(f"  FAIL {msg}")

    def summary(self):
        total = self.passes + len(self.fails)
        print(f"\n========== RESULT: {self.passes}/{total} PASS ==========")
        if self.fails:
            print("FAILED:")
            for f in self.fails:
                print(f"  - {f}")
            return False
        return True


def login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"login {email} failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


def get_closure(token, month=None):
    headers = {"Authorization": f"Bearer {token}"}
    params = {"month": month} if month else {}
    return requests.get(f"{API}/inventory/monthly-closure", headers=headers, params=params, timeout=30)


def get_statement(token, month=None):
    headers = {"Authorization": f"Bearer {token}"}
    params = {"month": month} if month else {}
    return requests.get(f"{API}/statement/me", headers=headers, params=params, timeout=30)


def get_closure_pdf(token, month=None):
    headers = {"Authorization": f"Bearer {token}"}
    params = {"month": month} if month else {}
    return requests.get(f"{API}/inventory/monthly-closure/pdf", headers=headers, params=params, timeout=60)


def validate_breakdown_shape(rep, prefix, bd, expected_level):
    lvl = bd.get("level")
    if lvl == expected_level:
        rep.ok(f"{prefix} breakdown.level == '{expected_level}'")
    else:
        rep.fail(f"{prefix} breakdown.level expected '{expected_level}', got {lvl!r}")
    bonuses = bd.get("bonuses")
    if not isinstance(bonuses, dict):
        rep.fail(f"{prefix} breakdown.bonuses missing/not-dict (got {type(bonuses).__name__})")
        return None
    rep.ok(f"{prefix} breakdown.bonuses present")
    missing = REQUIRED_BONUS_KEYS - set(bonuses.keys())
    if missing:
        rep.fail(f"{prefix} bonuses missing keys: {sorted(missing)}")
    else:
        rep.ok(f"{prefix} bonuses has all {len(REQUIRED_BONUS_KEYS)} required keys")
    return bonuses


def main():
    rep = Reporter()
    print(f"BASE: {API}\n")

    tokens = {}
    print("[Login] all users")
    for k, (e, p) in USERS.items():
        try:
            tokens[k] = login(e, p)
            rep.ok(f"login {k} ({e})")
        except Exception as ex:
            rep.fail(f"login {k}: {ex}")
            return rep.summary()

    # A) Junior
    print("\n[A] GET /inventory/monthly-closure (junior)")
    r = get_closure(tokens["junior"])
    if r.status_code != 200:
        rep.fail(f"junior closure HTTP {r.status_code} body={r.text[:400]}")
    else:
        rep.ok("junior closure HTTP 200")
        bd = r.json().get("breakdown") or {}
        bonuses = validate_breakdown_shape(rep, "junior", bd, "junior")
        if bonuses:
            jr_meta = bonuses["bonus_junior_meta"]
            jr_zero = bonuses["bonus_junior_zero_returns"]
            jr_valid = bonuses["valid_os"]
            jr_returns = bonuses["returns_30d"]
            print(f"     [debug] junior valid_os={jr_valid} returns_30d={jr_returns} "
                  f"bonus_meta={jr_meta} bonus_zero={jr_zero}")
            if jr_meta in (0, 0.0, 50, 50.0):
                rep.ok(f"junior bonus_junior_meta={jr_meta} (valid_os={jr_valid})")
            else:
                rep.fail(f"junior bonus_junior_meta unexpected: {jr_meta}")
            if jr_returns >= 1:
                if jr_zero == 0:
                    rep.ok(f"junior bonus_junior_zero_returns=0 (returns_30d={jr_returns}) ok")
                else:
                    rep.fail(
                        f"junior bonus_junior_zero_returns should be 0 when returns_30d={jr_returns}, "
                        f"got {jr_zero}"
                    )
            else:
                if jr_zero in (0, 0.0, 50, 50.0):
                    rep.ok(
                        f"junior bonus_junior_zero_returns={jr_zero} (returns_30d=0, valid_os={jr_valid})"
                    )
                else:
                    rep.fail(f"junior bonus_junior_zero_returns unexpected: {jr_zero}")
            expected_total = round(
                bonuses["bonus_junior_meta"] + bonuses["bonus_junior_zero_returns"]
                + bonuses["bonus_n1n2_retroactive"]
                + bonuses["bonus_n3_residual"] + bonuses["bonus_n3_tutoria"], 2,
            )
            actual_total = bonuses["bonus_total"]
            if abs(expected_total - actual_total) < 0.01:
                rep.ok(f"junior bonus_total coherent (={actual_total})")
            else:
                rep.fail(
                    f"junior bonus_total inconsistent: expected {expected_total} got {actual_total}"
                )

    # B) N3
    print("\n[B] GET /inventory/monthly-closure (n3)")
    r = get_closure(tokens["n3"])
    if r.status_code != 200:
        rep.fail(f"n3 closure HTTP {r.status_code} body={r.text[:400]}")
    else:
        rep.ok("n3 closure HTTP 200")
        bd = r.json().get("breakdown") or {}
        bonuses = validate_breakdown_shape(rep, "n3", bd, "n3")
        if bonuses:
            tutee_total = bonuses["tutee_total_os"]
            hit = bonuses["tutees_hit_goal"]
            with_returns = bonuses["tutees_with_returns"]
            residual = bonuses["bonus_n3_residual"]
            tutoria = bonuses["bonus_n3_tutoria"]
            print(f"     [debug] n3 tutee_total={tutee_total} hit={hit} with_returns={with_returns} "
                  f"residual={residual} tutoria={tutoria}")
            if isinstance(tutee_total, int):
                rep.ok(f"n3 tutee_total_os is int (={tutee_total})")
            else:
                rep.fail(f"n3 tutee_total_os not int: {tutee_total!r}")
            if isinstance(hit, int):
                rep.ok(f"n3 tutees_hit_goal is int (={hit})")
            else:
                rep.fail(f"n3 tutees_hit_goal not int: {hit!r}")
            if with_returns >= 1:
                rep.ok(f"n3 guilhotina activated: tutees_with_returns={with_returns}")
                if residual == 0 and tutoria == 0:
                    rep.ok(
                        "n3 bonus_n3_residual=0 e bonus_n3_tutoria=0 (todos juniores com retorno)"
                    )
                else:
                    rep.ok(
                        f"n3 bonus_n3_residual={residual}, bonus_n3_tutoria={tutoria} "
                        f"(há juniores limpos)"
                    )
            else:
                rep.ok("n3 sem guilhotina: tutees_with_returns=0")
            expected_total = round(
                bonuses["bonus_junior_meta"] + bonuses["bonus_junior_zero_returns"]
                + bonuses["bonus_n1n2_retroactive"]
                + bonuses["bonus_n3_residual"] + bonuses["bonus_n3_tutoria"], 2,
            )
            if abs(expected_total - bonuses["bonus_total"]) < 0.01:
                rep.ok(f"n3 bonus_total coherent (={bonuses['bonus_total']})")
            else:
                rep.fail(
                    f"n3 bonus_total inconsistent: expected {expected_total} "
                    f"got {bonuses['bonus_total']}"
                )

    # C) N1
    print("\n[C] GET /inventory/monthly-closure (n1 - tecnico)")
    r = get_closure(tokens["n1"])
    if r.status_code != 200:
        rep.fail(f"n1 closure HTTP {r.status_code} body={r.text[:400]}")
    else:
        rep.ok("n1 closure HTTP 200")
        bd = r.json().get("breakdown") or {}
        bonuses = validate_breakdown_shape(rep, "n1", bd, "n1")
        if bonuses:
            valid_os = bonuses["valid_os"]
            within_sla = bonuses["within_sla_os"]
            retro = bonuses["bonus_n1n2_retroactive"]
            print(f"     [debug] n1 valid_os={valid_os} within_sla={within_sla} retro={retro}")
            if valid_os < 60:
                if retro == 0 or retro == 0.0:
                    rep.ok(f"n1 bonus_n1n2_retroactive=0 (valid_os={valid_os} < 60)")
                else:
                    rep.fail(
                        f"n1 bonus_n1n2_retroactive should be 0 (valid_os={valid_os} < 60), got {retro}"
                    )
            else:
                expected = round(within_sla * 2.0, 2)
                if abs(retro - expected) < 0.01:
                    rep.ok(f"n1 bonus_n1n2_retroactive=2*within_sla_os ({retro})")
                else:
                    rep.fail(
                        f"n1 bonus_n1n2_retroactive expected {expected} (=2*{within_sla}), got {retro}"
                    )
            jr_zero = (
                bonuses["bonus_junior_meta"] == 0
                and bonuses["bonus_junior_zero_returns"] == 0
                and bonuses["bonus_n3_residual"] == 0
                and bonuses["bonus_n3_tutoria"] == 0
            )
            if jr_zero:
                rep.ok("n1 não tem bonus de junior nem n3 (todos 0)")
            else:
                rep.fail(
                    f"n1 has unexpected junior/n3 bonuses: "
                    f"junior_meta={bonuses['bonus_junior_meta']}, "
                    f"junior_zero={bonuses['bonus_junior_zero_returns']}, "
                    f"n3_resid={bonuses['bonus_n3_residual']}, "
                    f"n3_tut={bonuses['bonus_n3_tutoria']}"
                )

    # D) N2
    print("\n[D] GET /inventory/monthly-closure (n2)")
    r = get_closure(tokens["n2"])
    if r.status_code != 200:
        rep.fail(f"n2 closure HTTP {r.status_code} body={r.text[:400]}")
    else:
        rep.ok("n2 closure HTTP 200")
        bd = r.json().get("breakdown") or {}
        bonuses = validate_breakdown_shape(rep, "n2", bd, "n2")
        if bonuses:
            valid_os = bonuses["valid_os"]
            within_sla = bonuses["within_sla_os"]
            retro = bonuses["bonus_n1n2_retroactive"]
            print(f"     [debug] n2 valid_os={valid_os} within_sla={within_sla} retro={retro}")
            if valid_os < 60:
                if retro == 0:
                    rep.ok(f"n2 bonus_n1n2_retroactive=0 (valid_os={valid_os} < 60)")
                else:
                    rep.fail(
                        f"n2 bonus_n1n2_retroactive should be 0 (valid_os={valid_os}), got {retro}"
                    )
            else:
                expected = round(within_sla * 2.0, 2)
                if abs(retro - expected) < 0.01:
                    rep.ok(f"n2 bonus_n1n2_retroactive=2*within_sla_os ({retro})")
                else:
                    rep.fail(
                        f"n2 bonus_n1n2_retroactive expected {expected}, got {retro}"
                    )

    # E) Regressão
    print("\n[E] Regressão (gross/penalty/net) — junior")
    r_st = get_statement(tokens["junior"])
    if r_st.status_code != 200:
        rep.fail(f"junior statement HTTP {r_st.status_code} body={r_st.text[:300]}")
    else:
        st = r_st.json()
        r_cl = get_closure(tokens["junior"])
        if r_cl.status_code == 200:
            bd = r_cl.json().get("breakdown") or {}
            gross_st = round(float(st.get("gross_estimated") or 0), 2)
            gross_cl = round(float(bd.get("total_gross") or 0), 2)
            if abs(gross_st - gross_cl) < 0.01:
                rep.ok(f"junior total_gross == gross_estimated (={gross_cl})")
            else:
                rep.fail(f"junior total_gross ({gross_cl}) != gross_estimated ({gross_st})")
            bonus_total = float((bd.get("bonuses") or {}).get("bonus_total") or 0)
            penalty = float(bd.get("penalty_total") or 0)
            net = float(bd.get("net_after_penalty") or 0)
            expected_net = round(gross_cl + bonus_total - penalty, 2)
            if abs(expected_net - net) < 0.01:
                rep.ok(
                    f"junior net_after_penalty = gross+bonus-penalty "
                    f"({gross_cl} + {bonus_total} - {penalty} = {net})"
                )
            else:
                rep.fail(
                    f"junior net_after_penalty inconsistent: "
                    f"expected {expected_net} (={gross_cl}+{bonus_total}-{penalty}), got {net}"
                )
            pen_st = round(float(st.get("penalty_total") or 0), 2)
            if abs(pen_st - penalty) < 0.01:
                rep.ok(f"junior penalty_total == statement.penalty_total (={penalty})")
            else:
                rep.fail(
                    f"junior penalty_total ({penalty}) != statement.penalty_total ({pen_st})"
                )

    # F) PDF
    print("\n[F] GET /inventory/monthly-closure/pdf (junior)")
    r = get_closure_pdf(tokens["junior"])
    if r.status_code != 200:
        rep.fail(f"junior closure pdf HTTP {r.status_code} body={r.text[:300]}")
    else:
        rep.ok("junior closure pdf HTTP 200")
        ct = r.headers.get("Content-Type", "").lower()
        if "application/pdf" in ct:
            rep.ok(f"junior closure pdf Content-Type='{ct}'")
        else:
            rep.fail(f"junior closure pdf Content-Type expected pdf, got '{ct}'")
        if r.content[:4] == b"%PDF":
            rep.ok(f"junior closure pdf magic bytes %PDF ({len(r.content)} bytes)")
        else:
            rep.fail(
                f"junior closure pdf does not start with %PDF; first 8 bytes = {r.content[:8]!r}"
            )

    # E2 — n1
    print("\n[E2] Regressão extra — n1")
    r_st = get_statement(tokens["n1"])
    r_cl = get_closure(tokens["n1"])
    if r_st.status_code == 200 and r_cl.status_code == 200:
        gst = round(float(r_st.json().get("gross_estimated") or 0), 2)
        bd = r_cl.json().get("breakdown") or {}
        gcl = round(float(bd.get("total_gross") or 0), 2)
        if abs(gst - gcl) < 0.01:
            rep.ok(f"n1 total_gross == gross_estimated (={gcl})")
        else:
            rep.fail(f"n1 total_gross ({gcl}) != gross_estimated ({gst})")

    return rep.summary()


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
