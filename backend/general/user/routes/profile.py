# ================================================
#  File: Pulsar/backend/general/user/routes/profile.py
#  Description: Handles profile creation via DataWindowManager abstraction.
# ================================================

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

#  Internal Imports
from general.user.models.profile import Profile
from general.user.schemas.profile import ProfileCreate
from datawindows.common.utils.datawindow import DataWindowManager
from core.database import get_async_session

router = APIRouter(tags=["Profile"])
#router = APIRouter(prefix="/profile", tags=["Profile"])

# ================================================
# 🧪 Test endpoint to verify router is active
# ================================================
@router.get("/test")
async def test_route():
    return {"message": " Profile router is working!"}

# ================================================
#  POST /profile/create
# 📝 Description: Creates a profile record
#  Output: JSON message + profile ID
# ================================================
@router.post("/create")
async def create_profile(
    profile: ProfileCreate,
    db: AsyncSession = Depends(get_async_session)
):
    try:
        profile_id = str(uuid4())
        profile_data = profile.dict()
        profile_data["profile_id"] = profile_id

        dw = DataWindowManager(Profile, db)
        result = await dw.insert(profile_data)

        return {
            "message": " Profile created successfully",
            "profile_id": result.profile_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================================
#  Notes:
# - This route uses a reusable DataWindowManager to abstract insert logic.
# - Prefix "/profile" means full route is: POST /profile/create
# - Make sure this file is imported in main.py via `routes.profile`
# - Use /profile/test to verify it's being loaded
# ================================================
