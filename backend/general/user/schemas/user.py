# ===============================
#  File: Pulsar/backend/general/user/schemas/user.py
#  Purpose: User data schemas based on new DB structure
# ===============================

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID

# -------------------------------
# 📤 User profile information
# -------------------------------
class UserProfile(BaseModel):
    id: UUID                              # Maps to c_user_id
    email: EmailStr                       # Maps to c_user_email
    pid: UUID                              # Maps to profile_id
    created_at: Optional[datetime] = None # Maps to c_user_created_at

    class Config:
        from_attributes = True

# -------------------------------
# 🛠 For updating user info
# -------------------------------
class UserUpdate(BaseModel):
    id: UUID                           
    email: Optional[EmailStr] = None

class UserProfileResponse(BaseModel):
    id: UUID
    email: str
    profile_id: UUID
    is_active: bool
