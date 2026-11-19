# ===============================================
#  File: backend/admin/schemas/dashboard.py
# Description: Pydantic schemas related to admin paths
# ===============================================

from pydantic import BaseModel
from typing import Optional

#  Basic design for admin dashboard information
class AdminDashboardResponse(BaseModel):
    user_count: int
    ad_count: int
    system_status: Optional[str] = "OK"
