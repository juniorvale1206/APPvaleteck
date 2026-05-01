"""Cloud storage helpers (Cloudinary).

Se Cloudinary não estiver configurado (CLOUDINARY_ENABLED=False),
as funções caem em fallback retornando o data URI base64 original
para manter compatibilidade.
"""
import base64 as _b64
import hashlib
import logging
from typing import Optional

from .config import (
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_ENABLED,
    CLOUDINARY_FOLDER,
)

logger = logging.getLogger("valeteck.storage")

_configured = False


def _ensure_configured() -> bool:
    global _configured
    if _configured:
        return True
    if not CLOUDINARY_ENABLED:
        return False
    try:
        import cloudinary  # type: ignore
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
            secure=True,
        )
        _configured = True
        logger.info("Cloudinary configurado: cloud=%s folder=%s", CLOUDINARY_CLOUD_NAME, CLOUDINARY_FOLDER)
        return True
    except Exception as e:
        logger.warning("Falha ao configurar Cloudinary: %s", e)
        return False


def _strip_data_uri(b64: str) -> str:
    if not b64:
        return ""
    if "," in b64:
        return b64.split(",", 1)[1]
    return b64


def upload_base64_image(
    b64: str,
    folder: Optional[str] = None,
    public_id: Optional[str] = None,
) -> Optional[str]:
    """Upload uma imagem em base64 para o Cloudinary e retorna a URL pública.

    Retorna None se Cloudinary não estiver configurado ou em caso de erro.
    """
    if not _ensure_configured():
        return None
    raw = _strip_data_uri(b64)
    if not raw:
        return None
    try:
        import cloudinary.uploader  # type: ignore
        # Detecta um id determinístico p/ idempotência se não veio
        if not public_id:
            public_id = hashlib.sha1(raw.encode("utf-8")[:1024]).hexdigest()[:16]
        result = cloudinary.uploader.upload(
            f"data:image/jpeg;base64,{raw}",
            folder=folder or CLOUDINARY_FOLDER,
            public_id=public_id,
            resource_type="image",
            overwrite=False,
            invalidate=False,
        )
        url = result.get("secure_url") or result.get("url")
        return url
    except Exception as e:
        logger.warning("Cloudinary upload falhou: %s", e)
        return None


def fetch_url_as_bytes(url: str) -> Optional[bytes]:
    """Baixa uma URL Cloudinary (ou qualquer http(s)) e retorna os bytes."""
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=15) as r:  # noqa: S310
            return r.read()
    except Exception as e:
        logger.warning("Falha ao baixar %s: %s", url, e)
        return None


def base64_to_bytes(b64: str) -> Optional[bytes]:
    raw = _strip_data_uri(b64)
    if not raw:
        return None
    try:
        return _b64.b64decode(raw)
    except Exception:
        return None
