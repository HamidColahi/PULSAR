-- ===============================================
-- File: grid_footer_selection.sql
-- Description: Grid footer and multi-row selection translations
-- Modified: 2026-11-26 18:10 (Asia/Baku)
-- In collaboration with GPT4 Chat Assistant: Bahram
-- ===============================================

BEGIN;

INSERT INTO pulsar.translation_dictionary
    (item_code, language_code, translated_text)
VALUES
    ('pulsar.grid.selectedTotal', 'en', 'Selected total'),
    ('pulsar.grid.selectedTotal', 'fa', 'جمع رکوردهای انتخاب‌شده'),
    ('pulsar.grid.allTotal', 'en', 'All records total'),
    ('pulsar.grid.allTotal', 'fa', 'جمع کل رکوردها')
ON CONFLICT (item_code, language_code)
DO UPDATE SET translated_text = EXCLUDED.translated_text;

COMMIT;
