# ===============================================
#  File: Pulsar/backend/general/user/models/profile.py
# 👤 Model: Profile
#  Description: SQLAlchemy model mapped to the `pulsar.t_profile` table.
# ===============================================

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from core.base import Base

class Profile(Base):
    __tablename__ = "t_profile"
    __table_args__ = {"schema": "pulsar"}  #  Match schema in PostgreSQL

    profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
                      comment="Primary key: profile UUID")

    c_profile_type = Column(String(1), nullable=False,
                        comment="Type of profile (e.g., person, company)")

    c_profile_sector = Column(String(1), nullable=False,
                          comment="Sector classification (e.g., A, B, C)")

    c_profile_title = Column(String(255), nullable=False,
                         comment="Full name or company name")

    c_profile_created_at = Column(DateTime, default=datetime.utcnow,
                              comment="Profile creation timestamp")

    #  One-to-many relationship: one profile can have many users
    users = relationship("User", back_populates="profile", lazy="select")

# ===============================================
#  Learning Points:
# - Make sure `__table_args__` specifies schema as "pulsar"
# - Use UUID fields for IDs, with `default=uuid.uuid4`
# - Add back-populated `users` relationship for bidirectional access
# ===============================================
