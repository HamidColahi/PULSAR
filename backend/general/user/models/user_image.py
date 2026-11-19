# ================================================
#  File: Pulsar/backend/general/user/models/user_image.py
#  Description: SQLAlchemy model for pulsar.t_usrimg
# ================================================

from sqlalchemy import Column, String, ForeignKey, DateTime, CHAR, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ....core.base import Base

class UserImage(Base):
    __tablename__ = "t_usrimg"

    c_usrimg_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
                      comment="Primary key: image UUID")

    c_user_id = Column(UUID(as_uuid=True), ForeignKey("t_user.c_user_id", ondelete="CASCADE"),
                           nullable=False, comment="Foreign key to user")

    c_usrimg_url = Column(Text, nullable=False,
                       comment="Image or file URL")

    c_usrimg_type = Column(CHAR(1), nullable=False,
                        comment="P = Profile, B = Background, O = Other")

    c_usrimg_uploaded_at = Column(DateTime, default=datetime.utcnow,
                               comment="Upload timestamp")

    # Optional relationship
    user = relationship("User", back_populates="images", lazy="select")
