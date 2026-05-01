"""Serviços de inventário: deadline de reversa, categorização, penalidades."""
from calendar import monthrange
from datetime import datetime, timezone, timedelta
from typing import Optional


# Valores padrão de equipamento (R$) — usado quando item não tem equipment_value setado.
# Referência do cliente: rastreador=300, bloqueador=200, câmera=500, outros=150
EQUIPMENT_VALUES = {
    "rastreador": 300.00,
    "bloqueador": 200.00,
    "camera": 500.00,
    "outro": 150.00,
}

# Prazo base de devolução
REVERSE_DAYS = 5


def last_business_day_of_month(dt: datetime) -> datetime:
    """Retorna o último dia útil (seg-sex) do mês de `dt`, preservando tz."""
    tz = dt.tzinfo or timezone.utc
    y, m = dt.year, dt.month
    last_day = monthrange(y, m)[1]
    d = datetime(y, m, last_day, 23, 59, 59, tzinfo=tz)
    while d.weekday() > 4:  # 5=Sat, 6=Sun
        d -= timedelta(days=1)
    return d


def compute_reverse_deadline(pending_at: datetime) -> datetime:
    """Regra: 5 dias corridos após entrar em pending_reverse, MAS o prazo não pode
    atravessar o fim do mês — se atravessar, usa o último dia útil do mês atual.
    """
    base = pending_at + timedelta(days=REVERSE_DAYS)
    if base.month != pending_at.month or base.year != pending_at.year:
        return last_business_day_of_month(pending_at)
    return base


def categorize_equipment(tipo: str, modelo: str = "") -> str:
    """Mapeia tipo/modelo para categoria canonical (rastreador|bloqueador|camera|outro)."""
    t = (tipo or "").lower()
    m = (modelo or "").lower()
    if "bloque" in t or "bloque" in m:
        return "bloqueador"
    if "camera" in t or "câmera" in t or "cam" in m[:4]:
        return "camera"
    if "rastread" in t or "gps" in m or "tracker" in m:
        return "rastreador"
    return "outro"


def default_equipment_value(category: str) -> float:
    return EQUIPMENT_VALUES.get(category, EQUIPMENT_VALUES["outro"])


def enrich_reverse_fields(doc: dict, now: Optional[datetime] = None) -> dict:
    """Adiciona campos computados ao item: reverse_overdue, reverse_days_left,
    reverse_deadline_at (se ainda não persistido). NÃO modifica `doc` no DB.
    """
    now = now or datetime.now(timezone.utc)
    out = dict(doc)
    status = out.get("status", "")
    pending_iso = out.get("pending_reverse_at")
    # Garante equipment_category/value defaults
    if not out.get("equipment_category"):
        out["equipment_category"] = categorize_equipment(out.get("tipo", ""), out.get("modelo", ""))
    if not out.get("equipment_value"):
        out["equipment_value"] = default_equipment_value(out["equipment_category"])

    if status == "pending_reverse" and pending_iso:
        try:
            pending_at = datetime.fromisoformat(pending_iso.replace("Z", "+00:00"))
            deadline = out.get("reverse_deadline_at")
            if deadline:
                try:
                    deadline_dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                except Exception:
                    deadline_dt = compute_reverse_deadline(pending_at)
            else:
                deadline_dt = compute_reverse_deadline(pending_at)
            diff = (deadline_dt - now).total_seconds()
            out["reverse_deadline_at"] = deadline_dt.isoformat()
            if diff >= 0:
                out["reverse_days_left"] = int(diff // 86400)
                out["reverse_overdue"] = False
            else:
                # Atraso: arredonda p/ cima (ex: 2h atrasado conta como 1 dia)
                import math
                out["reverse_days_left"] = -int(math.ceil((-diff) / 86400))
                out["reverse_overdue"] = True
        except Exception:
            out["reverse_overdue"] = False
            out["reverse_days_left"] = None
    else:
        out["reverse_overdue"] = False
        out["reverse_days_left"] = None
        if not out.get("reverse_deadline_at"):
            out["reverse_deadline_at"] = None
    return out


def compute_penalty_total(items: list) -> dict:
    """Dado uma lista de items enriquecidos, calcula o total de penalidade
    dos itens em `pending_reverse` que estão `reverse_overdue`."""
    overdue = [i for i in items if i.get("reverse_overdue")]
    total = 0.0
    for it in overdue:
        total += float(it.get("equipment_value") or default_equipment_value(it.get("equipment_category", "outro")))
    return {
        "overdue_count": len(overdue),
        "penalty_total": round(total, 2),
        "overdue_items": [
            {
                "id": i["id"], "modelo": i.get("modelo", ""), "serie": i.get("serie", ""),
                "imei": i.get("imei", ""), "placa": i.get("placa", ""),
                "equipment_category": i.get("equipment_category"),
                "equipment_value": i.get("equipment_value"),
                "days_overdue": abs(i.get("reverse_days_left") or 0),
                "reverse_deadline_at": i.get("reverse_deadline_at"),
            }
            for i in overdue
        ],
    }
