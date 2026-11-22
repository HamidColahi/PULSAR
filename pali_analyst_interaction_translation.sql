/*
File: PULSAR/pali_analyst_interaction_translation.sql
Description: Translation entries for interactive Pali Analyst controls
Change Date: 2026-11-22 23:26 (Asia/Baku)
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
        ('pulsar.pali_analyst.asking', 'fa', 'پالی در حال آماده‌سازی پاسخ مبتنی بر شواهد است...'),
        ('pulsar.pali_analyst.button', 'en', 'Pali Analyst'),
        ('pulsar.pali_analyst.button', 'fa', 'تحلیلگر پالی'),
        ('pulsar.pali_analyst.concepts', 'en', 'Retrieved Colony Concepts'),
        ('pulsar.pali_analyst.concepts', 'fa', 'مفاهیم بازیابی‌شدهٔ Colony'),
        ('pulsar.pali_analyst.conceptsHint', 'en', 'Definitions are retrieved from the Colony concept repository. Table 1 remains authoritative for process sequence and state transitions.'),
        ('pulsar.pali_analyst.conceptsHint', 'fa', 'تعریف‌ها از مخزن مفاهیم Colony بازیابی می‌شوند. برای توالی فرایند و تغییر وضعیت‌ها، Table 1 همچنان مرجع معتبر است.'),
        ('pulsar.pali_analyst.noConcepts', 'en', 'No matching active concepts were found for this section.'),
        ('pulsar.pali_analyst.noConcepts', 'fa', 'مفهوم فعال و مرتبطی برای این بخش پیدا نشد.'),
        ('pulsar.function_result.copy_report', 'en', 'Copy report'),
        ('pulsar.function_result.copy_report', 'fa', 'کپی گزارش'),
        ('pulsar.function_result.print_report', 'en', 'Print report'),
        ('pulsar.function_result.print_report', 'fa', 'چاپ گزارش'),
        ('pulsar.pali_analyst.resumeAnalysis', 'en', 'Analyze Current Section'),
        ('pulsar.pali_analyst.resumeAnalysis', 'fa', 'تحلیل بخش جاری'),
        ('pulsar.pali_analyst.resetAnalysis', 'en', 'Start a new analysis'),
        ('pulsar.pali_analyst.resetAnalysis', 'fa', 'شروع تحلیل جدید'),
        ('pulsar.pali_analyst.resetConfirm', 'en', 'Start a new Pali Analyst session? The current session will remain saved in history, and a new session will be created.'),
        ('pulsar.pali_analyst.resetConfirm', 'fa', 'یک نشست جدید برای تحلیلگر پالی آغاز شود؟ نشست فعلی در سوابق باقی می‌ماند و نشست جدیدی ایجاد خواهد شد.'),
        ('pulsar.pali_analyst.resetFailed', 'en', 'Could not start a new analysis session'),
        ('pulsar.pali_analyst.resetFailed', 'fa', 'ایجاد نشست جدید تحلیل ناموفق بود.'),
        ('pulsar.pali_analyst.copyReport', 'en', 'Copy full analysis'),
        ('pulsar.pali_analyst.copyReport', 'fa', 'کپی کل تحلیل'),
        ('pulsar.pali_analyst.copied', 'en', 'Analysis copied'),
        ('pulsar.pali_analyst.copied', 'fa', 'تحلیل کپی شد'),
        ('pulsar.pali_analyst.copyFailed', 'en', 'Could not copy analysis'),
        ('pulsar.pali_analyst.copyFailed', 'fa', 'کپی تحلیل انجام نشد')
) AS source(item_code, language_code, translated_text)
WHERE NOT EXISTS (
    SELECT 1
    FROM pulsar.translation_dictionary AS existing
    WHERE existing.item_code = source.item_code
      AND existing.language_code = source.language_code
);
