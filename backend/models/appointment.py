from typing import Optional
from pydantic import BaseModel


class AppointmentOut(BaseModel):
    id: str
    user_id: str
    numero_os: str
    cliente_nome: str
    cliente_sobrenome: str
    placa: str
    empresa: str
    endereco: str
    scheduled_at: str
    status: str  # agendado | aceita | recusada | em_andamento | concluido
    checklist_id: Optional[str] = None
    vehicle_type: Optional[str] = ""
    vehicle_brand: Optional[str] = ""
    vehicle_model: Optional[str] = ""
    vehicle_year: Optional[str] = ""
    prioridade: str = "normal"
    telefone: Optional[str] = ""
    tempo_estimado_min: Optional[int] = 60
    observacoes: Optional[str] = ""
    comissao: Optional[float] = None
    delay_min: Optional[int] = 0
    penalty_amount: Optional[float] = 0.0
    refuse_reason: Optional[str] = ""
    accepted_at: Optional[str] = None
    refused_at: Optional[str] = None
    created_at: Optional[str] = None


class AcceptIn(BaseModel):
    notes: Optional[str] = ""


class RefuseIn(BaseModel):
    reason: str
