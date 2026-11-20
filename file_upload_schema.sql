/*
File: PULSAR/file_upload_schema.sql
Description: Metadata configuration for secure dynamic binary file uploads
Change Date: 2026-11-21 01:00 (Asia/Baku)
In collaboration with GPT4 Chat Assistant: Bahram
*/

BEGIN;

ALTER TABLE pulsar.components_config
    ADD COLUMN IF NOT EXISTS accepted_mime_types text[],
    ADD COLUMN IF NOT EXISTS max_file_size_bytes bigint;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_components_config_file_size_positive'
          AND conrelid = 'pulsar.components_config'::regclass
    ) THEN
        ALTER TABLE pulsar.components_config
            ADD CONSTRAINT ck_components_config_file_size_positive
            CHECK (
                max_file_size_bytes IS NULL
                OR max_file_size_bytes > 0
            );
    END IF;
END;
$$;

COMMENT ON COLUMN pulsar.components_config.accepted_mime_types
    IS 'Allowed MIME types or filename extensions for metadata-defined file controls.';

COMMENT ON COLUMN pulsar.components_config.max_file_size_bytes
    IS 'Maximum accepted upload size in bytes for a metadata-defined file control.';

DO $$
DECLARE
    v_updated integer;
BEGIN
    UPDATE pulsar.components_config AS cc
    SET
        control_type = 'file',
        accepted_mime_types = ARRAY['application/pdf', '.pdf']::text[],
        max_file_size_bytes = 26214400,
        visible_in_form = true,
        is_readonly = CASE
            WHEN cc.field_mode IN ('insert', 'update') THEN false
            ELSE cc.is_readonly
        END
    FROM pulsar.components_base AS cb
    WHERE cb.component_name = cc.component_name
      AND LOWER(cb.schm_name) = 'pulsar'
      AND LOWER(cb.tbl_name) = 'table_1'
      AND cc.field_name = 'guidance_pdf'
      AND cc.field_mode IN ('insert', 'update', 'view');

    GET DIAGNOSTICS v_updated = ROW_COUNT;

    IF v_updated = 0 THEN
        RAISE EXCEPTION
            'No components_config rows found for pulsar.table_1.guidance_pdf in insert/update/view modes. Verify component metadata before retrying.';
    END IF;
END;
$;

UPDATE pulsar.components_config AS cc
SET
    visible_in_grid = false,
    visible_in_search = false
FROM pulsar.components_base AS cb
WHERE cb.component_name = cc.component_name
  AND LOWER(cb.schm_name) = 'pulsar'
  AND LOWER(cb.tbl_name) = 'table_1'
  AND cc.field_name = 'guidance_pdf'
  AND cc.field_mode IN ('list', 'grid', 'search');

COMMIT;

SELECT
    cb.component_name,
    cc.field_mode,
    cc.field_name,
    cc.control_type,
    cc.accepted_mime_types,
    cc.max_file_size_bytes,
    cc.visible_in_form,
    cc.is_readonly
FROM pulsar.components_config AS cc
JOIN pulsar.components_base AS cb
  ON cb.component_name = cc.component_name
WHERE LOWER(cb.schm_name) = 'pulsar'
  AND LOWER(cb.tbl_name) = 'table_1'
  AND cc.field_name = 'guidance_pdf'
ORDER BY cc.field_mode;
