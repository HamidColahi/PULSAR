#  File: Pulsar/backend/core/config.py
"""
Project settings using Pydantic BaseSettings
The settings values ​​are read from the .env file
"""

from pydantic_settings import BaseSettings 

class Settings(BaseSettings):
    APP_DEBUG: bool = False
    DATABASE_URL: str

    #  Add these for JWT authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = {
        "env_file": ".env",
        "extra": "allow",
    }

settings = Settings()

# Optional for direct imports in other modules
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
