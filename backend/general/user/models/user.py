# ===============================================
#  File: Pulsar/backend/general/user/models/user.py
# 👤 Model: User
#  Description: SQLAlchemy model mapped to the `pulsar.t_user` table.
# ===============================================

from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from core.base import Base

class User(Base):
    __tablename__ = "t_user"
    __table_args__ = {"schema": "pulsar"}  #  Match schema in PostgreSQL

    c_user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
                      index=True, comment="Primary key: user UUID")

    c_user_email = Column(String(255), unique=True, nullable=False, index=True,
                         comment="User's email address")

    c_user_password = Column(Text, nullable=False,
                            comment="Hashed user password")

    c_user_full_name = Column(String(100), nullable=True,
                             comment="User's full name (optional)")

    c_user_active = Column(Boolean, default=True,
                          comment="Indicates if user is active")

    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pulsar.t_profile.profile_id", ondelete="CASCADE"),
        nullable=False,
        comment="Foreign key to Profile"
    )

    c_user_created_at = Column(DateTime, default=datetime.utcnow,
                              comment="Timestamp of registration")

    #  Relationship to profile
    profile = relationship("Profile", back_populates="users", lazy="joined")

