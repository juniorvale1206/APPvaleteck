from typing import Optional
from fastapi import APIRouter

from constants import (
    COMPANIES, EQUIPMENTS, ACCESSORIES_CARRO, ACCESSORIES_MOTO,
    SERVICE_TYPES, BATTERY_STATES, PROBLEMS_CLIENT, PROBLEMS_TECHNICIAN,
)

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get("/companies")
async def list_companies():
    return {"companies": COMPANIES}


@router.get("/equipments")
async def list_equipments():
    return {"equipments": EQUIPMENTS}


@router.get("/accessories")
async def list_accessories(vehicle_type: Optional[str] = None):
    if vehicle_type == "moto":
        return {"accessories": ACCESSORIES_MOTO}
    if vehicle_type == "carro":
        return {"accessories": ACCESSORIES_CARRO}
    return {"accessories": list(dict.fromkeys(ACCESSORIES_CARRO + ACCESSORIES_MOTO))}


@router.get("/service-types")
async def list_service_types():
    return {"service_types": SERVICE_TYPES}


@router.get("/battery-states")
async def list_battery_states():
    return {"battery_states": BATTERY_STATES}


@router.get("/problems")
async def list_problems():
    return {"client": PROBLEMS_CLIENT, "technician": PROBLEMS_TECHNICIAN}
