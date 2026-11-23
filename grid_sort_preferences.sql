-- ===============================================
-- File: grid_sort_preferences.sql
-- Description: Configure forced Grid sorting and persist ordered user sorting
-- Author: MHKolahi@gmail.com
-- In collaboration with GPT4 Chat Assistant: Bahram
-- Last Modified: 2026-11-23 23:55 (Asia/Baku)
-- ===============================================

BEGIN;

ALTER TABLE pulsar.components_config
    ADD COLUMN IF NOT EXISTS field_sort SMALLINT
    NOT NULL DEFAULT 0;

ALTER TABLE pulsar.components_config
    ALTER COLUMN field_sort TYPE SMALLINT
    USING CASE
        WHEN field_sort IS TRUE THEN 1
        ELSE 0
    END;

ALTER TABLE pulsar.components_config
    ALTER COLUMN field_sort SET DEFAULT 0,
    ALTER COLUMN field_sort SET NOT NULL;

ALTER TABLE pulsar.components_config
    ADD COLUMN IF NOT EXISTS field_sort_order INTEGER;

ALTER TABLE pulsar.components_config
    DROP CONSTRAINT IF EXISTS components_config_field_sort_check;

ALTER TABLE pulsar.components_config
    ADD CONSTRAINT components_config_field_sort_check
    CHECK (field_sort IN (0, 1, 2, 3));

ALTER TABLE pulsar.components_config
    DROP CONSTRAINT IF EXISTS components_config_field_sort_order_check;

ALTER TABLE pulsar.components_config
    ADD CONSTRAINT components_config_field_sort_order_check
    CHECK (
        (field_sort IN (0, 1) AND field_sort_order IS NULL)
        OR
        (field_sort IN (2, 3) AND field_sort_order > 0)
    );

COMMENT ON COLUMN pulsar.components_config.field_sort IS
    '0=Disabled, 1=User-controlled, 2=Forced DESC, 3=Forced ASC';

COMMENT ON COLUMN pulsar.components_config.field_sort_order IS
    'Supervisor-defined priority for forced sorting; NULL for disabled and user-controlled fields';

DROP TABLE IF EXISTS pulsar.t_user_grid_sort;

CREATE TABLE pulsar.t_user_grid_sort
(
    c_user_id uuid NOT NULL,
    component_name text NOT NULL,
    field_mode text NOT NULL DEFAULT 'list',
    field_name text NOT NULL,
    direction text NOT NULL,
    field_sort_order integer NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT t_user_grid_sort_pkey
        PRIMARY KEY (c_user_id, component_name, field_mode, field_name),

    CONSTRAINT t_user_grid_sort_user_fkey
        FOREIGN KEY (c_user_id)
        REFERENCES pulsar.t_user (c_user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT t_user_grid_sort_direction_check
        CHECK (direction IN ('asc', 'desc')),

    CONSTRAINT t_user_grid_sort_order_positive
        CHECK (field_sort_order > 0),

    CONSTRAINT t_user_grid_sort_order_unique
        UNIQUE (c_user_id, component_name, field_mode, field_sort_order),

    CONSTRAINT t_user_grid_sort_component_not_empty
        CHECK (length(trim(component_name)) > 0)
);

COMMENT ON TABLE pulsar.t_user_grid_sort IS
    'Per-user ordered multi-column sorting preferences for metadata-driven PULSAR Grids';

COMMENT ON COLUMN pulsar.t_user_grid_sort.field_sort_order IS
    'User-defined priority among user-controlled Grid sort fields';

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

-- Supervisor-controlled configuration examples:
--
-- User-controlled:
-- UPDATE pulsar.components_config
-- SET field_sort = 1, field_sort_order = NULL
-- WHERE component_name = '<grid_component>'
--   AND field_mode = 'list'
--   AND field_name IN ('<field_1>', '<field_2>');
--
-- Forced DESC (priority 1), then forced ASC (priority 2):
-- UPDATE pulsar.components_config
-- SET field_sort = 2, field_sort_order = 1
-- WHERE component_name = '<grid_component>'
--   AND field_mode = 'list'
--   AND field_name = '<descending_field>';
--
-- UPDATE pulsar.components_config
-- SET field_sort = 3, field_sort_order = 2
-- WHERE component_name = '<grid_component>'
--   AND field_mode = 'list'
--   AND field_name = '<ascending_field>';
--
-- Disabled:
-- UPDATE pulsar.components_config
-- SET field_sort = 0, field_sort_order = NULL
-- WHERE component_name = '<grid_component>'
--   AND field_mode = 'list'
--   AND field_name = '<field_name>';
--
-- User sort priorities are stored independently per user and Grid
-- in pulsar.t_user_grid_sort.field_sort_order.
-- ===============================================
