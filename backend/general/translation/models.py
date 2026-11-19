
# File: Pulsar/backend/general/translation/models.py
# Last Modified: 2026-11-16 (Asia/Baku)
# In collaboration with GPT4 Chat Assistant: Bahram

from sqlalchemy import Column, Integer, String, Text

from core.base import Base


class TranslationDictionary(Base):
    __tablename__ = "translation_dictionary"
    __table_args__ = {"schema": "pulsar"}

    id = Column(Integer, primary_key=True, index=True)
    item_code = Column(String, nullable=False)
    language_code = Column(String(10), nullable=False)
    translated_text = Column(Text, nullable=False)

    # context_type = Column(String(50), nullable=True)
    # form_name = Column(String(50), nullable=True)
