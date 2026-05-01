from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import re
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import bcrypt
import jwt
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field


# ----------------- Logging -----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("valeteck")

# ----------------- Database -----------------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# ----------------- Auth Helpers -----------------
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_DAYS = 7  # mobile: longer-lived bearer tokens


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRES_DAYS),
        "type": "access",
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Não autenticado")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sessão expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user


# ----------------- Constants -----------------
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

PLATE_RE = re.compile(r"^[A-Z]{3}-?\d[A-Z0-9]\d{2}$")


def normalize_plate(p: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (p or "").upper())


def valid_plate(p: str) -> bool:
    s = normalize_plate(p)
    if len(s) != 7:
        return False
    return bool(re.match(r"^[A-Z]{3}\d[A-Z0-9]\d{2}$", s))


# ----------------- Models -----------------
class LoginInput(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str


class TokenOut(BaseModel):
    token: str
    user: UserOut


class PhotoIn(BaseModel):
    label: Optional[str] = None
    base64: str  # data uri or raw base64 (PNG/JPEG)
    workflow_step: Optional[int] = None  # 1=pré-instalação, 2=equipamento, 3=camuflagem, 4=finalização
    photo_id: Optional[str] = ""


class ChecklistInput(BaseModel):
    # Veículo
    vehicle_type: Optional[str] = ""  # carro | moto
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
    appointment_id: Optional[str] = ""
    alerts: List[str] = []
    created_at: str
    updated_at: str
    sent_at: Optional[str] = None


# ----------------- App + Router -----------------
app = FastAPI(title="Valeteck API")
api = APIRouter(prefix="/api")


@api.get("/")
async def root():
    return {"app": "Valeteck", "status": "ok"}


# ----------------- Auth -----------------
@api.post("/auth/login", response_model=TokenOut)
async def login(payload: LoginInput):
    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = create_access_token(user["id"], email)
    return TokenOut(
        token=token,
        user=UserOut(id=user["id"], email=user["email"], name=user["name"], role=user["role"]),
    )


@api.get("/auth/me", response_model=UserOut)
async def me(user=Depends(get_current_user)):
    return UserOut(id=user["id"], email=user["email"], name=user["name"], role=user["role"])


@api.post("/auth/logout")
async def logout(user=Depends(get_current_user)):
    # JWT stateless: client clears token. Endpoint kept for symmetry.
    return {"ok": True}


# ----------------- Reference data -----------------
@api.get("/reference/companies")
async def list_companies():
    return {"companies": COMPANIES}


@api.get("/reference/equipments")
async def list_equipments():
    return {"equipments": EQUIPMENTS}


@api.get("/reference/accessories")
async def list_accessories(vehicle_type: Optional[str] = None):
    if vehicle_type == "moto":
        return {"accessories": ACCESSORIES_MOTO}
    if vehicle_type == "carro":
        return {"accessories": ACCESSORIES_CARRO}
    return {"accessories": list(dict.fromkeys(ACCESSORIES_CARRO + ACCESSORIES_MOTO))}


@api.get("/reference/service-types")
async def list_service_types():
    return {"service_types": SERVICE_TYPES}


@api.get("/reference/battery-states")
async def list_battery_states():
    return {"battery_states": BATTERY_STATES}


@api.get("/reference/problems")
async def list_problems():
    return {"client": PROBLEMS_CLIENT, "technician": PROBLEMS_TECHNICIAN}


# ----------------- Appointments (Agenda) -----------------
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
    delay_min: Optional[int] = 0  # computed at read time
    penalty_amount: Optional[float] = 0.0
    refuse_reason: Optional[str] = ""
    accepted_at: Optional[str] = None
    refused_at: Optional[str] = None
    created_at: Optional[str] = None


# Penalidade de atraso: R$ 100,00 se check-in > 2h após horário agendado
DELAY_PENALTY_THRESHOLD_MIN = 120
DELAY_PENALTY_AMOUNT = 100.00


def _compute_delay(doc: dict) -> dict:
    """Adiciona delay_min e penalty_amount ao doc baseado em scheduled_at vs agora."""
    sched = doc.get("scheduled_at")
    status = doc.get("status", "agendado")
    delay = 0
    penalty = 0.0
    if sched and status in ("agendado", "aceita"):
        try:
            s = datetime.fromisoformat(sched.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            diff = (now - s).total_seconds() / 60
            if diff > 0:
                delay = int(diff)
                if delay > DELAY_PENALTY_THRESHOLD_MIN:
                    penalty = DELAY_PENALTY_AMOUNT
        except Exception:
            pass
    doc["delay_min"] = delay
    doc["penalty_amount"] = penalty
    return doc


@api.get("/appointments", response_model=List[AppointmentOut])
async def list_appointments(user=Depends(get_current_user)):
    cursor = db.appointments.find({"user_id": user["id"]}, {"_id": 0}).sort("scheduled_at", 1)
    docs = await cursor.to_list(length=200)
    return [_compute_delay(d) for d in docs]


@api.get("/appointments/{aid}", response_model=AppointmentOut)
async def get_appointment(aid: str, user=Depends(get_current_user)):
    doc = await db.appointments.find_one({"id": aid, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return _compute_delay(doc)


class AcceptIn(BaseModel):
    notes: Optional[str] = ""


@api.post("/appointments/{aid}/accept", response_model=AppointmentOut)
async def accept_appointment(aid: str, payload: AcceptIn, user=Depends(get_current_user)):
    doc = await db.appointments.find_one({"id": aid, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    if doc["status"] not in ("agendado",):
        raise HTTPException(status_code=400, detail="Apenas OS agendadas podem ser aceitas")
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.appointments.update_one(
        {"id": aid},
        {"$set": {"status": "aceita", "accepted_at": now_iso}},
    )
    updated = await db.appointments.find_one({"id": aid}, {"_id": 0})
    return _compute_delay(updated)


class RefuseIn(BaseModel):
    reason: str


@api.post("/appointments/{aid}/refuse", response_model=AppointmentOut)
async def refuse_appointment(aid: str, payload: RefuseIn, user=Depends(get_current_user)):
    doc = await db.appointments.find_one({"id": aid, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    if doc["status"] not in ("agendado", "aceita"):
        raise HTTPException(status_code=400, detail="OS não pode ser recusada neste estado")
    if not payload.reason.strip():
        raise HTTPException(status_code=400, detail="Motivo da recusa é obrigatório")
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.appointments.update_one(
        {"id": aid},
        {"$set": {"status": "recusada", "refused_at": now_iso, "refuse_reason": payload.reason.strip()}},
    )
    updated = await db.appointments.find_one({"id": aid}, {"_id": 0})
    return _compute_delay(updated)


@api.post("/appointments/seed-new", response_model=AppointmentOut)
async def seed_new_appointment(user=Depends(get_current_user)):
    """Demo: gera uma nova OS aleatória agendada para hoje/amanhã. Útil para testar alertas."""
    import random
    nomes = [
        ("Pedro", "Almeida"), ("Lucas", "Pereira"), ("Ana", "Costa"), ("Beatriz", "Martins"),
        ("Felipe", "Rodrigues"), ("Juliana", "Ferreira"), ("Rafael", "Santos"), ("Camila", "Oliveira"),
    ]
    enderecos = [
        "Av. Brigadeiro Faria Lima, 3000 - São Paulo/SP",
        "R. Augusta, 1500 - São Paulo/SP",
        "Av. Atlântica, 800 - Rio de Janeiro/RJ",
        "Rua XV de Novembro, 200 - Curitiba/PR",
        "Av. Beira Mar, 450 - Florianópolis/SC",
    ]
    placas = ["XPT1A23", "QWE4B56", "ASD7C89", "ZXC1D45", "JKL3F67"]
    empresas_random = random.choice(COMPANIES)
    nome_sob = random.choice(nomes)
    horas_offset = random.choice([1, 3, 6, 24, 28])
    prioridade = random.choices(["alta", "normal", "baixa"], weights=[2, 5, 3])[0]
    eta = random.choice([45, 60, 90, 120])
    tipo_v = random.choice(["carro", "moto"])
    now = datetime.now(timezone.utc)
    aid = str(uuid.uuid4())
    nro_seq = await db.appointments.count_documents({}) + 1
    doc = {
        "id": aid,
        "user_id": user["id"],
        "numero_os": f"OS-2026-{nro_seq:04d}",
        "cliente_nome": nome_sob[0],
        "cliente_sobrenome": nome_sob[1],
        "placa": random.choice(placas),
        "empresa": empresas_random,
        "endereco": random.choice(enderecos),
        "scheduled_at": (now + timedelta(hours=horas_offset)).isoformat(),
        "status": "agendado",
        "checklist_id": None,
        "vehicle_type": tipo_v,
        "prioridade": prioridade,
        "telefone": f"(11) 9{random.randint(1000,9999)}-{random.randint(1000,9999)}",
        "tempo_estimado_min": eta,
        "created_at": now.isoformat(),
    }
    await db.appointments.insert_one(doc)
    doc.pop("_id", None)
    return doc


# ----------------- Pricing / Earnings -----------------
# Tabela base: valor da comissão do técnico por empresa parceira x tipo de atendimento (BRL)
PRICE_TABLE: dict = {
    "Valeteck":  {"Instalação": 120.00, "Manutenção": 80.00, "Retirada": 60.00, "Garantia": 40.00},
    "Rastremix": {"Instalação": 100.00, "Manutenção": 75.00, "Retirada": 55.00, "Garantia": 35.00},
    "GPS My":    {"Instalação": 95.00,  "Manutenção": 70.00, "Retirada": 50.00, "Garantia": 30.00},
    "GPS Joy":   {"Instalação": 90.00,  "Manutenção": 65.00, "Retirada": 50.00, "Garantia": 30.00},
    "Topy Pro":  {"Instalação": 110.00, "Manutenção": 80.00, "Retirada": 55.00, "Garantia": 35.00},
    "Telensat":  {"Instalação": 115.00, "Manutenção": 85.00, "Retirada": 60.00, "Garantia": 40.00},
}
DEFAULT_PRICE = 80.00
SLA_FAST_SEC = 30 * 60      # < 30min → bônus de eficiência
SLA_OK_SEC = 60 * 60        # < 60min → sem bônus (OK)
SLA_FAST_BONUS_PCT = 0.20   # +20% de bônus se SLA rápido
SLA_LATE_PENALTY_PCT = 0.00 # MVP não aplica penalty (mantém motivacional)


def _base_price(empresa: str, tipo: str) -> float:
    return PRICE_TABLE.get(empresa, {}).get(tipo, DEFAULT_PRICE)


def _sla_bonus(base: float, elapsed_sec: int) -> float:
    if not elapsed_sec or elapsed_sec <= 0:
        return 0.0
    if elapsed_sec < SLA_FAST_SEC:
        return round(base * SLA_FAST_BONUS_PCT, 2)
    return 0.0


def _period_start(period: str) -> Optional[datetime]:
    now = datetime.now(timezone.utc)
    if period == "day":
        return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    if period == "week":
        # Segunda-feira da semana atual
        monday = now - timedelta(days=now.weekday())
        return datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)
    if period == "month":
        return datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if period == "all":
        return None
    return None


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


@api.get("/earnings/price-table")
async def earnings_price_table():
    return {"price_table": PRICE_TABLE, "default": DEFAULT_PRICE, "sla_fast_minutes": SLA_FAST_SEC // 60, "sla_fast_bonus_pct": SLA_FAST_BONUS_PCT}


@api.get("/earnings/me", response_model=EarningsSummary)
async def my_earnings(period: str = "month", user=Depends(get_current_user)):
    if period not in ("day", "week", "month", "all"):
        raise HTTPException(status_code=400, detail="period inválido (day|week|month|all)")
    start = _period_start(period)

    # Só OS enviadas/aprovadas/em auditoria/reprovadas contam como serviço realizado
    query: dict = {
        "user_id": user["id"],
        "status": {"$in": ["enviado", "em_auditoria", "aprovado", "reprovado"]},
    }
    if start is not None:
        query["$or"] = [
            {"sent_at": {"$gte": start.isoformat()}},
            {"$and": [{"sent_at": {"$in": [None, ""]}}, {"created_at": {"$gte": start.isoformat()}}]},
        ]
    cursor = db.checklists.find(query, {"_id": 0}).sort("sent_at", -1)
    docs = await cursor.to_list(length=2000)

    jobs: List[EarningJob] = []
    total_base = 0.0
    total_bonus = 0.0
    total_elapsed = 0
    fast_count = 0
    by_company: dict = {}
    by_type: dict = {}

    for d in docs:
        empresa = d.get("empresa", "")
        tipo = d.get("tipo_atendimento") or "Instalação"
        base = _base_price(empresa, tipo)
        elapsed = int(d.get("execution_elapsed_sec") or 0)
        bonus = _sla_bonus(base, elapsed)
        net = round(base + bonus, 2)
        fast = elapsed > 0 and elapsed < SLA_FAST_SEC
        total_base += base
        total_bonus += bonus
        total_elapsed += elapsed
        if fast:
            fast_count += 1
        by_company[empresa] = round(by_company.get(empresa, 0.0) + net, 2)
        by_type[tipo] = round(by_type.get(tipo, 0.0) + net, 2)
        jobs.append(EarningJob(
            id=d["id"],
            numero=d["numero"],
            empresa=empresa,
            tipo_atendimento=tipo,
            nome=d.get("nome", ""),
            sobrenome=d.get("sobrenome", ""),
            placa=d.get("placa", ""),
            base_amount=round(base, 2),
            bonus_amount=round(bonus, 2),
            total_amount=net,
            elapsed_sec=elapsed,
            elapsed_min=elapsed // 60,
            sla_fast=fast,
            sent_at=d.get("sent_at"),
            created_at=d.get("created_at"),
        ))

    count = len(jobs)
    avg_min = (total_elapsed // count // 60) if count > 0 and total_elapsed > 0 else 0
    return EarningsSummary(
        period=period,
        total_base=round(total_base, 2),
        total_bonus=round(total_bonus, 2),
        total_net=round(total_base + total_bonus, 2),
        count=count,
        avg_elapsed_min=avg_min,
        fast_count=fast_count,
        breakdown_by_company=by_company,
        breakdown_by_type=by_type,
        jobs=jobs,
        price_table=PRICE_TABLE,
    )


# ----------------- Device Test (mock) -----------------
class DeviceTestIn(BaseModel):
    imei: str


class DeviceTestOut(BaseModel):
    online: bool
    latency_ms: int
    message: str
    tested_at: str


@api.post("/device/test", response_model=DeviceTestOut)
async def test_device(payload: DeviceTestIn, user=Depends(get_current_user)):
    """Mock de verificação de comunicação do rastreador pelo IMEI.
    Retorna online/offline determinístico baseado no IMEI (~90% online) — placeholder
    para integração futura com API do parceiro (Rastremix/GPS/etc)."""
    import random, hashlib
    imei = (payload.imei or "").strip()
    if not imei or not imei.isdigit() or len(imei) != 15:
        raise HTTPException(status_code=400, detail="IMEI inválido (15 dígitos)")
    # Determinístico: hash do IMEI → 90% online
    seed = int(hashlib.md5(imei.encode()).hexdigest(), 16)
    random.seed(seed)
    online = random.random() < 0.9
    latency = random.randint(80, 380) if online else 0
    now_iso = datetime.now(timezone.utc).isoformat()
    if online:
        msg = f"Dispositivo respondendo — último sinal agora, latência {latency}ms"
    else:
        msg = "Dispositivo offline — verifique alimentação, antena e conexão GSM"
    return DeviceTestOut(online=online, latency_ms=latency, message=msg, tested_at=now_iso)


# ----------------- Checklists -----------------
def _validate_send(c: dict) -> List[str]:
    errors: List[str] = []
    if not c.get("nome", "").strip():
        errors.append("Nome obrigatório")
    if not c.get("sobrenome", "").strip():
        errors.append("Sobrenome obrigatório")
    if not c.get("placa", "").strip():
        errors.append("Placa obrigatória")
    elif not valid_plate(c["placa"]):
        errors.append("Placa inválida")
    if not c.get("empresa", "").strip():
        errors.append("Empresa obrigatória")
    elif c["empresa"] not in COMPANIES:
        errors.append("Empresa inválida")
    if not c.get("equipamento", "").strip():
        errors.append("Equipamento obrigatório")
    photos = c.get("photos", [])
    if len(photos) < 2:
        errors.append("Mínimo de 2 fotos obrigatórias")
    # Validação por grupo de fotos (se algum grupo foi iniciado, deve ter cobertura mínima)
    steps_present = {p.get("workflow_step") for p in photos if p.get("workflow_step")}
    if steps_present and not {1, 2, 3, 4}.issubset(steps_present):
        faltantes = sorted({1, 2, 3, 4} - steps_present)
        errors.append(f"Fotos faltantes nos grupos: {', '.join(str(s) for s in faltantes)}")
    if not c.get("signature_base64", "").strip():
        errors.append("Assinatura obrigatória")
    # Validação de IMEI (15 dígitos) se preenchido
    imei = (c.get("imei") or "").strip()
    if imei and not (imei.isdigit() and len(imei) == 15):
        errors.append("IMEI deve ter 15 dígitos")
    return errors


async def _build_alerts(payload: ChecklistInput, user_id: str, exclude_id: Optional[str] = None) -> List[str]:
    alerts: List[str] = []
    plate = normalize_plate(payload.placa)
    if not plate:
        return alerts
    now = datetime.now(timezone.utc)
    horizon_30 = now - timedelta(days=30)
    q = {"plate_norm": plate, "status": {"$in": ["enviado", "em_auditoria", "aprovado"]}}
    if exclude_id:
        q["id"] = {"$ne": exclude_id}
    cursor = db.checklists.find(q, {"_id": 0, "id": 1, "created_at": 1, "tipo_atendimento": 1, "user_id": 1})
    docs = await cursor.to_list(length=50)
    for d in docs:
        try:
            created = datetime.fromisoformat(d["created_at"].replace("Z", "+00:00"))
        except Exception:
            continue
        if created >= now - timedelta(hours=24):
            alerts.append("Possível duplicidade: já existe checklist enviado para esta placa nas últimas 24h.")
            break
    for d in docs:
        try:
            created = datetime.fromisoformat(d["created_at"].replace("Z", "+00:00"))
        except Exception:
            continue
        if created >= horizon_30 and d.get("tipo_atendimento") == "Instalação":
            if payload.tipo_atendimento in ("Manutenção", "Garantia", "Retirada"):
                alerts.append("Atenção: instalação realizada nos últimos 30 dias — possível garantia.")
                break
    # dedup
    return list(dict.fromkeys(alerts))


def _to_out(doc: dict) -> ChecklistOut:
    return ChecklistOut(**{k: v for k, v in doc.items() if k != "_id" and k != "plate_norm"})


@api.get("/checklists", response_model=List[ChecklistOut])
async def list_checklists(q: Optional[str] = None, user=Depends(get_current_user)):
    query: dict = {"user_id": user["id"]}
    if q:
        s = q.strip()
        regex = {"$regex": re.escape(s), "$options": "i"}
        query["$or"] = [
            {"placa": regex},
            {"nome": regex},
            {"sobrenome": regex},
            {"plate_norm": {"$regex": re.escape(normalize_plate(s)), "$options": "i"}},
        ]
    cursor = db.checklists.find(query, {"_id": 0}).sort("created_at", -1)
    docs = await cursor.to_list(length=500)
    return [_to_out(d) for d in docs]


@api.post("/checklists", response_model=ChecklistOut)
async def create_checklist(payload: ChecklistInput, user=Depends(get_current_user)):
    status = payload.status if payload.status in ("rascunho", "enviado") else "rascunho"
    if status == "enviado":
        errors = _validate_send(payload.dict())
        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))

    now_iso = datetime.now(timezone.utc).isoformat()
    cid = str(uuid.uuid4())
    numero = "VT-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + cid[:6].upper()

    alerts: List[str] = []
    if status == "enviado":
        alerts = await _build_alerts(payload, user["id"])

    doc = {
        "id": cid,
        "numero": numero,
        "user_id": user["id"],
        "status": status,
        "vehicle_type": payload.vehicle_type or "",
        "vehicle_brand": payload.vehicle_brand or "",
        "vehicle_model": payload.vehicle_model or "",
        "vehicle_year": payload.vehicle_year or "",
        "vehicle_color": payload.vehicle_color or "",
        "vehicle_vin": payload.vehicle_vin or "",
        "vehicle_odometer": payload.vehicle_odometer,
        "problems_client": payload.problems_client or [],
        "problems_client_other": payload.problems_client_other or "",
        "problems_technician": payload.problems_technician or [],
        "problems_technician_other": payload.problems_technician_other or "",
        "battery_state": payload.battery_state or "",
        "battery_voltage": payload.battery_voltage,
        "imei": (payload.imei or "").strip(),
        "iccid": (payload.iccid or "").strip(),
        "device_online": payload.device_online,
        "device_tested_at": payload.device_tested_at or "",
        "device_test_message": payload.device_test_message or "",
        "execution_started_at": payload.execution_started_at or "",
        "execution_ended_at": payload.execution_ended_at or "",
        "execution_elapsed_sec": payload.execution_elapsed_sec or 0,
        "appointment_id": payload.appointment_id or "",
        "nome": payload.nome.strip(),
        "sobrenome": payload.sobrenome.strip(),
        "placa": normalize_plate(payload.placa),
        "plate_norm": normalize_plate(payload.placa),
        "telefone": payload.telefone or "",
        "obs_iniciais": payload.obs_iniciais or "",
        "empresa": payload.empresa,
        "equipamento": payload.equipamento,
        "tipo_atendimento": payload.tipo_atendimento or "",
        "acessorios": payload.acessorios or [],
        "obs_tecnicas": payload.obs_tecnicas or "",
        "photos": [p.dict() for p in payload.photos],
        "location": payload.location,
        "location_available": payload.location_available,
        "signature_base64": payload.signature_base64 or "",
        "alerts": alerts,
        "created_at": now_iso,
        "updated_at": now_iso,
        "sent_at": now_iso if status == "enviado" else None,
    }
    await db.checklists.insert_one(doc)
    doc.pop("_id", None)
    if payload.appointment_id:
        await db.appointments.update_one(
            {"id": payload.appointment_id, "user_id": user["id"]},
            {"$set": {"checklist_id": cid, "status": "concluido" if status == "enviado" else "em_andamento"}},
        )
    return _to_out(doc)


@api.get("/checklists/{cid}", response_model=ChecklistOut)
async def get_checklist(cid: str, user=Depends(get_current_user)):
    doc = await db.checklists.find_one({"id": cid, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    return _to_out(doc)


@api.put("/checklists/{cid}", response_model=ChecklistOut)
async def update_checklist(cid: str, payload: ChecklistInput, user=Depends(get_current_user)):
    existing = await db.checklists.find_one({"id": cid, "user_id": user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    if existing["status"] not in ("rascunho",):
        raise HTTPException(status_code=400, detail="Apenas rascunhos podem ser editados")

    status = payload.status if payload.status in ("rascunho", "enviado") else "rascunho"
    if status == "enviado":
        errors = _validate_send(payload.dict())
        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))

    alerts: List[str] = existing.get("alerts", [])
    if status == "enviado":
        alerts = await _build_alerts(payload, user["id"], exclude_id=cid)

    now_iso = datetime.now(timezone.utc).isoformat()
    update = {
        "status": status,
        "vehicle_type": payload.vehicle_type or "",
        "vehicle_brand": payload.vehicle_brand or "",
        "vehicle_model": payload.vehicle_model or "",
        "vehicle_year": payload.vehicle_year or "",
        "vehicle_color": payload.vehicle_color or "",
        "vehicle_vin": payload.vehicle_vin or "",
        "vehicle_odometer": payload.vehicle_odometer,
        "problems_client": payload.problems_client or [],
        "problems_client_other": payload.problems_client_other or "",
        "problems_technician": payload.problems_technician or [],
        "problems_technician_other": payload.problems_technician_other or "",
        "battery_state": payload.battery_state or "",
        "battery_voltage": payload.battery_voltage,
        "imei": (payload.imei or "").strip(),
        "iccid": (payload.iccid or "").strip(),
        "device_online": payload.device_online,
        "device_tested_at": payload.device_tested_at or "",
        "device_test_message": payload.device_test_message or "",
        "execution_started_at": payload.execution_started_at or "",
        "execution_ended_at": payload.execution_ended_at or "",
        "execution_elapsed_sec": payload.execution_elapsed_sec or 0,
        "nome": payload.nome.strip(),
        "sobrenome": payload.sobrenome.strip(),
        "placa": normalize_plate(payload.placa),
        "plate_norm": normalize_plate(payload.placa),
        "telefone": payload.telefone or "",
        "obs_iniciais": payload.obs_iniciais or "",
        "empresa": payload.empresa,
        "equipamento": payload.equipamento,
        "tipo_atendimento": payload.tipo_atendimento or "",
        "acessorios": payload.acessorios or [],
        "obs_tecnicas": payload.obs_tecnicas or "",
        "photos": [p.dict() for p in payload.photos],
        "location": payload.location,
        "location_available": payload.location_available,
        "signature_base64": payload.signature_base64 or "",
        "alerts": alerts,
        "updated_at": now_iso,
    }
    if status == "enviado" and not existing.get("sent_at"):
        update["sent_at"] = now_iso

    await db.checklists.update_one({"id": cid}, {"$set": update})
    doc = await db.checklists.find_one({"id": cid}, {"_id": 0})
    return _to_out(doc)


@api.delete("/checklists/{cid}")
async def delete_checklist(cid: str, user=Depends(get_current_user)):
    existing = await db.checklists.find_one({"id": cid, "user_id": user["id"]})
    if not existing:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    if existing["status"] != "rascunho":
        raise HTTPException(status_code=400, detail="Apenas rascunhos podem ser excluídos")
    await db.checklists.delete_one({"id": cid})
    return {"ok": True}


# ----------------- Startup: indexes + seed -----------------
async def seed_appointments(user_id: str):
    existing = await db.appointments.count_documents({"user_id": user_id})
    if existing > 0:
        return
    now = datetime.now(timezone.utc)
    samples = [
        {"numero_os": "OS-2026-0001", "cliente_nome": "Transportadora Rápida", "cliente_sobrenome": "Ltda.",
         "placa": "BRA2E19", "empresa": "Rastremix", "endereco": "São Miguel Paulista — São Paulo/SP",
         "scheduled_at": (now - timedelta(hours=5, minutes=24)).isoformat(),
         "vehicle_type": "carro", "vehicle_brand": "Mercedes-Benz", "vehicle_model": "Actros 2651", "vehicle_year": "2023",
         "prioridade": "alta", "telefone": "(11) 98888-1111", "tempo_estimado_min": 90,
         "observacoes": "Portaria: pedir por Carlos. Caminhão no pátio 3.", "comissao": 140.00},
        {"numero_os": "OS-2026-0002", "cliente_nome": "Mariana", "cliente_sobrenome": "Souza",
         "placa": "DEF2G45", "empresa": "Telensat", "endereco": "Rua das Flores, 250 - Campinas/SP",
         "scheduled_at": (now + timedelta(hours=2)).isoformat(),
         "vehicle_type": "moto", "vehicle_brand": "Honda", "vehicle_model": "CG 160", "vehicle_year": "2022",
         "prioridade": "normal", "telefone": "(11) 97777-2222", "tempo_estimado_min": 60,
         "observacoes": "", "comissao": 115.00},
        {"numero_os": "OS-2026-0003", "cliente_nome": "Roberto", "cliente_sobrenome": "Lima",
         "placa": "GHI3J67", "empresa": "Valeteck", "endereco": "Rod. Anhanguera, km 25 - Jundiaí/SP",
         "scheduled_at": (now + timedelta(days=1)).isoformat(),
         "vehicle_type": "carro", "vehicle_brand": "Fiat", "vehicle_model": "Strada", "vehicle_year": "2024",
         "prioridade": "normal", "telefone": "(11) 96666-3333", "tempo_estimado_min": 120,
         "observacoes": "", "comissao": 120.00},
        {"numero_os": "OS-2026-0004", "cliente_nome": "Fernanda", "cliente_sobrenome": "Castro",
         "placa": "MNO4K89", "empresa": "GPS My", "endereco": "Av. Independência, 540 - Santo André/SP",
         "scheduled_at": (now + timedelta(days=2)).isoformat(),
         "vehicle_type": "carro", "vehicle_brand": "Volkswagen", "vehicle_model": "T-Cross", "vehicle_year": "2023",
         "prioridade": "baixa", "telefone": "(11) 95555-4444", "tempo_estimado_min": 60,
         "observacoes": "", "comissao": 95.00},
        {"numero_os": "OS-2026-0005", "cliente_nome": "Diego", "cliente_sobrenome": "Vieira",
         "placa": "PQR5L01", "empresa": "Topy Pro", "endereco": "R. da Consolação, 2200 - São Paulo/SP",
         "scheduled_at": (now + timedelta(days=4, hours=3)).isoformat(),
         "vehicle_type": "moto", "vehicle_brand": "Yamaha", "vehicle_model": "Fazer 250", "vehicle_year": "2023",
         "prioridade": "alta", "telefone": "(11) 94444-5555", "tempo_estimado_min": 45,
         "observacoes": "Pagamento antecipado", "comissao": 110.00},
        {"numero_os": "OS-2026-0006", "cliente_nome": "Patrícia", "cliente_sobrenome": "Nunes",
         "placa": "STU6M23", "empresa": "GPS Joy", "endereco": "Av. Paulista, 2500 - São Paulo/SP",
         "scheduled_at": (now + timedelta(days=6)).isoformat(),
         "vehicle_type": "carro", "vehicle_brand": "Toyota", "vehicle_model": "Corolla", "vehicle_year": "2024",
         "prioridade": "normal", "telefone": "(11) 93333-6666", "tempo_estimado_min": 75,
         "observacoes": "", "comissao": 90.00},
    ]
    for s in samples:
        await db.appointments.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "status": "agendado",
            "checklist_id": None,
            "created_at": now.isoformat(),
            **s,
        })
    logger.info(f"Seeded {len(samples)} appointments for user {user_id}")


async def seed_users():
    seeds = [
        {
            "email": os.environ["ADMIN_EMAIL"].lower(),
            "password": os.environ["ADMIN_PASSWORD"],
            "name": "Administrador",
            "role": "admin",
        },
        {
            "email": os.environ["TECH_EMAIL"].lower(),
            "password": os.environ["TECH_PASSWORD"],
            "name": "Técnico Demo",
            "role": "tecnico",
        },
    ]
    for s in seeds:
        existing = await db.users.find_one({"email": s["email"]})
        if existing is None:
            await db.users.insert_one({
                "id": str(uuid.uuid4()),
                "email": s["email"],
                "password_hash": hash_password(s["password"]),
                "name": s["name"],
                "role": s["role"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            logger.info(f"Seeded user {s['email']}")
        elif not verify_password(s["password"], existing["password_hash"]):
            await db.users.update_one(
                {"email": s["email"]},
                {"$set": {"password_hash": hash_password(s["password"])}},
            )
            logger.info(f"Updated password for {s['email']}")


@app.on_event("startup")
async def on_startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.checklists.create_index("id", unique=True)
    await db.checklists.create_index([("user_id", 1), ("created_at", -1)])
    await db.checklists.create_index("plate_norm")
    await db.appointments.create_index("id", unique=True)
    await db.appointments.create_index([("user_id", 1), ("scheduled_at", 1)])
    await seed_users()
    tech = await db.users.find_one({"email": os.environ["TECH_EMAIL"].lower()})
    if tech:
        await seed_appointments(tech["id"])
    logger.info("Valeteck API ready")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


# ----------------- Mount + CORS -----------------
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
