import os
from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


# =====================================================
# LOAD ENVIRONMENT VARIABLES
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(
    dotenv_path=BASE_DIR / ".env",
    override=True,
)


# =====================================================
# APPLICATION CONFIGURATION
# =====================================================

class Config:

    # =================================================
    # SECURITY AND SESSION
    # =================================================

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "PFCG_SECRET_KEY",
    )

    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # =================================================
    # DATABASE CONFIGURATION
    # =================================================

    railway_url = os.getenv("MYSQL_PUBLIC_URL", "").strip()

    if not railway_url:
        raise ValueError(
            "MYSQL_PUBLIC_URL is missing from .env"
        )

    SQLALCHEMY_DATABASE_URI = make_url(railway_url).set(
        drivername="mysql+pymysql",
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # =================================================
    # EMAIL CONFIGURATION
    # =================================================

    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False

    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

    MAIL_DEFAULT_SENDER = (
        "PFCG AI",
        os.getenv("MAIL_DEFAULT_SENDER") or MAIL_USERNAME,
    )