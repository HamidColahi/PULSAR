-- ============================================================
-- PULSAR Initial System Security Administrator Bootstrap
-- File: backend/reporting/sql/002_bootstrap_system_security_admin.template.sql
-- Modified: 2026-11-24 (Asia/Baku)
-- In collaboration with GPT4 Chat Assistant: Bahram
--
-- Replace all three placeholders before execution.
-- The deployment actor must be an existing active PULSAR user.
-- The initial administrator may be the same user or another user.
-- Run once, in the same database session, after migration 001.
-- ============================================================

BEGIN;

DO $bootstrap$
DECLARE
    v_initial_admin_user UUID := '<INITIAL_ADMIN_USER_UUID>'::UUID;
    v_deployment_actor_user UUID := '<DEPLOYMENT_ACTOR_USER_UUID>'::UUID;
    v_deployment_client_ip TEXT := '<DEPLOYMENT_CLIENT_IP>';
    v_permission_id BIGINT;
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pulsar.t_user
        WHERE c_user_id = v_initial_admin_user
          AND c_user_active IS TRUE
    ) THEN
        RAISE EXCEPTION 'Initial administrator user does not exist or is inactive.';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pulsar.t_user
        WHERE c_user_id = v_deployment_actor_user
          AND c_user_active IS TRUE
    ) THEN
        RAISE EXCEPTION 'Deployment actor user does not exist or is inactive.';
    END IF;

    SELECT permission_id
    INTO v_permission_id
    FROM pulsar.t_permission
    WHERE permission_code = 'SECURITY.PERMISSION.GRANT'
      AND scope_type = 'SYSTEM'
      AND scope_key IS NULL
      AND page_key IS NULL
      AND is_active IS TRUE
    LIMIT 1;

    IF v_permission_id IS NULL THEN
        RAISE EXCEPTION 'System permission definition SECURITY.PERMISSION.GRANT was not found.';
    END IF;

    PERFORM set_config(
        'pulsar.log_user',
        v_deployment_actor_user::TEXT,
        TRUE
    );

    PERFORM set_config(
        'pulsar.log_ip',
        v_deployment_client_ip,
        TRUE
    );

    IF NOT EXISTS (
        SELECT 1
        FROM pulsar.t_permit_usracc
        WHERE c_user_id = v_initial_admin_user
          AND permission_id = v_permission_id
          AND is_active IS TRUE
          AND valid_from <= CURRENT_TIMESTAMP
          AND (
                valid_until IS NULL
                OR CURRENT_TIMESTAMP < valid_until
          )
    ) THEN
        INSERT INTO pulsar.t_permit_usracc
        (
            c_user_id,
            permission_id,
            permission_code,
            valid_from,
            valid_until,
            is_active,
            granted_by,
            granted_at,
            grant_reason
        )
        VALUES
        (
            v_initial_admin_user,
            v_permission_id,
            'SECURITY.PERMISSION.GRANT',
            CURRENT_TIMESTAMP,
            NULL,
            TRUE,
            v_deployment_actor_user,
            CURRENT_TIMESTAMP,
            'Initial trusted system security administrator bootstrap'
        );
    END IF;
END;
$bootstrap$;

COMMIT;
