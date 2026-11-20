-- ===============================================
-- File: Pulsar/source_trace_analysis_schema.sql
-- Description: Persistent, user-owned P-ATVT interactive analysis sessions
-- Change Date: 2026-11-20 16:30 (Asia/Baku)
-- In collaboration with GPT4 Chat Assistant: Bahram
-- ===============================================

BEGIN;

CREATE TABLE IF NOT EXISTS pulsar.t_source_trace_analysis_session
(
    c_analysis_session_id uuid NOT NULL DEFAULT gen_random_uuid(),
    c_user_id uuid NOT NULL,
    c_topic varchar(200) NOT NULL,
    c_report jsonb NOT NULL,
    c_sections jsonb NOT NULL,
    c_analysis_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    c_current_section_index integer NOT NULL DEFAULT 0,
    c_status varchar(20) NOT NULL DEFAULT 'READY',
    c_definition_code varchar(100),
    c_conversation_id uuid,
    c_created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    c_updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    c_expires_at timestamptz NOT NULL DEFAULT (CURRENT_TIMESTAMP + INTERVAL '30 days'),

    CONSTRAINT pk_source_trace_analysis_session
        PRIMARY KEY (c_analysis_session_id),

    CONSTRAINT ck_source_trace_analysis_session_topic
        CHECK (length(btrim(c_topic)) > 0),

    CONSTRAINT ck_source_trace_analysis_session_sections
        CHECK (jsonb_typeof(c_sections) = 'array'),

    CONSTRAINT ck_source_trace_analysis_session_report
        CHECK (jsonb_typeof(c_report) = 'object'),

    CONSTRAINT ck_source_trace_analysis_session_state
        CHECK (jsonb_typeof(c_analysis_state) = 'object'),

    CONSTRAINT ck_source_trace_analysis_session_index
        CHECK (c_current_section_index >= 0),

    CONSTRAINT ck_source_trace_analysis_session_status
        CHECK (c_status IN ('READY', 'PAUSED', 'COMPLETED', 'STOPPED')),

    CONSTRAINT fk_source_trace_analysis_session_user
        FOREIGN KEY (c_user_id)
        REFERENCES pulsar.t_user (c_user_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE pulsar.t_source_trace_analysis_session IS
    'P-ATVT interactive source trace analysis session / نشست تحلیل تعاملی ردیابی سورس';

COMMENT ON COLUMN pulsar.t_source_trace_analysis_session.c_analysis_session_id IS
    'Stable identifier of the analysis session / شناسه یکتای نشست تحلیل';

COMMENT ON COLUMN pulsar.t_source_trace_analysis_session.c_user_id IS
    'Authenticated owner of the analysis session / مالک نشست تحلیل';

COMMENT ON COLUMN pulsar.t_source_trace_analysis_session.c_report IS
    'Immutable complete Source Trace report / گزارش کامل و تغییرناپذیر Source Trace';

COMMENT ON COLUMN pulsar.t_source_trace_analysis_session.c_sections IS
    'Logical report sections and their analysis checkpoints / بخش‌های منطقی و نقاط کنترل تحلیل';

COMMENT ON COLUMN pulsar.t_source_trace_analysis_session.c_analysis_state IS
    'Compact verified evidence and unresolved analysis state / وضعیت فشرده شواهد و موارد حل‌نشده';

CREATE INDEX IF NOT EXISTS ix_source_trace_analysis_session_user_updated
    ON pulsar.t_source_trace_analysis_session
       (c_user_id, c_updated_at DESC);

CREATE INDEX IF NOT EXISTS ix_source_trace_analysis_session_expiry
    ON pulsar.t_source_trace_analysis_session (c_expires_at);

COMMIT;
