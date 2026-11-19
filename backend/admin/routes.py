# ===============================================
# File: Pulsar/backend/admin/routes.py
# Description: System administration and monitoring APIs
# Change Date: 2026-11-19
# Timezone: Asia/Baku
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

from datetime import datetime, timezone

import psutil

from fastapi import APIRouter, Depends, HTTPException

from general.auth.dependencies import get_current_user
from general.user.schemas.user import UserProfileResponse


router = APIRouter()

# Initialize CPU sampling before the first metrics request.
psutil.cpu_percent(interval=None)


@router.get("/dashboard")
async def get_admin_dashboard():
    """Return administrative dashboard information."""

    return {
        "message": "Admin dashboard is under construction."
    }


@router.get("/system/metrics")
async def get_system_metrics(
    current_user: UserProfileResponse = Depends(get_current_user),
):
    """Return host CPU and memory utilization."""

    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive.",
        )

    memory = psutil.virtual_memory()

    return {
        "cpu": {
            "percent": psutil.cpu_percent(interval=None),
            "logical_cores": psutil.cpu_count(logical=True),
        },
        "memory": {
            "percent": memory.percent,
            "used_bytes": memory.used,
            "total_bytes": memory.total,
            "available_bytes": memory.available,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
