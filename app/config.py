
# import os
# from pathlib import Path
# from datetime import timedelta

# from dotenv import load_dotenv


# # =====================================================
# # LOAD ENVIRONMENT VARIABLES
# # =====================================================

# env_path = Path(__file__).resolve().parent.parent / ".env"

# load_dotenv(
#     dotenv_path=env_path,
#     override=True
# )


# # =====================================================
# # APPLICATION CONFIGURATION
# # =====================================================

# class Config:

#     SECRET_KEY = os.getenv(
#         "SECRET_KEY",
#         "PFCG_SECRET_KEY"
#     )

#     # =================================================
#     # DATABASE CONFIGURATION
#     # =================================================

#     railway_url = os.getenv("MYSQL_PUBLIC_URL")

#     if not railway_url:
#         raise ValueError(
#             "MYSQL_PUBLIC_URL is missing from .env"
#         )

#     base_url = railway_url.rsplit("/", 1)[0]

#     SQLALCHEMY_DATABASE_URI = (
#         base_url.replace(
#             "mysql://",
#             "mysql+pymysql://",
#             1
#         )
#         + "/pfcg_db"
#     )

#     SQLALCHEMY_TRACK_MODIFICATIONS = False

#     PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

#     # =================================================
#     # EMAIL CONFIGURATION
#     # =================================================

#     MAIL_SERVER = "smtp.gmail.com"
#     MAIL_PORT = 587
#     MAIL_USE_TLS = True
#     MAIL_USE_SSL = False

#     MAIL_USERNAME = os.getenv("MAIL_USERNAME")
#     MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

#     MAIL_DEFAULT_SENDER = (
#         os.getenv("MAIL_DEFAULT_SENDER")
#         or MAIL_USERNAME
#     )
import os
from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv


# =====================================================
# LOAD ENVIRONMENT VARIABLES
# =====================================================

env_path = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(
    dotenv_path=env_path,
    override=True
)


# =====================================================
# APPLICATION CONFIGURATION
# =====================================================

class Config:

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "PFCG_SECRET_KEY"
    )

    # =================================================
    # DATABASE CONFIGURATION
    # =================================================

       # DATABASE CONFIGURATION
    from sqlalchemy.engine import URL

        # DATABASE CONFIGURATION
    from sqlalchemy.engine import make_url

    railway_url = os.getenv("MYSQL_PUBLIC_URL")
    if not railway_url:
        raise ValueError("MYSQL_PUBLIC_URL is missing from .env")

    SQLALCHEMY_DATABASE_URI = make_url(railway_url).set(
        drivername="mysql+pymysql",
        database="pfcg_db",
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

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
        os.getenv("MAIL_DEFAULT_SENDER")
        or MAIL_USERNAME
    )