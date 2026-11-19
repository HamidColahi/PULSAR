# ================================================
#  File: Pulsar/backend/general/user/models/profile_image.py
#  Description: SQLAlchemy model for pulsar.t_prfimg
# ================================================

from sqlalchemy import Column, String, ForeignKey, DateTime, CHAR, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ....core.base import Base

class ProfileImage(Base):
    __tablename__ = "t_prfimg"

    c_prfimg_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
                      comment="Primary key: profile image UUID")

    profile_id = Column(UUID(as_uuid=True), ForeignKey("t_profile.profile_id", ondelete="CASCADE"),
                              nullable=False, comment="Foreign key to profile")

    c_prfimg_url = Column(Text, nullable=False,
                       comment="Document or image URL")

    c_prfimg_type = Column(CHAR(1), nullable=False,
                        comment="L = Logo, D = Document, S = Stamp")

    c_prfimg_uploaded_at = Column(DateTime, default=datetime.utcnow,
                               comment="Upload timestamp")

    # Optional relationship
    profile = relationship("Profile", back_populates="images", lazy="select")
