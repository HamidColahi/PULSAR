
# ===============================================
# File: Pulsar/backend/general/domain/services/component_Config_service.py
#
# Description:
# Service to fetch component configuration metadata.
#
# ===============================================

from sqlalchemy import and_, select

from core.database import get_async_session

from general.config.models import (
    ComponentsConfig,
    ComponentsBase,
    FieldDomainConfig,
)


async def get_config_options(
    component_name: str,
    field_mode: str,
):
    async for session in get_async_session():

        stmt = (
            select(
                ComponentsConfig.field_name,
                ComponentsConfig.search_mode,

                ComponentsConfig.visible_in_grid,
                ComponentsConfig.visible_in_form,
                ComponentsConfig.visible_in_search,

                ComponentsConfig.is_readonly,
                ComponentsConfig.default_value,
                ComponentsConfig.label_color,
                ComponentsConfig.control_type,
                ComponentsConfig.ordering_index,
                ComponentsConfig.null_able,

                FieldDomainConfig.control_type.label(
                    "domain_control_type"
                ),

                FieldDomainConfig.dddw_select_sql.label(
                    "domain_dddw_select_sql"
                ),
            )
            .select_from(ComponentsConfig)
            .outerjoin(
                ComponentsBase,
                ComponentsBase.component_name
                == ComponentsConfig.component_name,
            )
            .outerjoin(
                FieldDomainConfig,
                and_(
                    FieldDomainConfig.schema_name
                    == ComponentsBase.schm_name,

                    FieldDomainConfig.table_name
                    == ComponentsBase.tbl_name,

                    FieldDomainConfig.field_name
                    == ComponentsConfig.field_name,
                ),
            )
            .where(
                and_(
                    ComponentsConfig.component_name
                    == component_name,

                    ComponentsConfig.field_mode
                    == field_mode,
                )
            )
            .order_by(
                ComponentsConfig.ordering_index,
                ComponentsConfig.field_name,
            )
        )

        result = await session.execute(stmt)
        rows = result.all()

        config_options = []

        for row in rows:

            domain_control_type = (
                row.domain_control_type.upper()
                if row.domain_control_type
                else None
            )

            is_ddlistbox = (
                domain_control_type == "DDLB"
            )

            is_dddw = (
                domain_control_type == "DDDW"
            )

            config_options.append(
                {
                    "field_name": row.field_name,

                    "search_mode": row.search_mode,

                    "visible_in_grid": row.visible_in_grid,
                    "visible_in_form": row.visible_in_form,
                    "visible_in_search": row.visible_in_search,

                    "is_readonly": row.is_readonly,
                    "default_value": row.default_value,
                    "label_color": row.label_color,

                    "control_type": row.control_type,
                    "ordering_index": row.ordering_index,

                    "domain_control_type": domain_control_type,

                    "is_ddlistbox": is_ddlistbox,
                    "is_dddw": is_dddw,

                    "dddw_select_sql": (
                        row.domain_dddw_select_sql
                        if is_dddw
                        else None
                    ),

                    "null_able": row.null_able,
                    "required": row.null_able is False,
                }
            )

        return config_options
