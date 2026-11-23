/*
File: PULSAR/context_panel_interaction_translation.sql
Description: Translation entries for operational ContextPanel interactions
Change Date: 2026-11-23 (Asia/Baku)
In collaboration with GPT4 Chat Assistant: Bahram
*/

INSERT INTO pulsar.translation_dictionary (
    item_code,
    language_code,
    translated_text
)
SELECT
    source.item_code,
    source.language_code,
    source.translated_text
FROM (
    VALUES
        ('pulsar.context_panel.pin', 'en', 'Pin panel'),
        ('pulsar.context_panel.pin', 'fa', 'ثابت کردن پنل'),
        ('pulsar.context_panel.unpin', 'en', 'Unpin panel'),
        ('pulsar.context_panel.unpin', 'fa', 'برداشتن تثبیت پنل'),
        ('pulsar.context_panel.open', 'en', 'Open panel'),
        ('pulsar.context_panel.open', 'fa', 'باز کردن پنل')
) AS source(item_code, language_code, translated_text)
WHERE NOT EXISTS (
    SELECT 1
    FROM pulsar.translation_dictionary AS existing
    WHERE existing.item_code = source.item_code
      AND existing.language_code = source.language_code
);
