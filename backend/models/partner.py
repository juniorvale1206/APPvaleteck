from typing import Optional
from pydantic import BaseModel


class PartnerAppointmentWebhook(BaseModel):
    partner: str
    user_email: str
    numero_os: str
    cliente_nome: str
    cliente_sobrenome: str
    placa: str
    endereco: str
    scheduled_at: str
    telefone: Optional[str] = ""
    vehicle_type: Optional[str] = "carro"
    vehicle_brand: Optional[str] = ""
    vehicle_model: Optional[str] = ""
    vehicle_year: Optional[str] = ""
    prioridade: Optional[str] = "normal"
    tempo_estimado_min: Optional[int] = 60
    observacoes: Optional[str] = ""
    comissao: Optional[float] = None
    secret: Optional[str] = ""
