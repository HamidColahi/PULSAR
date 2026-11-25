-- ============================================================
-- PULSAR Report Filter Designer Extension
-- File: backend/reporting/sql/002_report_filter_designer.sql
-- Modified: 2026-11-26 (Asia/Baku)
-- In collaboration with GPT4 Chat Assistant: Bahram
--
-- Adds recursive negation and developer-authored SQL predicates.
-- The SQL mode remains predicate-only; report source and scope
-- continue to be resolved by the PULSAR component runtime.
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

ALTER TABLE pulsar.t_report_filter
    ADD COLUMN IF NOT EXISTS is_negated BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS sql_expression TEXT NULL;

ALTER TABLE pulsar.t_report_filter
    DROP CONSTRAINT IF EXISTS t_report_filter_node_type_ck,
    DROP CONSTRAINT IF EXISTS t_report_filter_shape_ck;

ALTER TABLE pulsar.t_report_filter
    ADD CONSTRAINT t_report_filter_node_type_ck
        CHECK (node_type IN ('GROUP', 'CONDITION', 'SQL'));

ALTER TABLE pulsar.t_report_filter
    ADD CONSTRAINT t_report_filter_shape_ck
        CHECK (
            (
                node_type = 'GROUP'
                AND logical_operator IN ('AND', 'OR')
                AND field_name IS NULL
                AND operator_code IS NULL
                AND parameter_code IS NULL
                AND value_json IS NULL
                AND sql_expression IS NULL
            )
            OR
            (
                node_type = 'CONDITION'
                AND field_name IS NOT NULL
                AND operator_code IS NOT NULL
                AND logical_operator IS NULL
                AND sql_expression IS NULL
            )
            OR
            (
                node_type = 'SQL'
                AND logical_operator IS NULL
                AND field_name IS NULL
                AND operator_code IS NULL
                AND parameter_code IS NULL
                AND value_json IS NULL
                AND sql_expression IS NOT NULL
                AND NULLIF(BTRIM(sql_expression), '') IS NOT NULL
                AND LENGTH(sql_expression) <= 4000
            )
        );



INSERT INTO pulsar.t_permission
(
    permission_code,
    permission_title,
    page_key,
    scope_type,
    scope_key,
    permission_desc,
    is_active,
    created_by,
    created_at
)
SELECT
    permission_definition.permission_code,
    permission_definition.permission_title,
    page_config.page_key,
    'PAGE',
    page_config.page_key,
    permission_definition.permission_desc,
    TRUE,
    NULLIF(current_setting('pulsar.log_user', TRUE), '')::UUID,
    CURRENT_TIMESTAMP
FROM pulsar.t_report_page_config page_config
CROSS JOIN
(
    VALUES
    (
        'REPORT.FILTER.ADVANCED',
        'Use advanced report filters',
        'Use nested AND/OR groups and advanced filter logic.'
    ),
    (
        'REPORT.FILTER.SQL',
        'Use SQL report filters',
        'Write restricted WHERE predicates using searchable fields of the current Grid.'
    )
) AS permission_definition
(
    permission_code,
    permission_title,
    permission_desc
)
WHERE page_config.is_enabled IS TRUE
ON CONFLICT DO NOTHING;


UPDATE pulsar.translation_dictionary AS target
SET translated_text = source.translated_text
FROM
(
    VALUES
    ('report.addNestedGroup', 'en', 'Add nested group'),
('report.addNestedGroup', 'fa', 'افزودن گروه تو‌در‌تو'),
('report.addSqlFilter', 'en', 'Add SQL Filter'),
('report.addSqlFilter', 'fa', 'افزودن فیلتر SQL'),
('report.sqlFilter', 'en', 'SQL Filter'),
('report.sqlFilter', 'fa', 'فیلتر SQL'),
('report.sqlFilterHelp', 'en', 'Enter only the WHERE predicate expression, without the WHERE keyword, using searchable fields of this Grid. SELECT, joins, comments, multiple statements, and unapproved functions are not allowed.'),
('report.sqlFilterHelp', 'fa', 'فقط عبارت شرطی WHERE را بدون کلمه WHERE و با استفاده از فیلدهای قابل جست‌وجوی همین گرید وارد کنید. SELECT، اتصال جدول‌ها، توضیحات، چند دستور و توابع تأییدنشده مجاز نیستند.'),
('report.filter.standard', 'en', 'Standard'),
('report.filter.standard', 'fa', 'ساده'),
('report.filter.advanced', 'en', 'Advanced'),
('report.filter.advanced', 'fa', 'پیشرفته'),
('report.filter.developer', 'en', 'Developer'),
('report.filter.developer', 'fa', 'توسعه‌دهنده'),
('report.filter.standardHelp', 'en', 'Combine conditions with AND and optionally negate individual conditions.'),
('report.filter.standardHelp', 'fa', 'شرط‌ها را با AND ترکیب کنید و در صورت نیاز هر شرط را به‌صورت مستقل معکوس کنید.'),
('report.filter.advancedHelp', 'en', 'Build nested groups with AND, OR, and NOT.'),
('report.filter.advancedHelp', 'fa', 'گروه‌های تو‌در‌تو با عملگرهای AND، OR و NOT بسازید.')
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
FROM
(
    VALUES
    ('report.addNestedGroup', 'en', 'Add nested group'),
('report.addNestedGroup', 'fa', 'افزودن گروه تو‌در‌تو'),
('report.addSqlFilter', 'en', 'Add SQL Filter'),
('report.addSqlFilter', 'fa', 'افزودن فیلتر SQL'),
('report.sqlFilter', 'en', 'SQL Filter'),
('report.sqlFilter', 'fa', 'فیلتر SQL'),
('report.sqlFilterHelp', 'en', 'Enter only the WHERE predicate expression, without the WHERE keyword, using searchable fields of this Grid. SELECT, joins, comments, multiple statements, and unapproved functions are not allowed.'),
('report.sqlFilterHelp', 'fa', 'فقط عبارت شرطی WHERE را بدون کلمه WHERE و با استفاده از فیلدهای قابل جست‌وجوی همین گرید وارد کنید. SELECT، اتصال جدول‌ها، توضیحات، چند دستور و توابع تأییدنشده مجاز نیستند.'),
('report.filter.standard', 'en', 'Standard'),
('report.filter.standard', 'fa', 'ساده'),
('report.filter.advanced', 'en', 'Advanced'),
('report.filter.advanced', 'fa', 'پیشرفته'),
('report.filter.developer', 'en', 'Developer'),
('report.filter.developer', 'fa', 'توسعه‌دهنده'),
('report.filter.standardHelp', 'en', 'Combine conditions with AND and optionally negate individual conditions.'),
('report.filter.standardHelp', 'fa', 'شرط‌ها را با AND ترکیب کنید و در صورت نیاز هر شرط را به‌صورت مستقل معکوس کنید.'),
('report.filter.advancedHelp', 'en', 'Build nested groups with AND, OR, and NOT.'),
('report.filter.advancedHelp', 'fa', 'گروه‌های تو‌در‌تو با عملگرهای AND، OR و NOT بسازید.')
) AS source(item_code, language_code, translated_text)
WHERE NOT EXISTS
(
    SELECT 1
    FROM pulsar.translation_dictionary AS target
    WHERE target.item_code = source.item_code
      AND target.language_code = source.language_code
);


COMMIT;
