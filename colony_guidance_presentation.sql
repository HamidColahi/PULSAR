/*
File: PULSAR/colony_guidance_presentation.sql
Description: Metadata-defined Structured Report presentation for Colony guidance
Change Date: 2026-11-22 23:26 (Asia/Baku)
In collaboration with GPT4 Chat Assistant: Bahram
*/

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pulsar.t_function_output_config
        WHERE schema_name = 'pulsar'
          AND function_name = 'fn_colony_guidance'
          AND config_code = 'COLONY_GUIDANCE_JSON'
          AND is_active = TRUE
    ) THEN
        RAISE EXCEPTION
            'Active output configuration COLONY_GUIDANCE_JSON was not found for pulsar.fn_colony_guidance.';
    END IF;
END;
$$;

UPDATE pulsar.t_function_output_config
SET
    renderer_key = 'structured-report',
    presentation_code = 'COLONY_GUIDANCE_REPORT',
    display_options = COALESCE(display_options, '{}'::jsonb)
        || jsonb_build_object(
            'display_type',
            'structured_report',
            'title',
            'Colony Item Guidance',
            'presentation_definition',
            $presentation$
            {
              "version": 1,
              "title": "Colony Item Guidance",
              "show_unmapped": false,
              "header": {
                "title": "Colony Item Guidance",
                "badges": [
                  {"path": "status", "label": "Execution"},
                  {"path": "mode", "label": "Mode"},
                  {"path": "mapping_status", "label": "Mapping"}
                ]
              },
              "sections": [
                {
                  "key": "overview",
                  "title": "Guidance Overview",
                  "type": "fields",
                  "fields": [
                    {"path": "title", "label": "Guidance Title"},
                    {"path": "mutation_performed", "label": "Mutation Performed", "display": "status"}
                  ]
                },
                {
                  "key": "project",
                  "title": "Project Information",
                  "type": "record",
                  "path": "project",
                  "fields": [
                    {"path": "c_project_name", "label": "Project"},
                    {"path": "c_project_code", "label": "Project Code"},
                    {"path": "c_project_id", "label": "Project ID"},
                    {"path": "c_project_status", "label": "Project Status", "display": "status"}
                  ]
                },
                {
                  "key": "selected_item",
                  "title": "Selected Product Backlog Item",
                  "type": "record",
                  "path": "selected_item",
                  "fields": [
                    {"path": "c_pb_code", "label": "PB Code"},
                    {"path": "c_pb_title", "label": "Title"},
                    {"path": "c_pb_type", "label": "Type"},
                    {"path": "c_pb_status", "label": "Status", "display": "status"},
                    {"path": "c_pb_priority", "label": "Priority"},
                    {"path": "c_pb_owner_id", "label": "Owner ID"},
                    {"path": "c_pb_assignee_id", "label": "Assignee ID"},
                    {"path": "c_pb_parent_id", "label": "Parent Item ID"},
                    {"path": "c_pb_description", "label": "Description"}
                  ]
                },
                {
                  "key": "guidance",
                  "title": "Methodology Assessment",
                  "type": "list",
                  "path": "guidance"
                },
                {
                  "key": "matched_rule",
                  "title": "Matched Methodology Rule",
                  "type": "record",
                  "path": "matched_rule",
                  "fields": [
                    {"path": "row_no", "label": "Table 1 Row"},
                    {"path": "event", "label": "Event"},
                    {"path": "backlog", "label": "Backlog"},
                    {"path": "inquiry", "label": "Inquiry"},
                    {"path": "pbi_sbi", "label": "Work Product"},
                    {"path": "reaction", "label": "Reaction"},
                    {"path": "action", "label": "Action"},
                    {"path": "start_state", "label": "Start State"},
                    {"path": "final_state", "label": "Final State"},
                    {"path": "rp", "label": "RP"},
                    {"path": "guidance_document.available", "label": "Guidance PDF Available", "display": "status"},
                    {"path": "guidance_document.mime_type", "label": "Guidance PDF Type"},
                    {"path": "guidance_document.file_size_bytes", "label": "Guidance PDF Size (bytes)"}
                  ]
                },
                {
                  "key": "next_rule",
                  "title": "Next Recommended Methodology Step",
                  "type": "record",
                  "path": "next_rule",
                  "fields": [
                    {"path": "row_no", "label": "Table 1 Row"},
                    {"path": "event", "label": "Event"},
                    {"path": "backlog", "label": "Backlog"},
                    {"path": "inquiry", "label": "Inquiry"},
                    {"path": "pbi_sbi", "label": "Work Product"},
                    {"path": "reaction", "label": "Reaction"},
                    {"path": "action", "label": "Action"},
                    {"path": "start_state", "label": "Start State"},
                    {"path": "final_state", "label": "Final State"},
                    {"path": "rp", "label": "RP"}
                  ]
                },
                {
                  "key": "backlog_summary",
                  "title": "Backlog Summary",
                  "type": "record",
                  "path": "backlog_summary",
                  "fields": [
                    {"path": "item_count", "label": "PB Item Count"},
                    {"path": "primary_usecase_count", "label": "Primary Usecase Count"},
                    {"path": "inception_record_exists", "label": "Inception Record Exists", "display": "status"}
                  ]
                },
                {
                  "key": "recommended_actions",
                  "title": "Recommended Actions",
                  "type": "actions",
                  "path": "recommended_actions"
                },
                {
                  "key": "warnings",
                  "title": "Warnings",
                  "type": "alerts",
                  "path": "warnings"
                },
                {
                  "key": "methodology_reference",
                  "title": "Methodology Reference",
                  "type": "table",
                  "path": "methodology_reference",
                  "columns": [
                    {"path": "row_no", "label": "Row"},
                    {"path": "event", "label": "Event"},
                    {"path": "backlog", "label": "Backlog"},
                    {"path": "inquiry", "label": "Inquiry"},
                    {"path": "pbi_sbi", "label": "Work Product"},
                    {"path": "reaction", "label": "Reaction"},
                    {"path": "action", "label": "Action"},
                    {"path": "start_state", "label": "Start State"},
                    {"path": "final_state", "label": "Final State"},
                    {"path": "rp", "label": "RP"}
                  ]
                }
              ]
            }
            $presentation$::jsonb
        ),
    updated_at = CURRENT_TIMESTAMP
WHERE schema_name = 'pulsar'
  AND function_name = 'fn_colony_guidance'
  AND config_code = 'COLONY_GUIDANCE_JSON'
  AND is_active = TRUE;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pulsar.t_function_output_config
        WHERE schema_name = 'pulsar'
          AND function_name = 'fn_colony_guidance'
          AND config_code = 'COLONY_GUIDANCE_JSON'
          AND is_active = TRUE
          AND display_options->>'display_type' = 'structured_report'
          AND display_options ? 'presentation_definition'
    ) THEN
        RAISE EXCEPTION
            'Colony structured report presentation metadata was not saved.';
    END IF;
END;
$$;

COMMIT;

SELECT
    output_config_id,
    config_code,
    output_type_code,
    renderer_key,
    presentation_code,
    display_options->>'display_type' AS display_type,
    jsonb_array_length(
        display_options->'presentation_definition'->'sections'
    ) AS presentation_section_count,
    updated_at
FROM pulsar.t_function_output_config
WHERE schema_name = 'pulsar'
  AND function_name = 'fn_colony_guidance'
  AND config_code = 'COLONY_GUIDANCE_JSON'
  AND is_active = TRUE;
