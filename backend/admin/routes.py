# ===============================================
#  File: admin/routes.py
# Description: Routers related to system management (e.g. dashboard, users)
# ===============================================
 
from fastapi import APIRouter

router = APIRouter()
 
@router.get("/dashboard")
async def get_admin_dashboard():
    """
    📊 Admin Dashboard Information (Temporary)
    """
    return {"message": "🛠️ Admin dashboard is under construction."}




