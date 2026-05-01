"""
Valeteck v10 — Backend tests for Gamification advanced endpoint.

Endpoint under test:
  GET /api/gamification/profile  (Bearer auth)

Asserts:
  - 401 without token
  - response shape: level, achievements (12), weekly_history (8), total_xp, unlocked_count, achievements_total
  - level object contains all required keys; next is null only at max level
  - achievements array has 12 items with required keys and 0<=progress_pct<=1
  - weekly_history has exactly 8 ISO weeks ordered ascending; last == current week
  - XP formula matches: base 50 per OS + 30 if elapsed<1800s + 20 if aprovado
"""
import os
from datetime import datetime, timezone, timedelta

import pytest
import requests

def _resolve_base_url() -> str:
    for k in ("EXPO_PUBLIC_BACKEND_URL", "EXPO_BACKEND_URL"):
        v = os.environ.get(k, "").strip().rstrip("/")
        if v:
            return v
    # Read from frontend/.env as last resort
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                line = line.strip()
                if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().strip('"').rstrip("/")
    except Exception:
        pass
    return ""

BASE_URL = _resolve_base_url()
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL must be set"

TECNICO = {"email": "tecnico@valeteck.com", "password": "tecnico123"}

# Mirror backend constants
LEVEL_THRESHOLDS = [
    (1, "Bronze", 0),
    (2, "Prata", 500),
    (3, "Ouro", 1500),
    (4, "Diamante", 3500),
    (5, "Mestre", 7500),
]
XP_PER_OS = 50
XP_BONUS_SLA = 30
XP_BONUS_APPROVED = 20
SLA_FAST_SEC = 1800


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=TECNICO, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data
    return data["token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ----------------- Auth -----------------
def test_gamification_profile_requires_auth():
    r = requests.get(f"{BASE_URL}/api/gamification/profile", timeout=15)
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}: {r.text}"


# ----------------- Shape -----------------
@pytest.fixture(scope="module")
def profile(headers):
    r = requests.get(f"{BASE_URL}/api/gamification/profile", headers=headers, timeout=20)
    assert r.status_code == 200, f"GET profile failed: {r.status_code} {r.text}"
    return r.json()


def test_profile_top_level_keys(profile):
    for k in ("level", "achievements", "weekly_history", "total_xp", "unlocked_count", "achievements_total"):
        assert k in profile, f"Missing top-level key: {k}"
    assert isinstance(profile["total_xp"], int)
    assert isinstance(profile["unlocked_count"], int)
    assert profile["achievements_total"] == 12


def test_level_object_shape(profile):
    lv = profile["level"]
    required = {"number", "name", "min_xp", "icon", "color", "xp", "xp_current_level", "xp_next_level", "progress_pct", "next"}
    assert required.issubset(lv.keys()), f"level missing keys: {required - set(lv.keys())}"
    assert lv["xp"] == profile["total_xp"]
    assert 0.0 <= lv["progress_pct"] <= 1.0
    # next must be None only when level is Mestre (max)
    if lv["name"] == "Mestre":
        assert lv["next"] is None
    else:
        assert lv["next"] is not None
        for k in ("number", "name", "icon", "color", "min_xp"):
            assert k in lv["next"], f"next missing {k}"


def test_level_matches_xp(profile):
    xp = profile["total_xp"]
    expected_name = "Bronze"
    for _, name, threshold in LEVEL_THRESHOLDS:
        if xp >= threshold:
            expected_name = name
    assert profile["level"]["name"] == expected_name, f"XP={xp} expected level={expected_name}, got {profile['level']['name']}"


# ----------------- Achievements -----------------
def test_achievements_count_and_shape(profile):
    achs = profile["achievements"]
    assert isinstance(achs, list)
    assert len(achs) == 12, f"expected 12 achievements, got {len(achs)}"
    keys = {"id", "name", "description", "icon", "target", "current", "unlocked", "progress_pct"}
    ids = set()
    for a in achs:
        assert keys.issubset(a.keys()), f"achievement missing keys: {keys - set(a.keys())}"
        assert isinstance(a["unlocked"], bool)
        assert 0.0 <= a["progress_pct"] <= 1.0
        ids.add(a["id"])
    # ids must be unique
    assert len(ids) == 12, "achievement ids must be unique"


