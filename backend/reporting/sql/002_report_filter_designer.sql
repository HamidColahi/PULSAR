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
                AND sql_expression IS NOT NULL
                AND NULLIF(BTRIM(sql_expression), '') IS NOT NULL
                AND LENGTH(sql_expression) <= 4000
            )
        );

COMMIT;
