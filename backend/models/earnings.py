from typing import List, Optional
from pydantic import BaseModel


class EarningJob(BaseModel):
    id: str
    numero: str
    empresa: str
    tipo_atendimento: Optional[str] = ""
    nome: str
    sobrenome: str
    placa: str
    base_amount: float
    bonus_amount: float
    total_amount: float
    elapsed_sec: int
    elapsed_min: int
    sla_fast: bool
    sent_at: Optional[str] = None
    created_at: str


class EarningsSummary(BaseModel):
    period: str
    total_base: float
    total_bonus: float
    total_net: float
    count: int
    avg_elapsed_min: int
    fast_count: int
    breakdown_by_company: dict
    breakdown_by_type: dict
    jobs: List[EarningJob]
    price_table: dict
