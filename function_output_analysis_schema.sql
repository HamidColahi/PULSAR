-- ===============================================
-- File: Pulsar/function_output_analysis_schema.sql
-- Description: Encrypted, user-owned Pali Analyst sessions for Function outputs
-- Change Date: 2026-11-21 04:00 (Asia/Baku)
-- In collaboration with GPT4 Chat Assistant: Bahram
-- ===============================================

BEGIN;

CREATE TABLE IF NOT EXISTS pulsar.t_function_output_analysis_session
(
    c_analysis_session_id uuid NOT NULL DEFAULT gen_random_uuid(),
    c_user_id uuid NOT NULL,
    c_ai_definition_id uuid NOT NULL,
    output_config_id bigint NOT NULL,
    c_definition_code varchar(100) NOT NULL,
    c_topic varchar(200) NOT NULL,
    c_payload_ciphertext bytea NOT NULL,
    c_encryption_nonce bytea NOT NULL,
    c_encryption_tag bytea NOT NULL,
    c_encryption_key_ref varchar(255) NOT NULL,
    c_encryption_key_version varchar(100) NOT NULL,
    c_current_section_index integer NOT NULL DEFAULT 0,
    c_status varchar(20) NOT NULL DEFAULT 'READY',
    c_conversation_id uuid,
    c_created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    c_updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    c_expires_at timestamptz NOT NULL DEFAULT (CURRENT_TIMESTAMP + INTERVAL '30 days'),

    CONSTRAINT pk_function_output_analysis_session
        PRIMARY KEY (c_analysis_session_id),

    CONSTRAINT ck_function_output_analysis_session_topic
        CHECK (length(btrim(c_topic)) > 0),

    CONSTRAINT ck_function_output_analysis_session_ciphertext
        CHECK (octet_length(c_payload_ciphertext) > 0),

    CONSTRAINT ck_function_output_analysis_session_nonce
        CHECK (octet_length(c_encryption_nonce) = 12),

    CONSTRAINT ck_function_output_analysis_session_tag
        CHECK (octet_length(c_encryption_tag) = 16),

    CONSTRAINT ck_function_output_analysis_session_index
        CHECK (c_current_section_index >= 0),

    CONSTRAINT ck_function_output_analysis_session_status
        CHECK (c_status IN ('READY', 'PAUSED', 'COMPLETED', 'STOPPED')),

    CONSTRAINT fk_function_output_analysis_session_user
        FOREIGN KEY (c_user_id)
        REFERENCES pulsar.t_user (c_user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_function_output_analysis_session_definition
        FOREIGN KEY (c_ai_definition_id)
        REFERENCES pulsar.t_ai_definition (c_ai_definition_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_function_output_analysis_session_config
        FOREIGN KEY (output_config_id)
        REFERENCES pulsar.t_function_output_config (output_config_id)
        ON DELETE RESTRICT
);

COMMENT ON TABLE pulsar.t_function_output_analysis_session IS
    'Encrypted Pali Analyst Function output analysis session / نشست رمزنگاری‌شده تحلیل خروجی تابع توسط Pali Analyst';

COMMENT ON COLUMN pulsar.t_function_output_analysis_session.c_user_id IS
    'Authenticated owner of the analysis session / مالک نشست تحلیل';

COMMENT ON COLUMN pulsar.t_function_output_analysis_session.c_ai_definition_id IS
    'Pali Analyst AI definition used by the session / تعریف هوش مصنوعی Pali Analyst';

COMMENT ON COLUMN pulsar.t_function_output_analysis_session.output_config_id IS
    'Function output configuration that grants resource access / پیکربندی خروجی که مجوز منابع را تعیین می‌کند';

COMMENT ON COLUMN pulsar.t_function_output_analysis_session.c_payload_ciphertext IS
    'AES-GCM encrypted Function output, sections, evidence references, and checkpoints / خروجی تابع، بخش‌ها، ارجاعات شواهد و نقاط کنترل رمزنگاری‌شده';

CREATE INDEX IF NOT EXISTS ix_function_output_analysis_session_user_updated
    ON pulsar.t_function_output_analysis_session
       (c_user_id, c_updated_at DESC);

CREATE INDEX IF NOT EXISTS ix_function_output_analysis_session_expiry
    ON pulsar.t_function_output_analysis_session (c_expires_at);

COMMIT;
