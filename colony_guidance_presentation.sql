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
              "translation_prefix": "pulsar.colony.guidance",
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
        )
WHERE schema_name = 'pulsar'
  AND function_name = 'fn_colony_guidance'
  AND config_code = 'COLONY_GUIDANCE_JSON'
  AND is_active = TRUE;

INSERT INTO pulsar.translation_dictionary (
    item_code,
    language_code,
    translated_text
)
SELECT
    source.item_code,
    source.language_code,
    source.translated_text
FROM (
    VALUES
        ('pulsar.colony.guidance.header', 'en', 'Colony Item Guidance'),
        ('pulsar.colony.guidance.header', 'fa', 'راهنمای آیتم Colony'),
        ('pulsar.colony.guidance.additional_data', 'en', 'Additional Data'),
        ('pulsar.colony.guidance.additional_data', 'fa', 'اطلاعات تکمیلی'),
        ('pulsar.colony.guidance.badge.status', 'en', 'Execution'),
        ('pulsar.colony.guidance.badge.status', 'fa', 'اجرا'),
        ('pulsar.colony.guidance.badge.mode', 'en', 'Mode'),
        ('pulsar.colony.guidance.badge.mode', 'fa', 'حالت'),
        ('pulsar.colony.guidance.badge.mapping_status', 'en', 'Mapping'),
        ('pulsar.colony.guidance.badge.mapping_status', 'fa', 'تطبیق'),
        ('pulsar.colony.guidance.section.overview', 'en', 'Guidance Overview'),
        ('pulsar.colony.guidance.section.overview', 'fa', 'نمای کلی راهنمایی'),
        ('pulsar.colony.guidance.section.project', 'en', 'Project Information'),
        ('pulsar.colony.guidance.section.project', 'fa', 'اطلاعات پروژه'),
        ('pulsar.colony.guidance.section.selected_item', 'en', 'Selected Product Backlog Item'),
        ('pulsar.colony.guidance.section.selected_item', 'fa', 'آیتم انتخاب‌شده از Product Backlog'),
        ('pulsar.colony.guidance.section.guidance', 'en', 'Methodology Assessment'),
        ('pulsar.colony.guidance.section.guidance', 'fa', 'ارزیابی روش‌شناسی'),
        ('pulsar.colony.guidance.section.matched_rule', 'en', 'Matched Methodology Rule'),
        ('pulsar.colony.guidance.section.matched_rule', 'fa', 'قاعده منطبق روش‌شناسی'),
        ('pulsar.colony.guidance.section.next_rule', 'en', 'Next Recommended Methodology Step'),
        ('pulsar.colony.guidance.section.next_rule', 'fa', 'گام بعدی پیشنهادی روش‌شناسی'),
        ('pulsar.colony.guidance.section.backlog_summary', 'en', 'Backlog Summary'),
        ('pulsar.colony.guidance.section.backlog_summary', 'fa', 'خلاصه Backlog'),
        ('pulsar.colony.guidance.section.recommended_actions', 'en', 'Recommended Actions'),
        ('pulsar.colony.guidance.section.recommended_actions', 'fa', 'اقدامات پیشنهادی'),
        ('pulsar.colony.guidance.section.warnings', 'en', 'Warnings'),
        ('pulsar.colony.guidance.section.warnings', 'fa', 'هشدارها'),
        ('pulsar.colony.guidance.section.methodology_reference', 'en', 'Methodology Reference'),
        ('pulsar.colony.guidance.section.methodology_reference', 'fa', 'مرجع روش‌شناسی'),
        ('pulsar.colony.guidance.field.title', 'en', 'Guidance Title'),
        ('pulsar.colony.guidance.field.title', 'fa', 'عنوان راهنمایی'),
        ('pulsar.colony.guidance.field.mutation_performed', 'en', 'Mutation Performed'),
        ('pulsar.colony.guidance.field.mutation_performed', 'fa', 'تغییر در داده‌ها انجام شد'),
        ('pulsar.colony.guidance.field.c_project_name', 'en', 'Project'),
        ('pulsar.colony.guidance.field.c_project_name', 'fa', 'پروژه'),
        ('pulsar.colony.guidance.field.c_project_code', 'en', 'Project Code'),
        ('pulsar.colony.guidance.field.c_project_code', 'fa', 'کد پروژه'),
        ('pulsar.colony.guidance.field.c_project_id', 'en', 'Project ID'),
        ('pulsar.colony.guidance.field.c_project_id', 'fa', 'شناسه پروژه'),
        ('pulsar.colony.guidance.field.c_project_status', 'en', 'Project Status'),
        ('pulsar.colony.guidance.field.c_project_status', 'fa', 'وضعیت پروژه'),
        ('pulsar.colony.guidance.field.c_pb_code', 'en', 'PB Code'),
        ('pulsar.colony.guidance.field.c_pb_code', 'fa', 'کد PB'),
        ('pulsar.colony.guidance.field.c_pb_title', 'en', 'Title'),
        ('pulsar.colony.guidance.field.c_pb_title', 'fa', 'عنوان'),
        ('pulsar.colony.guidance.field.c_pb_type', 'en', 'Type'),
        ('pulsar.colony.guidance.field.c_pb_type', 'fa', 'نوع'),
        ('pulsar.colony.guidance.field.c_pb_status', 'en', 'Status'),
        ('pulsar.colony.guidance.field.c_pb_status', 'fa', 'وضعیت'),
        ('pulsar.colony.guidance.field.c_pb_priority', 'en', 'Priority'),
        ('pulsar.colony.guidance.field.c_pb_priority', 'fa', 'اولویت'),
        ('pulsar.colony.guidance.field.c_pb_owner_id', 'en', 'Owner ID'),
        ('pulsar.colony.guidance.field.c_pb_owner_id', 'fa', 'شناسه مالک'),
        ('pulsar.colony.guidance.field.c_pb_assignee_id', 'en', 'Assignee ID'),
        ('pulsar.colony.guidance.field.c_pb_assignee_id', 'fa', 'شناسه مسئول اجرا'),
        ('pulsar.colony.guidance.field.c_pb_parent_id', 'en', 'Parent Item ID'),
        ('pulsar.colony.guidance.field.c_pb_parent_id', 'fa', 'شناسه آیتم والد'),
        ('pulsar.colony.guidance.field.c_pb_description', 'en', 'Description'),
        ('pulsar.colony.guidance.field.c_pb_description', 'fa', 'شرح'),
        ('pulsar.colony.guidance.field.row_no', 'en', 'Table 1 Row'),
        ('pulsar.colony.guidance.field.row_no', 'fa', 'ردیف Table 1'),
        ('pulsar.colony.guidance.field.event', 'en', 'Event'),
        ('pulsar.colony.guidance.field.event', 'fa', 'رویداد'),
        ('pulsar.colony.guidance.field.backlog', 'en', 'Backlog'),
        ('pulsar.colony.guidance.field.backlog', 'fa', 'Backlog'),
        ('pulsar.colony.guidance.field.inquiry', 'en', 'Inquiry'),
        ('pulsar.colony.guidance.field.inquiry', 'fa', 'موضوع درخواست'),
        ('pulsar.colony.guidance.field.pbi_sbi', 'en', 'Work Product'),
        ('pulsar.colony.guidance.field.pbi_sbi', 'fa', 'محصول کاری'),
        ('pulsar.colony.guidance.field.reaction', 'en', 'Reaction'),
        ('pulsar.colony.guidance.field.reaction', 'fa', 'واکنش'),
        ('pulsar.colony.guidance.field.action', 'en', 'Action'),
        ('pulsar.colony.guidance.field.action', 'fa', 'اقدام'),
        ('pulsar.colony.guidance.field.start_state', 'en', 'Start State'),
        ('pulsar.colony.guidance.field.start_state', 'fa', 'وضعیت آغاز'),
        ('pulsar.colony.guidance.field.final_state', 'en', 'Final State'),
        ('pulsar.colony.guidance.field.final_state', 'fa', 'وضعیت نهایی'),
        ('pulsar.colony.guidance.field.rp', 'en', 'RP'),
        ('pulsar.colony.guidance.field.rp', 'fa', 'RP'),
        ('pulsar.colony.guidance.field.guidance_document.available', 'en', 'Guidance PDF Available'),
        ('pulsar.colony.guidance.field.guidance_document.available', 'fa', 'فایل راهنما موجود است'),
        ('pulsar.colony.guidance.field.guidance_document.mime_type', 'en', 'Guidance PDF Type'),
        ('pulsar.colony.guidance.field.guidance_document.mime_type', 'fa', 'نوع فایل راهنما'),
        ('pulsar.colony.guidance.field.guidance_document.file_size_bytes', 'en', 'Guidance PDF Size (bytes)'),
        ('pulsar.colony.guidance.field.guidance_document.file_size_bytes', 'fa', 'اندازه فایل راهنما (بایت)'),
        ('pulsar.colony.guidance.field.item_count', 'en', 'PB Item Count'),
        ('pulsar.colony.guidance.field.item_count', 'fa', 'تعداد آیتم‌های PB'),
        ('pulsar.colony.guidance.field.primary_usecase_count', 'en', 'Primary Usecase Count'),
        ('pulsar.colony.guidance.field.primary_usecase_count', 'fa', 'تعداد Primary Usecase'),
        ('pulsar.colony.guidance.field.inception_record_exists', 'en', 'Inception Record Exists'),
        ('pulsar.colony.guidance.field.inception_record_exists', 'fa', 'رکورد Inception وجود دارد')
) AS source(item_code, language_code, translated_text)
WHERE NOT EXISTS (
    SELECT 1
    FROM pulsar.translation_dictionary AS existing
    WHERE existing.item_code = source.item_code
      AND existing.language_code = source.language_code
);

DO $
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
    ) AS presentation_section_count
FROM pulsar.t_function_output_config
WHERE schema_name = 'pulsar'
  AND function_name = 'fn_colony_guidance'
  AND config_code = 'COLONY_GUIDANCE_JSON'
  AND is_active = TRUE;
