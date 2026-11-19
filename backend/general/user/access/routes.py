# ===============================================
# File:
# backend/general/user/access/routes.py
#
# Description:
# t_page_usracc route registration
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================
from fastapi import APIRouter
from datawindows.common.utils.datawindow import (
    router as t_page_usracc_router
)

t_page_usracc_PREFIX = "/t_page_usracc"
t_page_usracc_TAG = "t_page_usracc"

API_PREFIXES = {
    "t_page_usracc":
        t_page_usracc_PREFIX
}

API_TAGS = {
    "t_page_usracc":
        t_page_usracc_TAG
}

router = APIRouter()

router.include_router(
    t_page_usracc_router
)

# Important Learning Points:
# 1. t_page_usracc route registration remains centralized here.
# 2. Access metadata is resolved by the existing access/datawindow layer.
# 3. This module does not interpret primary_key.
# 4. This module does not interpret where_clause.
# 5. This module does not create or resolve parm[n].
# 6. No table-specific runtime mapping is added here.