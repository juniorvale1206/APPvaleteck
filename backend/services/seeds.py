"""Seeds iniciais (admin/técnico, agendamentos demo, inventário)."""
import logging
import uuid
from datetime import datetime, timezone, timedelta

from core.config import (
    ADMIN_EMAIL, ADMIN_PASSWORD,
    TECH_EMAIL, TECH_PASSWORD,
)
from core.database import db
from core.security import hash_password, verify_password

logger = logging.getLogger("valeteck.seeds")


async def seed_users():
    seeds = [
        {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "name": "Administrador", "role": "admin"},
        {"email": TECH_EMAIL,  "password": TECH_PASSWORD,  "name": "Técnico Demo",  "role": "tecnico"},
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
            logger.info("Seeded user %s", s["email"])
        elif not verify_password(s["password"], existing["password_hash"]):
            await db.users.update_one(
                {"email": s["email"]},
                {"$set": {"password_hash": hash_password(s["password"])}},
            )
            logger.info("Updated password for %s", s["email"])


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
         "placa": "PQR5L01", "empresa": "Topy Pro", "endereco": "R. da Consolacao, 2200 - São Paulo/SP",
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
    logger.info("Seeded %d appointments for user %s", len(samples), user_id)


async def seed_inventory(user_id: str):
    existing = await db.inventory.count_documents({"user_id": user_id})
    if existing > 0:
        return
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    # Para testar logística reversa: 1 já vencido (há 10d em pending_reverse),
    # 1 dentro do prazo (há 2d), e os demais em outros estados
    overdue_start = (now - timedelta(days=10)).isoformat()
    recent_start = (now - timedelta(days=2)).isoformat()
    samples = [
        {"tipo": "Rastreador", "modelo": "Rastreador GPS XT-2000", "imei": "123456789012345", "iccid": "89550100012345678901", "serie": "SN-X2-001", "empresa": "Rastremix", "status": "with_tech",
         "equipment_category": "rastreador", "equipment_value": 300.00},
        {"tipo": "Rastreador", "modelo": "Rastreador GPS Plus", "imei": "234567890123456", "iccid": "89550100012345678902", "serie": "SN-GP-002", "empresa": "Telensat", "status": "with_tech",
         "equipment_category": "rastreador", "equipment_value": 300.00},
        {"tipo": "Bloqueador", "modelo": "Bloqueador Veicular V8", "imei": "", "iccid": "", "serie": "SN-V8-003", "empresa": "Valeteck", "status": "with_tech",
         "equipment_category": "bloqueador", "equipment_value": 200.00},
        {"tipo": "Rastreador", "modelo": "Rastreador Moto MT-100", "imei": "345678901234567", "iccid": "89550100012345678903", "serie": "SN-MT-004", "empresa": "GPS My", "status": "in_transit_to_tech", "tracking_code": "BR123456789BR",
         "equipment_category": "rastreador", "equipment_value": 300.00},
        {"tipo": "Rastreador", "modelo": "Rastreador Híbrido GSM/GPS", "imei": "456789012345678", "iccid": "89550100012345678904", "serie": "SN-HY-005", "empresa": "Topy Pro", "status": "installed", "placa": "BRA1A23",
         "equipment_category": "rastreador", "equipment_value": 300.00},
        # VENCIDO (há 10 dias em pending_reverse)
        {"tipo": "Bloqueador", "modelo": "Bloqueador Anti-Furto BR-9", "imei": "", "iccid": "", "serie": "SN-BR-006", "empresa": "Rastremix", "status": "pending_reverse", "placa": "DEF1B45",
         "equipment_category": "bloqueador", "equipment_value": 200.00,
         "pending_reverse_at": overdue_start},
        # NO PRAZO (há 2 dias em pending_reverse)
        {"tipo": "Rastreador", "modelo": "Rastreador GPS Plus", "imei": "567890123456789", "iccid": "", "serie": "SN-GP-007", "empresa": "Telensat", "status": "pending_reverse", "placa": "JKL3F67",
         "equipment_category": "rastreador", "equipment_value": 300.00,
         "pending_reverse_at": recent_start},
    ]
    for s in samples:
        await db.inventory.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "checklist_id": None,
            "tracking_code": "",
            "placa": "",
            "created_at": now_iso,
            "updated_at": now_iso,
            **s,
        })
    logger.info("Seeded %d inventory items for user %s", len(samples), user_id)
