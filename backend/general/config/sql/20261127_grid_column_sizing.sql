-- ===============================================
-- File: backend/general/config/sql/20261127_grid_column_sizing.sql
-- Description: Add developer-controlled Grid column sizing metadata
-- In collaboration with GPT4 Chat Assistant: Bahram
-- Modified: 2026-11-27 10:20 (Asia/Baku)
-- ===============================================

ALTER TABLE pulsar.components_config
    ADD COLUMN IF NOT EXISTS grid_width_px INTEGER,
    ADD COLUMN IF NOT EXISTS grid_min_width_px INTEGER,
    ADD COLUMN IF NOT EXISTS grid_max_width_px INTEGER;

ALTER TABLE pulsar.components_config
    DROP CONSTRAINT IF EXISTS components_config_grid_width_positive,
    DROP CONSTRAINT IF EXISTS components_config_grid_min_width_positive,
    DROP CONSTRAINT IF EXISTS components_config_grid_max_width_positive,
    DROP CONSTRAINT IF EXISTS components_config_grid_width_bounds;

ALTER TABLE pulsar.components_config
    ADD CONSTRAINT components_config_grid_width_positive
        CHECK (grid_width_px IS NULL OR grid_width_px >= 48),
    ADD CONSTRAINT components_config_grid_min_width_positive
        CHECK (grid_min_width_px IS NULL OR grid_min_width_px >= 48),
    ADD CONSTRAINT components_config_grid_max_width_positive
        CHECK (grid_max_width_px IS NULL OR grid_max_width_px <= 2000),
    ADD CONSTRAINT components_config_grid_width_bounds
        CHECK (
            grid_min_width_px IS NULL
            OR grid_max_width_px IS NULL
            OR grid_min_width_px <= grid_max_width_px
        );
