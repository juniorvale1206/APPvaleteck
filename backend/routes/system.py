from datetime import datetime, timezone

from fastapi import APIRouter

from core.config import CLOUDINARY_ENABLED
from core.database import db, client

router = APIRouter(prefix="", tags=["system"])


@router.get("/")
async def root():
    return {"app": "Valeteck", "status": "ok"}


@router.get("/health")
async def health():
    """Health check completo: API + DB + integrações."""
    db_ok = True
    db_error = None
    try:
        await client.admin.command("ping")
    except Exception as e:
        db_ok = False
        db_error = str(e)[:200]
    return {
        "status": "ok" if db_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "api": "ok",
            "database": "ok" if db_ok else f"error: {db_error}",
            "cloudinary": "enabled" if CLOUDINARY_ENABLED else "disabled",
        },
    }
