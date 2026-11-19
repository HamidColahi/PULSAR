# Pulsar/backend/general/user/schemas/profile.py
from pydantic import BaseModel

class ProfileCreate(BaseModel):
    c_profile_type: str
    c_profile_sector: str
    c_profile_title: str


class ProfileOut(BaseModel):
    profile_id: int

    class Config:
        orm_mode = True