def test_unlocked_count_consistent(profile):
    achs = profile["achievements"]
    expected = sum(1 for a in achs if a["unlocked"])
    assert profile["unlocked_count"] == expected


def test_first_os_unlocked_when_n_ge_1(profile):
    # first_os achievement (target=1) should unlock if user has >=1 sent checklist
    first = next((a for a in profile["achievements"] if a["id"] == "first_os"), None)
    assert first is not None
    if first["current"] >= 1:
        assert first["unlocked"] is True
        assert first["progress_pct"] == 1.0


# ----------------- Weekly history -----------------
def test_weekly_history_length_and_order(profile):
    wh = profile["weekly_history"]
    assert isinstance(wh, list)
    assert len(wh) == 8, f"expected 8 weeks, got {len(wh)}"
    starts = [w["week_start"] for w in wh]
    assert starts == sorted(starts), "weekly_history must be ascending by week_start"
    keys = {"week_start", "week_label", "total_net", "count", "fast_count", "xp"}
    for w in wh:
        assert keys.issubset(w.keys()), f"week missing keys: {keys - set(w.keys())}"


def test_last_week_is_current_iso_week(profile):
    last = profile["weekly_history"][-1]
    last_dt = datetime.fromisoformat(last["week_start"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    expected_monday = now - timedelta(days=now.weekday())
    expected_monday = datetime(expected_monday.year, expected_monday.month, expected_monday.day, tzinfo=timezone.utc)
    assert last_dt == expected_monday, f"last week_start {last_dt} != current ISO week monday {expected_monday}"


def test_weeks_are_consecutive_mondays(profile):
    wh = profile["weekly_history"]
    for i in range(1, len(wh)):
        prev = datetime.fromisoformat(wh[i - 1]["week_start"].replace("Z", "+00:00"))
        cur = datetime.fromisoformat(wh[i]["week_start"].replace("Z", "+00:00"))
        assert (cur - prev) == timedelta(days=7), f"weeks not consecutive at idx {i}: {prev} -> {cur}"


# ----------------- XP formula consistency with checklists list -----------------
def test_xp_formula_matches_checklists(headers, profile):
    """Cross-check: fetch user's checklists and recompute XP — must equal profile.total_xp."""
    r = requests.get(f"{BASE_URL}/api/checklists?limit=5000", headers=headers, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"GET /api/checklists not available ({r.status_code}) for cross-check")
    body = r.json()
    items = body.get("items") if isinstance(body, dict) else body
    if not isinstance(items, list):
        pytest.skip("Could not parse checklists list response")

    # Only count "sent" statuses (matching backend filter)
    valid_status = {"enviado", "em_auditoria", "aprovado", "reprovado"}
    xp = 0
    sent_count = 0
    fast_count = 0
    approved_count = 0
    for c in items:
        if c.get("status") not in valid_status:
            continue
        sent_count += 1
        xp += XP_PER_OS
        elapsed = int(c.get("execution_elapsed_sec") or 0)
        if 0 < elapsed < SLA_FAST_SEC:
            xp += XP_BONUS_SLA
            fast_count += 1
        if c.get("status") == "aprovado":
            xp += XP_BONUS_APPROVED
            approved_count += 1

    print(f"\n[xp-cross-check] sent={sent_count} fast={fast_count} approved={approved_count} computed_xp={xp} profile_xp={profile['total_xp']}")
    assert xp == profile["total_xp"], (
        f"XP mismatch: client computed {xp} (sent={sent_count}, fast={fast_count}, approved={approved_count}) "
        f"vs server {profile['total_xp']}"
    )


def test_expected_xp_660_scenario(profile):
    """Per problem statement: 12 OS, 2 fast, 0 approved → 12*50 + 2*30 + 0*20 = 660 → Prata."""
    # We can't force scenario, but we log and assert level matches whatever XP is.
    print(f"\n[scenario] total_xp={profile['total_xp']} level={profile['level']['name']} "
          f"unlocked={profile['unlocked_count']}/{profile['achievements_total']}")
    if profile["total_xp"] == 660:
        assert profile["level"]["name"] == "Prata"
        assert profile["level"]["next"]["name"] == "Ouro"
        assert profile["level"]["xp_current_level"] == 660 - 500
        assert profile["level"]["xp_next_level"] == 1500 - 500
