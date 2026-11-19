
"""
===============================================
File:
Pulsar/backend/general/domain/services/domain_options_service.py

Description:
Metadata-driven DDLB options retrieval service

Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
===============================================
"""

from sqlalchemy import (
    and_,
    case,
    func,
    select
)

from core.database import get_async_session

from general.config.models import (
    FieldDomainConfig,
    FieldDomainValues
)

from general.translation.models import (
    TranslationDictionary
)


# -----------------------------------------------
# Domain Options Service
# -----------------------------------------------
async def get_domain_options(
    schema_name: str,
    table_name: str,
    field_name: str,
    language_code: str = "en"
):
    """
    Fetch DDLB options from field_domain_values.

    Translation is applied only when requires_translation
    is enabled for the domain value.

    The returned structure is normalized for the
    domain-options runtime client.
    """

    if not all((
        schema_name,
        table_name,
        field_name
    )):
        return []

    language_code = (
        language_code or "en"
    ).strip() or "en"

    async for session in get_async_session():

        translated_label = case(
            (
                FieldDomainValues.requires_translation.is_(True),
                func.coalesce(
                    TranslationDictionary.translated_text,
                    FieldDomainValues.domain_value
                )
            ),
            else_=FieldDomainValues.domain_value
        )

        stmt = (
            select(
                FieldDomainValues.domain_value.label("value"),
                translated_label.label("label")
            )
            .select_from(
                FieldDomainValues
            )
            .join(
                FieldDomainConfig,
                and_(
                    FieldDomainConfig.schema_name ==
                    FieldDomainValues.schema_name,

                    FieldDomainConfig.table_name ==
                    FieldDomainValues.table_name,

                    FieldDomainConfig.field_name ==
                    FieldDomainValues.field_name
                )
            )
            .outerjoin(
                TranslationDictionary,
                and_(
                    FieldDomainValues.requires_translation.is_(True),

                    TranslationDictionary.item_code ==
                    FieldDomainValues.domain_value,

                    TranslationDictionary.language_code ==
                    language_code
                )
            )
            .where(
                FieldDomainValues.schema_name ==
                schema_name,

                FieldDomainValues.table_name ==
                table_name,

                FieldDomainValues.field_name ==
                field_name,

                FieldDomainConfig.control_type ==
                "DDLB"
            )
            .order_by(
                FieldDomainValues.sort_order,
                FieldDomainValues.domain_value
            )
        )

        result = await session.execute(
            stmt
        )

        rows = result.all()

        return [
            {
                "value": row.value,
                "label": row.label
            }
            for row in rows
        ]

    return []


# -----------------------------------------------
# Important Learning Points
# -----------------------------------------------
# 1. field_domain_values is the source of DDLB options.
# 2. field_domain_config determines whether a field uses DDLB.
# 3. Domain values are identified by schema, table, and field.
# 4. domain_value is the actual value stored in the physical table.
# 5. Translation is optional and controlled by requires_translation.
# 6. translation_dictionary provides globally shared translations.
# 7. item_code is matched directly with domain_value.
# 8. context_type is not used for domain value translation.
# 9. Missing translations fall back to domain_value.
# 10. Values are ordered by sort_order and domain_value.
# 11. DDDW fields are not handled by this service.
# 12. The returned structure is normalized as {value, label}.
# 13. This service does not interpret primary_key.
# 14. This service does not interpret where_clause.
# 15. This service does not create or resolve parm[n].
