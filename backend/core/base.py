
# =======================================================
# File: Pulsar/backend/core/base.py
# Description: Central SQLAlchemy Declarative Base
# In collaboration with GPT4 Chat Assistant: Bahram
# Last Modified: 2026-11-16 13:10 (Asia/Baku)
# =======================================================

from sqlalchemy.orm import declarative_base  # type: ignore[reportMissingImports]


Base = declarative_base()
