from typing import List, Optional
from pydantic import BaseModel

from .inventory import ReverseOverdueItem


class MonthlyClosureIn(BaseModel):
    month: str            # formato YYYY-MM
    signature_base64: Optional[str] = ""   # assinatura digital do técnico confirmando
    notes: Optional[str] = ""


class LevelBonuses(BaseModel):
    """Breakdown dos bônus por nível no fechamento mensal (v14 Fase 4)."""
    # Contagens
    valid_os: int = 0                   # OS válidas (validation_status = valido)
    within_sla_os: int = 0              # OS dentro do SLA
    returns_30d: int = 0                # retornos 30d causados ao próprio técnico
    tutee_total_os: int = 0             # total de OS dos juniores vinculados (para N3)
    tutees_hit_goal: int = 0            # quantos juniores bateram 30 OS
    tutees_with_returns: int = 0        # juniores com retorno 30d (guilhotina)
    # Bônus específicos
    bonus_junior_meta: float = 0.0      # +R$ 50 se junior bateu 30 OS
    bonus_junior_zero_returns: float = 0.0   # +R$ 50 se junior teve 0 retornos
    bonus_n1n2_retroactive: float = 0.0      # +R$ 2 retroativo × within_sla_os (se valid >= 60)
    bonus_n3_residual: float = 0.0           # R$ 1 × OS de juniores vinculados
    bonus_n3_tutoria: float = 0.0            # R$ 1 extra se junior bateu meta (bloqueado se teve retorno)
    bonus_total: float = 0.0                 # soma de todos os bônus


class MonthlyClosureBreakdown(BaseModel):
    total_gross: float                # total bruto de ganhos no mês (comp_final_value)
    total_jobs: int                    # qtd de OS enviadas no mês
    inventory_total: int               # itens em estoque no momento
    overdue_count: int                 # qtd vencidos
    penalty_total: float               # R$ em penalidades (inventário + retorno 30d)
    net_after_penalty: float           # gross + bonuses - penalty
    overdue_items: List[ReverseOverdueItem]
    # v14 Fase 4
    level: Optional[str] = None        # nível aplicado (junior/n1/n2/n3)
    bonuses: Optional[LevelBonuses] = None


class MonthlyClosureOut(BaseModel):
    id: Optional[str] = None
    user_id: str
    month: str
    confirmed_at: Optional[str] = None    # se None, é snapshot em tempo real (não fechado)
    breakdown: MonthlyClosureBreakdown
    signature_base64: Optional[str] = ""
    notes: Optional[str] = ""
