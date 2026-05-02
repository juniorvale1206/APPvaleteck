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
    # Motor de Comissionamento — tipo de serviço oficial (obrigatório a partir da v14)
    service_type_code: Optional[str] = ""     # código da tabela SERVICE_TYPES
    # v14.1 — Anti-fraude SLA (server-side timestamps)
    phase: Optional[str] = "draft"            # draft | awaiting_equipment_photo | in_execution | finalized
    checklist_sent_at: Optional[str] = ""     # server-side: momento do "Enviar Checklist Inicial"
    equipment_photo_at: Optional[str] = ""    # server-side: momento do upload da foto
    equipment_photo_delay_sec: Optional[int] = 0  # delay entre checklist_sent_at e equipment_photo_at
    equipment_photo_flag: Optional[bool] = False   # true se passou de 180s
    equipment_photo_url: Optional[str] = ""   # URL/base64 da foto unificada (rastreador+IMEI+placa)
    service_finished_at: Optional[str] = ""   # server-side: momento do "Finalizar OS"
    sla_total_sec: Optional[int] = 0          # diff entre checklist_sent_at e service_finished_at
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
    numero: Optional[str] = ""
    user_id: str
    status: str
    vehicle_type: Optional[str] = ""
    vehicle_brand: Optional[str] = ""
    vehicle_model: Optional[str] = ""
    vehicle_year: Optional[str] = ""
    vehicle_color: Optional[str] = ""
    vehicle_vin: Optional[str] = ""
    vehicle_odometer: Optional[int] = None
    nome: Optional[str] = ""
    sobrenome: Optional[str] = ""
    placa: Optional[str] = ""
    telefone: Optional[str] = ""
    obs_iniciais: Optional[str] = ""
    problems_client: List[str] = []
    problems_client_other: Optional[str] = ""
    empresa: Optional[str] = ""
    equipamento: Optional[str] = ""
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
    # Motor de Comissionamento
    service_type_code: Optional[str] = ""
    service_type_name: Optional[str] = ""
    sla_max_minutes: Optional[int] = 0
    sla_base_value: Optional[float] = 0.0
    sla_within: Optional[bool] = None
    # v14.1 — Anti-fraude SLA (server-side)
    phase: Optional[str] = "draft"
    checklist_sent_at: Optional[str] = ""
    equipment_photo_at: Optional[str] = ""
    equipment_photo_delay_sec: Optional[int] = 0
    equipment_photo_flag: Optional[bool] = False
    equipment_photo_url: Optional[str] = ""
    service_finished_at: Optional[str] = ""
    sla_total_sec: Optional[int] = 0
    # v14 Fase 3C — Check-in/out do painel (antifraude visual)
    dashboard_photo_in_url: Optional[str] = ""
    dashboard_photo_in_at: Optional[str] = ""
    dashboard_photo_in_valid: Optional[bool] = None
    dashboard_photo_in_reason: Optional[str] = ""
    dashboard_photo_in_confidence: Optional[float] = 0.0
    dashboard_photo_out_url: Optional[str] = ""
    dashboard_photo_out_at: Optional[str] = ""
    dashboard_photo_out_valid: Optional[bool] = None
    dashboard_photo_out_reason: Optional[str] = ""
    dashboard_photo_out_confidence: Optional[float] = 0.0
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
    inventory_ops: List[dict] = []
    # Motor de regras pós-aprovação
    validation_status: Optional[str] = "pending"   # pending|valido|duplicidade_garantia
    validation_bonus: Optional[float] = 0.0         # R$ 5,00 se valido
    approved_at: Optional[str] = None
    approved_by_id: Optional[str] = None
    approved_by_name: Optional[str] = None
    rejected_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    duplicate_of: Optional[str] = None               # id do checklist original se duplicado
