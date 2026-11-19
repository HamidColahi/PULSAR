
# ===============================================
# File: backend/general/user/models/user_access.py
# Description: User page access and CRUD permissions model
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# Last Modified: 2026-11-16 (Asia/Baku)
# ===============================================

from sqlalchemy import Boolean, Column, DateTime, String

from core.base import Base


class UserAccess(Base):
    __tablename__ = "t_page_usracc"
    __table_args__ = {"schema": "pulsar"}

    c_user_id = Column(String, primary_key=True)
    page_key = Column(String, primary_key=True)
    c_page_state = Column(String, nullable=False)
    page_level = Column(String, nullable=False)
    c_page_acc_start = Column(DateTime)
    c_page_acc_end = Column(DateTime)

    page_type = Column(String)
    c_page_view = Column(Boolean, nullable=False, default=True)
    c_page_insert = Column(Boolean, nullable=False, default=True)
    c_page_update = Column(Boolean, nullable=False, default=True)
    c_page_delete = Column(Boolean, nullable=False, default=True)

    log_time = Column(DateTime)
    log_state = Column(String)
    log_user = Column(String)
    log_ip = Column(String)


# Important Learning Points
# - CRUD permissions are page-level metadata stored with the existing access row.
# - c_page_update is the database action name for UI Edit.
# - DateTime matches the PostgreSQL timestamp columns.
