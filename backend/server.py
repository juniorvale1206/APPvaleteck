"""Valeteck API — entrypoint enxuto.

A lógica foi modularizada em:
- core/      → config, database, security (JWT), rate_limit, storage
- models/    → Pydantic models por domínio
- services/  → regras de negócio (pricing, plates, pdf, alerts, partners,
               gamification, seeds)
- routes/    → APIRouter por domínio (auth, appointments, checklists, etc.)
- constants.py → catálogos estáticos
"""
import logging

from fastapi import APIRouter, FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware

# core
from core.config import TECH_EMAIL  # ensures .env carregado antes de tudo
from core.database import client, db
from core.rate_limit import limiter

# services
from services.seeds import seed_appointments, seed_inventory, seed_users

# routes
from routes import (
    admin,
    appointments,
    auth,
    checklists,
    closures,
    device,
    earnings,
    gamification,
    inventory,
    ocr,
    partners,
    rankings,
    reference,
    statement,
    system,
)


# ----------------- Logging -----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("valeteck")


# ----------------- FastAPI app -----------------
app = FastAPI(title="Valeteck API", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ----------------- Mount routers under /api -----------------
api = APIRouter(prefix="/api")
api.include_router(system.router)
api.include_router(auth.router)
api.include_router(reference.router)
api.include_router(appointments.router)
api.include_router(checklists.router)
api.include_router(earnings.router)
api.include_router(rankings.router)
api.include_router(gamification.router)
api.include_router(inventory.router)
api.include_router(closures.router)
api.include_router(statement.router)
api.include_router(device.router)
api.include_router(ocr.router)
api.include_router(partners.router)
api.include_router(admin.router)
app.include_router(api)


# ----------------- CORS -----------------
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------- Startup / Shutdown -----------------
@app.on_event("startup")
async def on_startup():
    # Indexes — UNIQUE
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.checklists.create_index("id", unique=True)
    await db.appointments.create_index("id", unique=True)

    # Indexes — performance
    # Histórico do técnico ordenado por data (já existia)
    await db.checklists.create_index([("user_id", 1), ("created_at", -1)])
    # Filtro de earnings/rankings (status + envio)
    await db.checklists.create_index([("user_id", 1), ("status", 1), ("sent_at", -1)])
    # Busca por placa
    await db.checklists.create_index("plate_norm")
    # Agenda — ordenação cronológica por técnico
    await db.appointments.create_index([("user_id", 1), ("scheduled_at", 1)])
    # Filas de sync e dashboards (status + recente)
    await db.appointments.create_index([("user_id", 1), ("status", 1), ("scheduled_at", -1)])

    # --- Novos módulos (v2) ---
    # Inventory: dashboard do técnico + detecção de atrasos
    await db.inventory.create_index([("user_id", 1), ("status", 1)])
    await db.inventory.create_index([("user_id", 1), ("status", 1), ("reverse_deadline_at", 1)])
    await db.inventory.create_index("serial_number")
    # Closures: fechamento mensal por técnico/mês
    await db.closures.create_index([("user_id", 1), ("year", -1), ("month", -1)], unique=True)
    # Aprovações pendentes (admin) e regras de duplicidade
    await db.checklists.create_index([("validation_status", 1), ("sent_at", -1)])
    await db.checklists.create_index([("plate_norm", 1), ("status", 1), ("created_at", -1)])

    # Seeds
    await seed_users()
    tech = await db.users.find_one({"email": TECH_EMAIL})
    if tech:
        await seed_appointments(tech["id"])
        await seed_inventory(tech["id"])
    logger.info("Valeteck API ready (v2 modular)")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()
