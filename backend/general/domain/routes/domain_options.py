
# ===============================================
# File:
# Pulsar/backend/general/domain/routes/domain_options.py
#
# Description:
# Metadata-driven DDLB domain options API route
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

from fastapi import (
    APIRouter,
    Query
)

from general.domain.services.domain_options_service import (
    get_domain_options
)


router = APIRouter(
    tags=["domain"]
)


# -----------------------------------------------
# Domain Options
# -----------------------------------------------
@router.get(
    "/domain_options"
)
async def domain_options(
    schema_name: str = Query(
        ...,
        min_length=1,
        description="Physical table schema name"
    ),
    table_name: str = Query(
        ...,
        min_length=1,
        description="Physical table name"
    ),
    field_name: str = Query(
        ...,
        min_length=1,
        description="Physical field name"
    ),
    language_code: str = Query(
        "en",
        min_length=1,
        description="Requested translation language"
    )
):
    """
    Return DDLB options for a physical database field.

    Domain resolution and optional translation are
    delegated to the domain service layer.
    """

    return await get_domain_options(
        schema_name=schema_name,
        table_name=table_name,
        field_name=field_name,
        language_code=language_code
    )


# -----------------------------------------------
# Important Learning Points
# -----------------------------------------------
# 1. This is the only domain_options route file.
# 2. The API path remains /domain_options.
# 3. schema_name, table_name, and field_name identify the domain.
# 4. language_code determines the requested translation language.
# 5. Domain options are retrieved from field_domain_values.
# 6. Optional translations are resolved by the domain service.
# 7. No domain values are hard-coded here.
# 8. No context_type is required for domain identification.
# 9. No primary_key interpretation exists here.
# 10. No where_clause interpretation exists here.
# 11. No parm[n] creation or resolution exists here.
