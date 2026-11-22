/*
File: PULSAR/pali_analyst_ollama_resource_profile.sql
Description: Conservative Ollama runtime limits for Pali Analyst
Change Date: 2026-11-22 23:26 (Asia/Baku)
In collaboration with GPT4 Chat Assistant: Bahram
*/

BEGIN;

DO $$
DECLARE
    v_updated integer;
BEGIN
    UPDATE pulsar.t_ai_operation AS operation
    SET
        c_parameters = COALESCE(operation.c_parameters, '{}'::jsonb)
            || jsonb_build_object(
                'runtime_limits',
                jsonb_build_object(
                    'num_thread', 4,
                    'num_ctx', 4096,
                    'num_predict', 2048
                )
            ),
        c_updated_at = CURRENT_TIMESTAMP
    FROM pulsar.t_ai_definition_operation AS definition_operation
    JOIN pulsar.t_ai_definition AS definition
      ON definition.c_ai_definition_id = definition_operation.c_ai_definition_id
    JOIN pulsar.t_ai_model AS model
      ON model.c_ai_model_id = operation.c_ai_model_id
    JOIN pulsar.t_ai_provider AS provider
      ON provider.c_ai_provider_id = model.c_ai_provider_id
    WHERE definition_operation.c_ai_operation_id = operation.c_ai_operation_id
      AND definition.c_definition_code = 'PULSAR_ANALYST'
      AND definition.c_enabled = TRUE
      AND upper(definition.c_state) = 'ACTIVE'
      AND definition_operation.c_is_default = TRUE
      AND upper(definition_operation.c_state) = 'ACTIVE'
      AND upper(operation.c_state) = 'ACTIVE'
      AND upper(model.c_state) = 'ACTIVE'
      AND upper(provider.c_state) = 'ACTIVE'
      AND upper(provider.c_provider_code) = 'OLLAMA';

    GET DIAGNOSTICS v_updated = ROW_COUNT;

    IF v_updated <> 1 THEN
        RAISE EXCEPTION
            'Expected exactly one active default Ollama operation for PULSAR_ANALYST; updated % rows.',
            v_updated;
    END IF;
END;
$$;

COMMIT;

SELECT
    definition.c_definition_code,
    operation.c_operation_code,
    model.c_model_code,
    provider.c_provider_code,
    operation.c_parameters->'runtime_limits' AS runtime_limits,
    operation.c_updated_at
FROM pulsar.t_ai_definition AS definition
JOIN pulsar.t_ai_definition_operation AS definition_operation
  ON definition_operation.c_ai_definition_id = definition.c_ai_definition_id
JOIN pulsar.t_ai_operation AS operation
  ON operation.c_ai_operation_id = definition_operation.c_ai_operation_id
JOIN pulsar.t_ai_model AS model
  ON model.c_ai_model_id = operation.c_ai_model_id
JOIN pulsar.t_ai_provider AS provider
  ON provider.c_ai_provider_id = model.c_ai_provider_id
WHERE definition.c_definition_code = 'PULSAR_ANALYST'
  AND definition_operation.c_is_default = TRUE
  AND upper(definition_operation.c_state) = 'ACTIVE'
  AND upper(operation.c_state) = 'ACTIVE'
  AND upper(provider.c_provider_code) = 'OLLAMA';
