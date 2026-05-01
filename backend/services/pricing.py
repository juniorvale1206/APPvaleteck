"""Tabela de preços (R$) por empresa parceira x tipo de serviço + helpers de SLA/período."""
from datetime import datetime, timezone, timedelta
from typing import Optional

from core.config import (
    SLA_FAST_SEC,
    SLA_FAST_BONUS_PCT,
)


PRICE_TABLE: dict = {
    "Valeteck":  {"Instalação": 120.00, "Manutenção": 80.00, "Retirada": 60.00, "Garantia": 40.00},
    "Rastremix": {"Instalação": 100.00, "Manutenção": 75.00, "Retirada": 55.00, "Garantia": 35.00},
    "GPS My":    {"Instalação": 95.00,  "Manutenção": 70.00, "Retirada": 50.00, "Garantia": 30.00},
    "GPS Joy":   {"Instalação": 90.00,  "Manutenção": 65.00, "Retirada": 50.00, "Garantia": 30.00},
    "Topy Pro":  {"Instalação": 110.00, "Manutenção": 80.00, "Retirada": 55.00, "Garantia": 35.00},
    "Telensat":  {"Instalação": 115.00, "Manutenção": 85.00, "Retirada": 60.00, "Garantia": 40.00},
}
DEFAULT_PRICE = 80.00


def base_price(empresa: str, tipo: str) -> float:
    return PRICE_TABLE.get(empresa, {}).get(tipo, DEFAULT_PRICE)


def sla_bonus(base: float, elapsed_sec: int) -> float:
    if not elapsed_sec or elapsed_sec <= 0:
        return 0.0
    if elapsed_sec < SLA_FAST_SEC:
        return round(base * SLA_FAST_BONUS_PCT, 2)
    return 0.0


def period_start(period: str) -> Optional[datetime]:
    now = datetime.now(timezone.utc)
    if period == "day":
        return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    if period == "week":
        monday = now - timedelta(days=now.weekday())
        return datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)
    if period == "month":
        return datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if period == "all":
        return None
    return None
