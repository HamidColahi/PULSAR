/*
File: PULSAR/pali_analyst_interaction_translation.sql
Description: Translation entries for interactive Pali Analyst controls
Change Date: 2026-11-21 01:00 (Asia/Baku)
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
        ('pulsar.pali_analyst.retry', 'en', 'Retry initialization'),
        ('pulsar.pali_analyst.retry', 'fa', 'تلاش مجدد برای راه‌اندازی'),
        ('pulsar.pali_analyst.questions', 'en', 'Questions & Answers'),
        ('pulsar.pali_analyst.questions', 'fa', 'پرسش‌ها و پاسخ‌ها'),
        ('pulsar.pali_analyst.askPali', 'en', 'Ask Pali about this section'),
        ('pulsar.pali_analyst.askPali', 'fa', 'از پالی درباره این بخش سؤال کنید'),
        ('pulsar.pali_analyst.questionPlaceholder', 'en', 'Ask a question about the current report section or its Colony evidence...'),
        ('pulsar.pali_analyst.questionPlaceholder', 'fa', 'درباره بخش جاری گزارش یا شواهد Colony سؤال خود را بنویسید...'),
        ('pulsar.pali_analyst.questionHint', 'en', 'Ctrl+Enter to send'),
        ('pulsar.pali_analyst.questionHint', 'fa', 'برای ارسال از Ctrl+Enter استفاده کنید'),
        ('pulsar.pali_analyst.ask', 'en', 'Ask Pali'),
        ('pulsar.pali_analyst.ask', 'fa', 'پرسیدن از پالی'),
        ('pulsar.pali_analyst.asking', 'en', 'Pali is preparing an evidence-based answer...'),
        ('pulsar.pali_analyst.asking', 'fa', 'پالی در حال آماده‌سازی پاسخ مبتنی بر شواهد است...')
) AS source(item_code, language_code, translated_text)
WHERE NOT EXISTS (
    SELECT 1
    FROM pulsar.translation_dictionary AS existing
    WHERE existing.item_code = source.item_code
      AND existing.language_code = source.language_code
);
