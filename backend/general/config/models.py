
# ===============================================
# File: Pulsar/backend/general/config/models.py
#
# Description:
# SQLAlchemy models for component configuration
# and field domain metadata.
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# Last Modified: 2026-11-16 (Asia/Baku)
# ===============================================

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    text,
)

from core.base import Base


# ===============================================
# Component Configuration
# ===============================================

class ComponentsConfig(Base):
    __tablename__ = "components_config"
    __table_args__ = {"schema": "pulsar"}

    component_name = Column(Text, primary_key=True)
    field_name = Column(Text, primary_key=True)
    field_mode = Column(Text, primary_key=True)

    search_mode = Column(Text, nullable=True)

    visible_in_grid = Column(Boolean, nullable=True)
    visible_in_form = Column(Boolean, nullable=True)
    visible_in_search = Column(Boolean, nullable=True)

    is_readonly = Column(Boolean, nullable=True)

    default_value = Column(Text, nullable=True)
    label_color = Column(Text, nullable=True)

    # UI control type, such as text, numeric, or date.
    # This is not the DDLB/DDDW domain control type.
    control_type = Column(Text, nullable=True)

    ordering_index = Column(Integer, nullable=True)

    null_able = Column(Boolean, nullable=True)


# ===============================================
# Component Base Configuration
# ===============================================

class ComponentsBase(Base):
    __tablename__ = "components_base"
    __table_args__ = {"schema": "pulsar"}

    component_name = Column(Text, primary_key=True)

    tbl_name = Column(Text, nullable=False)
    schm_name = Column(Text, nullable=False)

    primary_key = Column(Text, nullable=False)
    where_clause = Column(Text, nullable=False)


# ===============================================
# Field Domain Configuration
# ===============================================

class FieldDomainConfig(Base):
    __tablename__ = "field_domain_config"
    __table_args__ = {"schema": "pulsar"}

    schema_name = Column(String, primary_key=True)
    table_name = Column(String, primary_key=True)
    field_name = Column(String, primary_key=True)

    # Supported values: DDLB and DDDW.
    control_type = Column(String, nullable=False)

    # Required only when control_type is DDDW.
    dddw_select_sql = Column(Text, nullable=True)


# ===============================================
# Field Domain Values
# ===============================================

class FieldDomainValues(Base):
    __tablename__ = "field_domain_values"

    __table_args__ = (
        ForeignKeyConstraint(
            [
                "schema_name",
                "table_name",
                "field_name",
            ],
            [
                "pulsar.field_domain_config.schema_name",
                "pulsar.field_domain_config.table_name",
                "pulsar.field_domain_config.field_name",
            ],
            name="field_domain_values_field_domain_config_fkey",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "length(trim(domain_value)) > 0",
            name="field_domain_values_value_not_empty",
        ),
        {"schema": "pulsar"},
    )

    schema_name = Column(String, primary_key=True)
    table_name = Column(String, primary_key=True)
    field_name = Column(String, primary_key=True)
    domain_value = Column(String, primary_key=True)

    sort_order = Column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    requires_translation = Column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
