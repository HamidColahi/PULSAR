# ===============================================
# File: Pulsar/backend/general/auth/security.py
# Description: Password hashing and JWT token utilities
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

import os
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from jose import jwt
from passlib.context import CryptContext

load_dotenv()

# =================================================
# JWT Configuration
# =================================================
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "super-secret-key"
)

ALGORITHM = os.getenv(
    "ALGORITHM",
    "HS256"
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "30"
    )
)

# =================================================
# Password Hashing
# =================================================
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def get_password_hash(
    password: str
) -> str:
    """
    Hash the input password.
    """
    return pwd_context.hash(
        password
    )

def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """
    Verify a plain password against its stored hash.
    """
    return pwd_context.verify(
        plain_password,
        hashed_password
    )

# =================================================
# JWT Access Token
# =================================================
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    """
    to_encode = data.copy()

    expire = (
        datetime.utcnow() +
        (
            expires_delta
            or timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )
    )

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

# Important Learning Points:
# 1. JWT configuration is loaded from the environment.
# 2. .env is loaded before SECRET_KEY and ALGORITHM are read.
# 3. The fallback SECRET_KEY matches the authentication dependency.
# 4. create_access_token and get_current_user therefore use the same JWT contract.
# 5. Password hashing remains independent from JWT authentication.
# 6. No frontend code is responsible for JWT signing or validation.