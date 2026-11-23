-- ===============================================
-- File: grid_sort_preferences.sql
-- Description: Enable metadata-controlled Grid sorting and persist user preferences
-- Author: MHKolahi@gmail.com
-- In collaboration with GPT4 Chat Assistant: Bahram
-- Last Modified: 2026-11-23 23:25 (Asia/Baku)
-- ===============================================

BEGIN;

ALTER TABLE pulsar.components_config
    ADD COLUMN IF NOT EXISTS field_sort boolean
    NOT NULL DEFAULT false;

COMMENT ON COLUMN pulsar.components_config.field_sort IS
    'Supervisor-controlled permission to expose this field in Grid sorting';

CREATE TABLE IF NOT EXISTS pulsar.t_user_grid_sort
(
    c_user_id uuid NOT NULL,
    component_name text NOT NULL,
    field_mode text NOT NULL DEFAULT 'list',
    sort_spec jsonb NOT NULL DEFAULT '[]'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT t_user_grid_sort_pkey
        PRIMARY KEY (c_user_id, component_name, field_mode),

    CONSTRAINT t_user_grid_sort_user_fkey
        FOREIGN KEY (c_user_id)
        REFERENCES pulsar.t_user (c_user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT t_user_grid_sort_spec_array
        CHECK (jsonb_typeof(sort_spec) = 'array'),

    CONSTRAINT t_user_grid_sort_component_not_empty
        CHECK (length(trim(component_name)) > 0)
);

COMMENT ON TABLE pulsar.t_user_grid_sort IS
    'Per-user ordered multi-column sorting preferences for metadata-driven PULSAR Grids';

COMMENT ON COLUMN pulsar.t_user_grid_sort.sort_spec IS
    'Ordered JSON array of field and direction pairs; earlier entries have higher sort priority';

INSERT INTO pulsar.translation_dictionary
    (item_code, language_code, translated_text)
SELECT source.item_code, source.language_code, source.translated_text
FROM (
    VALUES
        ('pulsar.grid.sortNone', 'en', 'No sorting'),
        ('pulsar.grid.sortNone', 'fa', 'بدون ترتیب'),
        ('pulsar.grid.sortAscending', 'en', 'Sort ascending'),
        ('pulsar.grid.sortAscending', 'fa', 'مرتب‌سازی صعودی'),
        ('pulsar.grid.sortDescending', 'en', 'Sort descending'),
        ('pulsar.grid.sortDescending', 'fa', 'مرتب‌سازی نزولی')
) AS source(item_code, language_code, translated_text)
WHERE NOT EXISTS (
    SELECT 1
    FROM pulsar.translation_dictionary existing
    WHERE existing.item_code = source.item_code
      AND existing.language_code = source.language_code
);

COMMIT;

-- ===============================================
-- Supervisor enables sorting per field:
--
-- UPDATE pulsar.components_config
-- SET field_sort = true
-- WHERE component_name = '<grid_component>'
--   AND field_mode = 'list'
--   AND field_name IN ('<field_1>', '<field_2>');
--
-- Sorting remains disabled by default for every field.
-- ===============================================
