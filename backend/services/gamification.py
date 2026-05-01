"""Serviço de gamificação (XP, níveis, conquistas, histórico semanal)."""
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from core.config import (
    SLA_FAST_SEC,
    XP_PER_OS,
    XP_BONUS_SLA,
    XP_BONUS_APPROVED,
)
from services.pricing import base_price, sla_bonus
from constants import COMPANIES


LEVELS = [
    {"number": 1, "name": "Bronze",    "min_xp": 0,    "icon": "🥉", "color": "#C97E3D"},
    {"number": 2, "name": "Prata",     "min_xp": 500,  "icon": "🥈", "color": "#9CA3AF"},
    {"number": 3, "name": "Ouro",      "min_xp": 1500, "icon": "🥇", "color": "#F59E0B"},
    {"number": 4, "name": "Diamante",  "min_xp": 3500, "icon": "💎", "color": "#3B82F6"},
    {"number": 5, "name": "Mestre",    "min_xp": 7500, "icon": "👑", "color": "#8B5CF6"},
]


def compute_xp(docs: List[dict]) -> int:
    total = 0
    for d in docs:
        total += XP_PER_OS
        elapsed = int(d.get("execution_elapsed_sec") or 0)
        if 0 < elapsed < SLA_FAST_SEC:
            total += XP_BONUS_SLA
        if d.get("status") == "aprovado":
            total += XP_BONUS_APPROVED
    return total


def level_from_xp(xp: int) -> dict:
    current = LEVELS[0]
    nxt: Optional[dict] = None
    for i, lv in enumerate(LEVELS):
        if xp >= lv["min_xp"]:
            current = lv
            nxt = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
    if nxt is None:
        return {**current, "xp": xp, "xp_current_level": xp - current["min_xp"], "xp_next_level": 0, "progress_pct": 1.0, "next": None}
    xp_in = xp - current["min_xp"]
    xp_req = nxt["min_xp"] - current["min_xp"]
    return {
        **current,
        "xp": xp,
        "xp_current_level": xp_in,
        "xp_next_level": xp_req,
        "progress_pct": round(min(xp_in / xp_req, 1.0), 3),
        "next": nxt,
    }


def compute_achievements(docs: List[dict]) -> List[dict]:
    n = len(docs)
    by_empresa = set()
    approved = 0
    fast = 0
    total_net = 0.0
    max_per_day: dict = {}
    for d in docs:
        by_empresa.add(d.get("empresa", ""))
        if d.get("status") == "aprovado":
            approved += 1
        elapsed = int(d.get("execution_elapsed_sec") or 0)
        if 0 < elapsed < SLA_FAST_SEC:
            fast += 1
        base = base_price(d.get("empresa", ""), d.get("tipo_atendimento") or "Instalação")
        bonus = sla_bonus(base, elapsed)
        total_net += base + bonus
        created = d.get("created_at") or d.get("sent_at") or ""
        key = created[:10]
        max_per_day[key] = max_per_day.get(key, 0) + 1
    triple_day = any(v >= 3 for v in max_per_day.values())
    full_partners = len(by_empresa & set(COMPANIES)) >= len(COMPANIES)
    catalog = [
        {"id": "first_os",     "name": "Primeira instalação", "description": "Envie seu 1º checklist",          "icon": "rocket-outline",          "target": 1,    "current": n},
        {"id": "10_os",        "name": "10 checklists",        "description": "Envie 10 checklists",            "icon": "medal-outline",           "target": 10,   "current": n},
        {"id": "50_os",        "name": "Veterano",              "description": "Envie 50 checklists",            "icon": "trophy-outline",          "target": 50,   "current": n},
        {"id": "100_os",       "name": "Cento",                 "description": "Envie 100 checklists",           "icon": "star-outline",            "target": 100,  "current": n},
        {"id": "5_fast",       "name": "5 relâmpagos",          "description": "5 OS com SLA < 30 min",          "icon": "flash-outline",           "target": 5,    "current": fast},
        {"id": "10_fast",      "name": "10 relâmpagos",         "description": "10 OS com SLA < 30 min",         "icon": "flash",                   "target": 10,   "current": fast},
        {"id": "5_approved",   "name": "5 aprovadas",           "description": "5 checklists aprovados em auditoria", "icon": "checkmark-circle-outline", "target": 5,  "current": approved},
        {"id": "10_approved",  "name": "10 aprovadas",          "description": "10 checklists aprovados",        "icon": "checkmark-done",          "target": 10,   "current": approved},
        {"id": "triple_day",   "name": "Triplo no dia",         "description": "3 OS enviadas no mesmo dia",     "icon": "layers-outline",          "target": 1,    "current": 1 if triple_day else 0},
        {"id": "earn_1k",      "name": "R$ 1.000",              "description": "Acumule R$ 1.000 em ganhos",     "icon": "cash-outline",            "target": 1000, "current": int(total_net)},
        {"id": "earn_5k",      "name": "R$ 5.000",              "description": "Acumule R$ 5.000 em ganhos",     "icon": "wallet-outline",          "target": 5000, "current": int(total_net)},
        {"id": "full_partners","name": "Todos os parceiros",    "description": "Atenda todas as 6 empresas parceiras", "icon": "people-outline",     "target": 1,    "current": 1 if full_partners else 0},
    ]
    out = []
    for a in catalog:
        unlocked = a["current"] >= a["target"]
        out.append({
            **a,
            "unlocked": unlocked,
            "progress_pct": round(min(a["current"] / a["target"], 1.0), 3) if a["target"] > 0 else 1.0,
        })
    return out


def _iso_week_start(dt: datetime) -> datetime:
    monday = dt - timedelta(days=dt.weekday())
    return datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)


def compute_weekly_history(docs: List[dict], weeks: int = 8) -> List[dict]:
    now = datetime.now(timezone.utc)
    current_start = _iso_week_start(now)
    buckets: dict = {}
    for w in range(weeks):
        start = current_start - timedelta(days=7 * w)
        buckets[start.isoformat()] = {
            "week_start": start.isoformat(),
            "week_label": start.strftime("%d/%m"),
            "total_net": 0.0, "count": 0, "fast_count": 0, "xp": 0,
        }
    for d in docs:
        created = d.get("sent_at") or d.get("created_at")
        if not created:
            continue
        try:
            ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except Exception:
            continue
        wstart = _iso_week_start(ts)
        key = wstart.isoformat()
        if key not in buckets:
            continue
        base = base_price(d.get("empresa", ""), d.get("tipo_atendimento") or "Instalação")
        elapsed = int(d.get("execution_elapsed_sec") or 0)
        bonus = sla_bonus(base, elapsed)
        buckets[key]["count"] += 1
        buckets[key]["total_net"] += base + bonus
        if 0 < elapsed < SLA_FAST_SEC:
            buckets[key]["fast_count"] += 1
            buckets[key]["xp"] += XP_PER_OS + XP_BONUS_SLA
        else:
            buckets[key]["xp"] += XP_PER_OS
        if d.get("status") == "aprovado":
            buckets[key]["xp"] += XP_BONUS_APPROVED
    out = list(buckets.values())
    for b in out:
        b["total_net"] = round(b["total_net"], 2)
    out.sort(key=lambda x: x["week_start"])
    return out
