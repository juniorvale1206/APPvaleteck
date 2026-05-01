from typing import List, Optional
from pydantic import BaseModel


class PhotoIn(BaseModel):
    label: Optional[str] = None
    base64: Optional[str] = ""        # data uri ou raw base64 (entrada)
    url: Optional[str] = None         # URL do Cloudinary (saída preferencial)
    workflow_step: Optional[int] = None
    photo_id: Optional[str] = ""


class RemovedEquipmentIn(BaseModel):
    """Equipamento retirado/trocado durante a O.S (Retirada|Manutenção|Garantia).
    Ao enviar o checklist, será criado um item em inventário com status=pending_reverse.
    """
    tipo: str = "Rastreador"          # Rastreador | Bloqueador | Câmera | Outro
    modelo: Optional[str] = ""
    imei: Optional[str] = ""
    iccid: Optional[str] = ""
    serie: Optional[str] = ""
    empresa: Optional[str] = ""       # se vazio, herda a empresa do checklist
    estado: Optional[str] = "funcional"  # funcional | avariado | defeituoso
    notes: Optional[str] = ""


class ChecklistInput(BaseModel):
    # Veículo
    vehicle_type: Optional[str] = ""
    vehicle_brand: Optional[str] = ""
    vehicle_model: Optional[str] = ""
    vehicle_year: Optional[str] = ""
    vehicle_color: Optional[str] = ""
    vehicle_vin: Optional[str] = ""
    vehicle_odometer: Optional[int] = None
    # Cliente
    nome: str
    sobrenome: str
    placa: str
    telefone: Optional[str] = ""
    obs_iniciais: Optional[str] = ""
    problems_client: List[str] = []
    problems_client_other: Optional[str] = ""
    # Instalação
    empresa: str
    equipamento: str
    tipo_atendimento: Optional[str] = ""
    acessorios: List[str] = []
    obs_tecnicas: Optional[str] = ""
    problems_technician: List[str] = []
    problems_technician_other: Optional[str] = ""
    battery_state: Optional[str] = ""
    battery_voltage: Optional[float] = None
    # Identificação do dispositivo
    imei: Optional[str] = ""
    iccid: Optional[str] = ""
    device_online: Optional[bool] = None
    device_tested_at: Optional[str] = ""
    device_test_message: Optional[str] = ""
    # SLA Timer
    execution_started_at: Optional[str] = ""
    execution_ended_at: Optional[str] = ""
    execution_elapsed_sec: Optional[int] = 0
    # Evidências
    photos: List[PhotoIn] = []
    location: Optional[dict] = None
    location_available: bool = False
    # Assinatura
    signature_base64: Optional[str] = ""
    # Vínculo agenda
    appointment_id: Optional[str] = ""
    # Estado
    status: str = "rascunho"
    # FASE 3 — Integração O.S ↔ Estoque
    removed_equipments: List[RemovedEquipmentIn] = []   # p/ Retirada/Manutenção/Garantia
    installed_from_inventory_id: Optional[str] = None   # item do estoque usado na instalação


class ChecklistOut(BaseModel):
    id: str
    numero: str
    user_id: str
    status: str
    vehicle_type: Optional[str] = ""
    vehicle_brand: Optional[str] = ""
    vehicle_model: Optional[str] = ""
    vehicle_year: Optional[str] = ""
    vehicle_color: Optional[str] = ""
    vehicle_vin: Optional[str] = ""
    vehicle_odometer: Optional[int] = None
    nome: str
    sobrenome: str
    placa: str
    telefone: Optional[str] = ""
    obs_iniciais: Optional[str] = ""
    problems_client: List[str] = []
    problems_client_other: Optional[str] = ""
    empresa: str
    equipamento: str
    tipo_atendimento: Optional[str] = ""
    acessorios: List[str] = []
    obs_tecnicas: Optional[str] = ""
    problems_technician: List[str] = []
    problems_technician_other: Optional[str] = ""
    battery_state: Optional[str] = ""
    battery_voltage: Optional[float] = None
    imei: Optional[str] = ""
    iccid: Optional[str] = ""
    device_online: Optional[bool] = None
    device_tested_at: Optional[str] = ""
    device_test_message: Optional[str] = ""
    execution_started_at: Optional[str] = ""
    execution_ended_at: Optional[str] = ""
    execution_elapsed_sec: Optional[int] = 0
    photos: List[PhotoIn] = []
    location: Optional[dict] = None
    location_available: bool = False
    signature_base64: Optional[str] = ""
    signature_url: Optional[str] = None
    appointment_id: Optional[str] = ""
    alerts: List[str] = []
    created_at: str
    updated_at: str
    sent_at: Optional[str] = None
    removed_equipments: List[RemovedEquipmentIn] = []
    installed_from_inventory_id: Optional[str] = None
    inventory_ops: List[dict] = []  # log de operações aplicadas ao estoque (criado/atualizado)
