from typing import Optional, List
from pydantic import BaseModel


class InventoryItem(BaseModel):
    id: str
    user_id: Optional[str] = None
    tipo: str  # rastreador | bloqueador | acessório
    modelo: str
    imei: Optional[str] = ""
    iccid: Optional[str] = ""
    serie: Optional[str] = ""
    empresa: Optional[str] = ""
    status: str
    checklist_id: Optional[str] = None
    placa: Optional[str] = ""
    tracking_code: Optional[str] = ""

    # Categorização + valor do equipamento (para penalidade de não-devolução)
    equipment_category: Optional[str] = None  # rastreador|bloqueador|camera|outro
    equipment_value: Optional[float] = None   # R$

    # Logística reversa
    pending_reverse_at: Optional[str] = None      # quando entrou em pending_reverse
    reverse_deadline_at: Optional[str] = None     # prazo final para devolver (computado)
    reverse_carrier: Optional[str] = None         # Correios|Jadlog|Mercado Envios|Outro
    reverse_tracking_code: Optional[str] = None   # código de rastreio da reversa
    reverse_sent_at: Optional[str] = None         # data em que o técnico enviou
    reverse_expected_at: Optional[str] = None     # previsão de chegada na central
    reverse_received_at: Optional[str] = None     # recebido de fato na central
    reverse_notes: Optional[str] = None           # observações do técnico

    # Flags computadas (somente leitura)
    reverse_overdue: Optional[bool] = False
    reverse_days_left: Optional[int] = None

    updated_at: str
    created_at: str


class InventoryTransferIn(BaseModel):
    new_status: str
    tracking_code: Optional[str] = ""           # legacy (usado para encaminhamento do técnico)
    # Campos de logística reversa (usados em pending_reverse → in_transit_to_hq)
    reverse_carrier: Optional[str] = None
    reverse_tracking_code: Optional[str] = None
    reverse_sent_at: Optional[str] = None
    reverse_expected_at: Optional[str] = None
    reverse_notes: Optional[str] = None


class ReverseOverdueItem(BaseModel):
    id: str
    modelo: str
    serie: Optional[str] = ""
    imei: Optional[str] = ""
    placa: Optional[str] = ""
    equipment_category: Optional[str] = None
    equipment_value: Optional[float] = None
    days_overdue: int
    reverse_deadline_at: Optional[str] = None


class InventorySummary(BaseModel):
    total: int
    by_status: dict  # { status: count }
    with_tech_count: int
    installed_count: int
    pending_reverse_count: int
    overdue_count: int
    penalty_total: float         # valor total em R$ que pode ser descontado
    overdue_items: List[ReverseOverdueItem]
