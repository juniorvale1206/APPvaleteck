"""Tabela SLA + preços do Motor de Comissionamento Inteligente (Valeteck).

Cada tipo de serviço possui:
- `code`: identificador único usado na DB
- `name`: rótulo exibido
- `max_minutes`: SLA máximo em minutos; acima disso o valor é cortado em 50%
- `base_value`: valor em R$ pago quando dentro do SLA
- `level_restriction`: se não None, apenas técnicos deste nível podem executar

Júnior ganha R$ 1,00 fixo (sem usar essa tabela) por OS dentro do SLA.
N1 e N2 compartilham a mesma tabela. Apenas N2 pode executar acessórios.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class ServiceTypeCode(str, Enum):
    # Serviços base (N1/N2)
    DESINSTALACAO = "desinstalacao"
    AUDITORIA = "auditoria"
    INSTALACAO_SEM_BLOQUEIO = "instalacao_sem_bloqueio"
    INSTALACAO_COM_BLOQUEIO = "instalacao_com_bloqueio"
    INSTALACAO_BLOQ_ANTIFURTO = "instalacao_bloq_antifurto"
    INSTALACAO_BLOQ_ANTIFURTO_PARTIDA = "instalacao_bloq_antifurto_partida"
    TELEMETRIA_SEM_BLOQUEIO = "telemetria_sem_bloqueio"
    TELEMETRIA_COM_BLOQUEIO = "telemetria_com_bloqueio"
    TELEMETRIA_COMPLETA_CAMERAS = "telemetria_completa_cameras"
    # Acessórios (exclusivos N2)
    ACESSORIO_SMART_CONTROL = "acessorio_smart_control"          # Alarme com partida remota
    ACESSORIO_SENSOR_ESTACIONAMENTO = "acessorio_sensor_estacionamento"


class ServiceTypeDef(BaseModel):
    code: ServiceTypeCode
    name: str
    category: str          # "desinstalacao" | "instalacao" | "telemetria" | "acessorio" | "auditoria"
    max_minutes: int       # SLA máximo
    base_value: float      # R$ quando dentro do SLA
    level_restriction: Optional[str] = None   # "n2" para acessórios


# -------------- Tabela oficial (SLA + preços) --------------
SERVICE_TYPES: dict[str, ServiceTypeDef] = {
    ServiceTypeCode.DESINSTALACAO.value: ServiceTypeDef(
        code=ServiceTypeCode.DESINSTALACAO, name="Desinstalação",
        category="desinstalacao", max_minutes=20, base_value=2.00,
    ),
    ServiceTypeCode.AUDITORIA.value: ServiceTypeDef(
        code=ServiceTypeCode.AUDITORIA, name="Auditoria/Manutenção",
        category="auditoria", max_minutes=30, base_value=3.00,
    ),
    ServiceTypeCode.INSTALACAO_SEM_BLOQUEIO.value: ServiceTypeDef(
        code=ServiceTypeCode.INSTALACAO_SEM_BLOQUEIO, name="Instalação S/ Bloqueio",
        category="instalacao", max_minutes=40, base_value=4.00,
    ),
    ServiceTypeCode.INSTALACAO_COM_BLOQUEIO.value: ServiceTypeDef(
        code=ServiceTypeCode.INSTALACAO_COM_BLOQUEIO, name="Instalação C/ Bloqueio",
        category="instalacao", max_minutes=50, base_value=5.00,
    ),
    ServiceTypeCode.INSTALACAO_BLOQ_ANTIFURTO.value: ServiceTypeDef(
        code=ServiceTypeCode.INSTALACAO_BLOQ_ANTIFURTO, name="Instalação C/ Bloq + Antifurto",
        category="instalacao", max_minutes=60, base_value=6.00,
    ),
    ServiceTypeCode.INSTALACAO_BLOQ_ANTIFURTO_PARTIDA.value: ServiceTypeDef(
        code=ServiceTypeCode.INSTALACAO_BLOQ_ANTIFURTO_PARTIDA,
        name="Instalação C/ Bloq + Antifurto + Partida",
        category="instalacao", max_minutes=70, base_value=7.00,
    ),
    ServiceTypeCode.TELEMETRIA_SEM_BLOQUEIO.value: ServiceTypeDef(
        code=ServiceTypeCode.TELEMETRIA_SEM_BLOQUEIO, name="Telemetria S/ Bloqueio",
        category="telemetria", max_minutes=40, base_value=6.00,
    ),
    ServiceTypeCode.TELEMETRIA_COM_BLOQUEIO.value: ServiceTypeDef(
        code=ServiceTypeCode.TELEMETRIA_COM_BLOQUEIO, name="Telemetria C/ Bloqueio",
        category="telemetria", max_minutes=50, base_value=7.00,
    ),
    ServiceTypeCode.TELEMETRIA_COMPLETA_CAMERAS.value: ServiceTypeDef(
        code=ServiceTypeCode.TELEMETRIA_COMPLETA_CAMERAS,
        name="Telemetria Completa + Câmeras",
        category="telemetria", max_minutes=60, base_value=8.00,
    ),
    ServiceTypeCode.ACESSORIO_SMART_CONTROL.value: ServiceTypeDef(
        code=ServiceTypeCode.ACESSORIO_SMART_CONTROL,
        name="Smart Control (Alarme c/ Partida Remota)",
        category="acessorio", max_minutes=40, base_value=5.00,
        level_restriction="n2",
    ),
    ServiceTypeCode.ACESSORIO_SENSOR_ESTACIONAMENTO.value: ServiceTypeDef(
        code=ServiceTypeCode.ACESSORIO_SENSOR_ESTACIONAMENTO,
        name="Sensor de Estacionamento",
        category="acessorio", max_minutes=60, base_value=10.00,
        level_restriction="n2",
    ),
}


# Constantes do motor
JUNIOR_FIXED_VALUE_PER_OS = 1.00
JUNIOR_GOAL_BONUS_THRESHOLD = 30        # >= 30 OS no mês
JUNIOR_GOAL_BONUS_VALUE = 50.00
JUNIOR_ZERO_RETURNS_BONUS_VALUE = 50.00
N1N2_MONTHLY_GOAL_THRESHOLD = 60        # >= 60 OS no mês → +R$ 2 retroativo por OS no SLA
N1N2_MONTHLY_GOAL_BONUS_PER_OS = 2.00
TUTOR_RESIDUAL_PER_JUNIOR_OS = 1.00     # N3 ganha R$ 1 por cada OS do júnior
TUTOR_BONUS_JUNIOR_GOAL = 1.00          # N3 ganha R$ 1 extra por OS do júnior SE júnior bater meta
RETURN_PENALTY_VALUE = 30.00            # débito por duplicidade 30d do técnico original
WARRANTY_WINDOW_DAYS = 90               # garantia: placa+tipo repetidos em 90d → R$ 0
RETURN_WINDOW_DAYS = 30                 # retorno: placa+tipo repetidos em 30d → multa R$ 30


def get_service_type(code: str) -> Optional[ServiceTypeDef]:
    return SERVICE_TYPES.get(code)


def list_service_types_for_level(level: str) -> list[ServiceTypeDef]:
    """Lista os tipos de serviço executáveis por um nível.

    Júnior/N1 não podem executar acessórios; N2 pode tudo; N3 pode tudo como instrutor.
    """
    out: list[ServiceTypeDef] = []
    for st in SERVICE_TYPES.values():
        if st.level_restriction and st.level_restriction != level:
            # restrição não bate
            if level != "n3":   # N3 (instrutor) também pode executar para demo/suporte
                continue
        out.append(st)
    return out
