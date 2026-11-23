# ===============================================
# File:
# Pulsar/backend/main.py
#
# Description:
# Main FastAPI application and router registration
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# Last Modified: 2026-11-24 (Asia/Baku)
# ===============================================

import json
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import AsyncSessionLocal, engine


# -----------------------------------------------
# Static Routers
# -----------------------------------------------
from general.auth.routes import (
    router as auth_router
)
from admin.routes import (
    router as admin_router
)
from general.user.routes.profile import (
    router as profile_router
)
from general.user.routes.register import (
    router as register_router
)
from general.translation.routes import (
    router as translation_router
)
from general.domain.routes import (
    domain_options as domain_options_router
)
from general.config.routes import (
    router as config_router
)
from general.user.access.routes import (
    router as user_access_router
)
from general.functions.function_executor import (
    router as function_executor_router
)
from ai_avatar.routes import (
    router as ai_avatar_router
)
from source_trace.routes import (
    router as source_trace_router
)
from general.permissions.routes import (
    router as permission_router
)
from reporting.routes import (
    router as report_router
)


# -----------------------------------------------
# Dynamic Metadata DataWindow
# -----------------------------------------------
from datawindows.common.utils.datawindow import (
    router as datawindow_router
)


# -----------------------------------------------
# Dynamic Runtime Routes
# -----------------------------------------------
from core.dynamic_routes import (
    register_dynamic_routes
)
from core.page_runtime import (
    router as page_runtime_router
)
from core.component_where import (
    router as component_where_router
)
from core.component_key import (
    router as component_key_router
)


# -----------------------------------------------
# Logger Setup
# -----------------------------------------------
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format=(
        "%(asctime)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    handlers=[
        logging.StreamHandler()
    ]
)


# ===============================================
# Load CORS Origins from JSON
# ===============================================
CORS_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "shared_config",
    "cors_origins.json"
)

try:
    with open(
        CORS_CONFIG_PATH,
        "r"
    ) as file:
        origins = json.load(file)

        if not isinstance(
            origins,
            list
        ):
            raise ValueError(
                "CORS origins JSON must be a list of strings."
            )

except Exception as exc:
    raise RuntimeError(
        f"Failed to load CORS origins from "
        f"{CORS_CONFIG_PATH}: {exc}"
    )


# ===============================================
# Lifespan
# ===============================================
@asynccontextmanager
async def lifespan(
    app: FastAPI
):
    logger.info(
        "Starting Pulsar Backend..."
    )

    try:
        async with AsyncSessionLocal() as session:
            await register_dynamic_routes(
                app,
                session
            )

        yield

    finally:
        await engine.dispose()

        logger.info(
            "Backend shutdown complete."
        )


# ===============================================
# Initialize FastAPI App
# ===============================================
app = FastAPI(
    title="Pulsar Backend",
    description=(
        "High-performance backend for Pulsar Platform "
        "using FastAPI + PostgreSQL"
    ),
    version="1.0.0",
    lifespan=lifespan
)


# ===============================================
# Enable CORS Middleware
# ===============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ===============================================
# Static Routers
# ===============================================
app.include_router(
    auth_router
)

app.include_router(
    admin_router,
    prefix="/admin",
    tags=["Admin"]
)

app.include_router(
    profile_router,
    prefix="/profile",
    tags=["Profile"]
)

app.include_router(
    register_router,
    prefix="/auth",
    tags=["Register"]
)

app.include_router(
    translation_router
)

app.include_router(
    domain_options_router.router,
    prefix="/common",
    tags=["domain"]
)

app.include_router(
    config_router
)

app.include_router(
    user_access_router,
    prefix="/access",
    tags=["user_access"]
)


# ===============================================
# Panel Function Executor
# ===============================================
app.include_router(
    function_executor_router
)


# ===============================================
# AI Avatar Runtime Router
# ===============================================
app.include_router(
    ai_avatar_router
)


# ===============================================
# Source Trace Engineering Router
# ===============================================
app.include_router(
    source_trace_router
)

app.include_router(
    permission_router
)

app.include_router(
    report_router
)



# ===============================================
# Page Runtime Router
# ===============================================
app.include_router(
    page_runtime_router,
    prefix="/page",
    tags=["Page Runtime"]
)


# ===============================================
# Component Where Resolver
# ===============================================
app.include_router(
    component_where_router
)


# ===============================================
# Component Key Resolver
# ===============================================
app.include_router(
    component_key_router
)


# ===============================================
# Dynamic DataWindow Router
# ===============================================
app.include_router(
    datawindow_router
)


# ===============================================
# Health Check
# ===============================================
@app.get("/")
async def root():
    return {
        "message":
            "Pulsar backend is up and running!"
    }


# ===============================================
# Important Learning Points
# ===============================================
# 1. Dynamic metadata DataWindow routes are registered at application startup.
# 2. Page runtime routes are available under /page.
# 3. Component where_clause resolution is registered under /runtime.
# 4. Component primary-key resolution is registered under /runtime.
# 5. component_where.py exclusively owns where_clause semantics.
# 6. component_key.py exclusively owns primary-key semantics.
# 7. component_data.py remains the CRUD/query execution layer.
# 8. The database remains the source of truth for runtime metadata.
# 9. No table-specific primary-key or parm mapping is defined in main.py.
# 10. Panel Functions are executed through registered function metadata.
# 11. AI Avatar runtime routes are registered independently under /ai-avatar.
# 12. Source Trace is registered as an independent engineering tool router.
# 13. All application database sessions use the centralized database module.
# 14. The shared database engine is disposed during application shutdown.
