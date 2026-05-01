"""Constantes de domínio (empresas, equipamentos, acessórios, problemas)."""

COMPANIES = ["Rastremix", "GPS My", "GPS Joy", "Topy Pro", "Telensat", "Valeteck"]
SERVICE_TYPES = ["Instalação", "Manutenção", "Retirada", "Garantia"]
VEHICLE_TYPES = ["carro", "moto"]
BATTERY_STATES = ["Nova", "Em bom estado", "Usada", "Apresentando falhas"]

EQUIPMENTS = [
    "Rastreador GPS XT-2000",
    "Rastreador GPS Plus",
    "Bloqueador Veicular V8",
    "Rastreador Moto MT-100",
    "Rastreador Híbrido GSM/GPS",
    "Bloqueador Anti-Furto BR-9",
]

ACCESSORIES_CARRO = [
    "Alarme e travas", "Vidros elétricos", "Painel", "Ar condicionado",
    "Som / Central multimídia", "Buzina e sirene", "Limpador de para-brisa",
    "Lanterna traseira direita", "Lanterna traseira esquerda", "Freio de mão",
    "Banco elétrico", "Piscas alerta", "Farol alto/baixo direito",
    "Farol alto/baixo esquerdo", "Luz de ré", "Luz de freio / Brake light",
    "Sensor de porta", "Botão de pânico", "Bloqueio de combustível",
    "Lacre anti-violação", "Antena externa",
]
ACCESSORIES_MOTO = [
    "Painel de instrumentos", "Farol alto/baixo", "Lanterna traseira",
    "Luz de freio", "Pisca esquerdo dianteiro", "Pisca esquerdo traseiro",
    "Pisca direito dianteiro", "Pisca direito traseiro", "Buzina",
    "Carenagem esquerda", "Carenagem direita", "Retrovisor esquerdo",
    "Retrovisor direito", "Bateria", "Sirene", "Bloqueio de combustível",
    "Lacre anti-violação",
]

PROBLEMS_CLIENT = [
    "Bateria fraca", "Não liga", "Vidro elétrico não funciona",
    "Painel com falha", "Som não liga", "Ar condicionado não gela",
    "Trava elétrica com defeito", "Farol queimado", "Pisca não funciona",
    "Buzina sem som", "Falha no rastreador anterior",
]
PROBLEMS_TECHNICIAN = [
    "Fiação danificada", "Bateria abaixo de 11V", "Curto-circuito identificado",
    "Conector OBD com falha", "Corrosão em terminais", "Fusível queimado",
    "Chicote com mau contato", "Lacre violado anteriormente",
    "Equipamento anterior com defeito", "Bateria descarregando rápido",
]

CHECKLIST_STATUSES = ["rascunho", "enviado", "em_auditoria", "aprovado", "reprovado"]
INVENTORY_STATUSES = [
    "in_stock",
    "in_transit_to_tech",
    "with_tech",
    "installed",
    "pending_reverse",
    "in_transit_to_hq",
    "received_at_hq",
]

PARTNER_EMPRESA_MAP = {
    "rastremix": "Rastremix",
    "gps_my": "GPS My",
    "gps_joy": "GPS Joy",
    "topy_pro": "Topy Pro",
    "telensat": "Telensat",
    "valeteck": "Valeteck",
}
