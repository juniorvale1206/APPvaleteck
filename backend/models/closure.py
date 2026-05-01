from typing import List, Optional
from pydantic import BaseModel

from .inventory import ReverseOverdueItem


class MonthlyClosureIn(BaseModel):
    month: str            # formato YYYY-MM
    signature_base64: Optional[str] = ""   # assinatura digital do técnico confirmando
    notes: Optional[str] = ""


class MonthlyClosureBreakdown(BaseModel):
    total_gross: float                # total bruto de ganhos no mês
    total_jobs: int                    # qtd de OS enviadas no mês
    inventory_total: int               # itens em estoque no momento
    overdue_count: int                 # qtd vencidos
    penalty_total: float               # R$ em penalidades
    net_after_penalty: float           # gross - penalty
    overdue_items: List[ReverseOverdueItem]


class MonthlyClosureOut(BaseModel):
    id: Optional[str] = None
    user_id: str
    month: str
    confirmed_at: Optional[str] = None    # se None, é snapshot em tempo real (não fechado)
    breakdown: MonthlyClosureBreakdown
    signature_base64: Optional[str] = ""
    notes: Optional[str] = ""
