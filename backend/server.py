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


class ChecklistInput(BaseModel):
    # Veículo
    vehicle_type: Optional[str] = ""  # carro | moto
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
    battery_state: Optional[str] = ""  # Nova | Em bom estado | Usada | Apresentando falhas
    battery_voltage: Optional[float] = None  # in Volts
    # Evidências
    photos: List[PhotoIn] = []
    location: Optional[dict] = None
    location_available: bool = False
    # Assinatura
    signature_base64: Optional[str] = ""
    # Vínculo agenda
    appointment_id: Optional[str] = ""
    # Estado
    status: str = "rascunho"  # rascunho | enviado


class ChecklistOut(BaseModel):
    id: str
    numero: str
    user_id: str
    status: str
    vehicle_type: Optional[str] = ""
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
    status: str  # agendado | em_andamento | concluido
    checklist_id: Optional[str] = None
    vehicle_type: Optional[str] = ""


@api.get("/appointments", response_model=List[AppointmentOut])
async def list_appointments(user=Depends(get_current_user)):
    cursor = db.appointments.find({"user_id": user["id"]}, {"_id": 0}).sort("scheduled_at", 1)
    return await cursor.to_list(length=200)


@api.get("/appointments/{aid}", response_model=AppointmentOut)
async def get_appointment(aid: str, user=Depends(get_current_user)):
    doc = await db.appointments.find_one({"id": aid, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return doc


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
    if len(c.get("photos", [])) < 2:
        errors.append("Mínimo de 2 fotos obrigatórias")
    if not c.get("signature_base64", "").strip():
        errors.append("Assinatura obrigatória")
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
        "problems_client": payload.problems_client or [],
        "problems_client_other": payload.problems_client_other or "",
        "problems_technician": payload.problems_technician or [],
        "problems_technician_other": payload.problems_technician_other or "",
        "battery_state": payload.battery_state or "",
        "battery_voltage": payload.battery_voltage,
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
        "problems_client": payload.problems_client or [],
        "problems_client_other": payload.problems_client_other or "",
        "problems_technician": payload.problems_technician or [],
        "problems_technician_other": payload.problems_technician_other or "",
        "battery_state": payload.battery_state or "",
        "battery_voltage": payload.battery_voltage,
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
        {"numero_os": "OS-2026-0001", "cliente_nome": "Carlos", "cliente_sobrenome": "Mendes",
         "placa": "ABC1D23", "empresa": "Rastremix", "endereco": "Av. Paulista, 1000 - São Paulo/SP",
         "scheduled_at": (now + timedelta(hours=2)).isoformat(), "vehicle_type": "carro"},
        {"numero_os": "OS-2026-0002", "cliente_nome": "Mariana", "cliente_sobrenome": "Souza",
         "placa": "DEF2G45", "empresa": "Telensat", "endereco": "Rua das Flores, 250 - Campinas/SP",
         "scheduled_at": (now + timedelta(hours=5)).isoformat(), "vehicle_type": "moto"},
        {"numero_os": "OS-2026-0003", "cliente_nome": "Roberto", "cliente_sobrenome": "Lima",
         "placa": "GHI3J67", "empresa": "Valeteck", "endereco": "Rod. Anhanguera, km 25 - Jundiaí/SP",
         "scheduled_at": (now + timedelta(days=1)).isoformat(), "vehicle_type": "carro"},
    ]
    for s in samples:
        await db.appointments.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "status": "agendado",
            "checklist_id": None,
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
