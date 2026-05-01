"""Configurações globais carregadas via env (.env).

Carrega o .env logo na importação para que outros módulos vejam
os valores ao serem carregados.
"""
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# ---- Database
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

# ---- JWT
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_REFRESH_SECRET = os.environ.get("JWT_REFRESH_SECRET") or (JWT_SECRET + "-refresh")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_MINUTES = int(os.environ.get("JWT_ACCESS_MINUTES", "30"))
JWT_REFRESH_DAYS = int(os.environ.get("JWT_REFRESH_DAYS", "7"))

# ---- Seeds
ADMIN_EMAIL = os.environ["ADMIN_EMAIL"].lower()
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
TECH_EMAIL = os.environ["TECH_EMAIL"].lower()
TECH_PASSWORD = os.environ["TECH_PASSWORD"]

# ---- Integrações
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
PARTNER_WEBHOOK_SECRET = os.environ.get("PARTNER_WEBHOOK_SECRET", "valeteck-partner-dev-secret")

# ---- Cloudinary (opcional — fallback para base64 se não configurado)
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")
CLOUDINARY_FOLDER = os.environ.get("CLOUDINARY_FOLDER", "valeteck")
CLOUDINARY_ENABLED = bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)

# ---- Penalidade de atraso
DELAY_PENALTY_THRESHOLD_MIN = 120
DELAY_PENALTY_AMOUNT = 100.00

# ---- SLA / Pricing
SLA_FAST_SEC = 30 * 60      # < 30 min → bônus
SLA_OK_SEC = 60 * 60        # < 60 min → OK
SLA_FAST_BONUS_PCT = 0.20   # 20% bônus
SLA_LATE_PENALTY_PCT = 0.00

# ---- Gamification XP
XP_PER_OS = 50
XP_BONUS_SLA = 30
XP_BONUS_APPROVED = 20
