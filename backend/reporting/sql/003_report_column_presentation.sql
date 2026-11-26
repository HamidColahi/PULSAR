-- ============================================================
-- PULSAR Report Column Presentation
-- File: backend/reporting/sql/003_report_column_presentation.sql
-- Modified: 2026-11-26 (Asia/Baku)
-- In collaboration with GPT4 Chat Assistant: Bahram
--
-- Persists per-column label mode, custom label, and header height.
-- ============================================================

BEGIN;

DO $audit_context$
DECLARE
    v_actor_text TEXT;
    v_actor UUID;
    v_ip_text TEXT;
BEGIN
    v_actor_text := NULLIF(current_setting('pulsar.log_user', TRUE), '');
    IF v_actor_text IS NULL THEN
        RAISE EXCEPTION
            'Set pulsar.log_user to an active PULSAR user UUID before applying this migration.';
    END IF;

    v_actor := v_actor_text::UUID;

    IF NOT EXISTS (
        SELECT 1
        FROM pulsar.t_user
        WHERE c_user_id = v_actor
          AND c_user_active IS TRUE
    ) THEN
        RAISE EXCEPTION 'The migration audit actor does not exist or is inactive.';
    END IF;

    v_ip_text := NULLIF(current_setting('pulsar.log_ip', TRUE), '');
    IF v_ip_text IS NULL THEN
        RAISE EXCEPTION
            'Set pulsar.log_ip to the deployment client IP before applying this migration.';
    END IF;

    PERFORM v_ip_text::INET;
    PERFORM set_config('pulsar.log_user', v_actor::TEXT, TRUE);
    PERFORM set_config('pulsar.log_ip', v_ip_text, TRUE);
END;
$audit_context$;

ALTER TABLE pulsar.t_report_column
    ADD COLUMN IF NOT EXISTS label_mode TEXT NOT NULL DEFAULT 'FULL',
    ADD COLUMN IF NOT EXISTS custom_label TEXT NULL,
    ADD COLUMN IF NOT EXISTS header_height_px INTEGER NULL;

ALTER TABLE pulsar.t_report_column
    DROP CONSTRAINT IF EXISTS t_report_column_label_mode_ck,
    DROP CONSTRAINT IF EXISTS t_report_column_header_height_ck;

ALTER TABLE pulsar.t_report_column
    ADD CONSTRAINT t_report_column_label_mode_ck
        CHECK (label_mode IN ('FULL', 'INITIALS', 'CUSTOM')),
    ADD CONSTRAINT t_report_column_header_height_ck
        CHECK (header_height_px IS NULL OR header_height_px BETWEEN 36 AND 160);

UPDATE pulsar.translation_dictionary AS target
SET translated_text = source.translated_text
FROM (
    VALUES
        ('report.labelMode', 'en', 'Header label'),
        ('report.labelMode', 'fa', 'عنوان ستون'),
        ('report.labelFull', 'en', 'Full'),
        ('report.labelFull', 'fa', 'کامل'),
        ('report.labelInitials', 'en', 'Initials'),
        ('report.labelInitials', 'fa', 'حروف اول'),
        ('report.labelCustom', 'en', 'Custom'),
        ('report.labelCustom', 'fa', 'دلخواه'),
        ('report.customLabel', 'en', 'Enter a custom column label'),
        ('report.customLabel', 'fa', 'عنوان دلخواه ستون را وارد کنید'),
        ('report.headerHeight', 'en', 'Header height'),
        ('report.headerHeight', 'fa', 'ارتفاع عنوان')
) AS source(item_code, language_code, translated_text)
WHERE target.item_code = source.item_code
  AND target.language_code = source.language_code;

INSERT INTO pulsar.translation_dictionary
(
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
        ('report.labelMode', 'en', 'Header label'),
        ('report.labelMode', 'fa', 'عنوان ستون'),
        ('report.labelFull', 'en', 'Full'),
        ('report.labelFull', 'fa', 'کامل'),
        ('report.labelInitials', 'en', 'Initials'),
        ('report.labelInitials', 'fa', 'حروف اول'),
        ('report.labelCustom', 'en', 'Custom'),
        ('report.labelCustom', 'fa', 'دلخواه'),
        ('report.customLabel', 'en', 'Enter a custom column label'),
        ('report.customLabel', 'fa', 'عنوان دلخواه ستون را وارد کنید'),
        ('report.headerHeight', 'en', 'Header height'),
        ('report.headerHeight', 'fa', 'ارتفاع عنوان')
) AS source(item_code, language_code, translated_text)
WHERE NOT EXISTS (
    SELECT 1
    FROM pulsar.translation_dictionary AS target
    WHERE target.item_code = source.item_code
      AND target.language_code = source.language_code
);

COMMIT;
