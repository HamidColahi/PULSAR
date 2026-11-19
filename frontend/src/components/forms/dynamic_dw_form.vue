
<!-- ===============================================
File: frontend/src/components/forms/dynamic_dw_form.vue
Description: Metadata-driven dynamic data form with language, calendar, and file support
Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
Modified: 2026-11-16 Asia/Baku
=============================================== -->

<template>
  <div
    :dir="isRtl ? 'rtl' : 'ltr'"
    class="pulsar-surface mx-auto w-full max-w-5xl p-4 sm:p-5"
  >
    <div class="mb-1 flex items-center justify-between gap-3">
      <div>
        <div class="pulsar-section-title">
          {{ translations.record || 'Record' }}
          {{ translations[mode] || mode }}
        </div>
      </div>

      <span class="pulsar-status">
        {{ fieldOrder.length }}
        {{
          fieldOrder.length === 1
            ? (translations.field || 'field')
            : (translations.fields || 'fields')
        }}
      </span>
    </div>

    <dw_form_toolbar
      :mode="mode"
      :isSaving="loading"
      @save="onSave"
      @delete="onDeleteClick"
      @cancel="onCancel"
    />

    <div
      v-if="showStateControl"
      class="mb-4 flex justify-end"
    >
      <button
        type="button"
        class="state-control"
        :title="
          translations.change_record_state ||
          'Change Record State'
        "
      >
        <span class="state-icon">⇄</span>

        <span class="state-content">
          <span class="state-label">
            {{ translations.record_state || 'Record State' }}
          </span>

          <span class="state-value">
            {{ form.c_state ?? '—' }}
          </span>
        </span>

        <span class="state-arrow">›</span>
      </button>
    </div>

    <form
      class="grid grid-cols-1 gap-4 md:grid-cols-2"
      @submit.prevent
    >
      <template
        v-for="field in fieldOrder"
        :key="field"
      >
        <div
          v-if="!hiddenFields.includes(field)"
          class="rounded-xl border border-border bg-panel-alt p-3"
          @dblclick.stop="openExpandedField(field)"
        >
          <label
            class="mb-1.5 block text-xs font-semibold text-label"
          >
            {{ translations[field] || field }}

            <span
              v-if="
                fieldMeta[field]?.required === true &&
                ['insert', 'update', 'edit'].includes(
                  String(mode).toLowerCase()
                )
              "
              class="ml-1 inline-block text-red-500"
              :aria-label="
                translations.required_field || 'Required field'
              "
              :title="
                translations.required_field || 'Required field'
              "
            >*</span>
          </label>

          <input
            v-if="fieldTypes[field] === 'date'"
            v-model="form[field]"
            :type="getDateInputType()"
            :placeholder="getDatePlaceholder()"
            :readonly="isFieldReadonly(field)"
            :dir="dateInputDirection"
            class="input"
          />

          <input
            v-else-if="fieldTypes[field] === 'url'"
            v-model="form[field]"
            type="url"
            :readonly="isFieldReadonly(field)"
            class="input"
          />

          <select
            v-else-if="
              ['ddlistbox', 'ddlb'].includes(fieldTypes[field])
            "
            v-model="form[field]"
            :disabled="isFieldReadonly(field)"
            class="input"
          >
            <option value=""></option>

            <option
              v-for="opt in getDomainOptions(field)"
              :key="String(opt.value)"
              :value="opt.value"
            >
              {{ opt.label }}
            </option>
          </select>

          <input
            v-else-if="fieldTypes[field] === 'checkbox'"
            v-model="form[field]"
            type="checkbox"
            :disabled="isFieldReadonly(field)"
            class="h-4 w-4 accent-indigo-500"
          />

          <textarea
            v-else-if="fieldTypes[field] === 'textarea'"
            v-model="form[field]"
            :readonly="isFieldReadonly(field)"
            class="input"
            rows="3"
          ></textarea>

          <div
            v-else-if="fieldTypes[field] === 'file'"
            class="space-y-2"
          >
            <input
              :key="`${field}-${fileInputVersion}`"
              type="file"
              :accept="getFileAccept(field)"
              :disabled="isFieldReadonly(field)"
              class="input file-input"
              @change="onFileChange(field, $event)"
            />

            <div
              v-if="selectedFiles[field]"
              class="file-status"
            >
              <span class="file-indicator"></span>

              <span class="min-w-0 flex-1 truncate">
                {{ selectedFiles[field].name }}
              </span>

              <span class="file-size">
                {{ formatFileSize(selectedFiles[field].size) }}
              </span>
            </div>

            <div
              v-else-if="isFileAvailable(field)"
              class="file-status"
            >
              <span class="file-indicator existing"></span>

              <span class="min-w-0 flex-1">
                {{ translations.existing_file || 'File available' }}
              </span>

              <span
                v-if="getExistingFileSize(field) > 0"
                class="file-size"
              >
                {{ formatFileSize(getExistingFileSize(field)) }}
              </span>

              <button
                type="button"
                class="file-download"
                @click.stop="requestFileDownload(field)"
              >
                {{ translations.download_file || 'Download' }}
              </button>
            </div>

            <p
              v-if="fileErrors[field]"
              class="text-xs text-red-500"
            >
              {{ fileErrors[field] }}
            </p>
          </div>

          <input
            v-else
            v-model="form[field]"
            type="text"
            :readonly="isFieldReadonly(field)"
            class="input"
          />

          <p
            v-if="validationErrors[field]"
            class="mt-1.5 text-xs text-red-500"
          >
            {{ validationErrors[field] }}
          </p>
        </div>
      </template>
    </form>

    <field_expander
      :open="expandedField.open"
      :model-value="expandedField.value"
      :label="expandedField.label"
      :mode="expandedField.mode"
      @update:open="expandedField.open = $event"
      @update:model-value="onExpandedInput"
      @save="onExpandedSave"
      @close="closeExpandedField"
    />
  </div>
</template>

<script setup>
import {
  ref,
  reactive,
  watch,
  computed
} from 'vue'

import {
  language,
  languageMeta
} from '@/stores/uiStore'

import {
  useTranslation
} from '@/composables/useTranslation'

import {
  useDomainOptionsMap
} from '@/composables/useDomainOptions'

import dw_form_toolbar from '@/components/forms/dw_form_toolbar.vue'
import field_expander from '@/components/field_expander.vue'

// --------------------------------------------------
// Component Properties
// --------------------------------------------------

const props = defineProps({
  config: {
    type: Object,
    required: true
  },
  modelValue: {
    type: Object,
    default: () => ({})
  },
  mode: {
    type: String,
    default: 'view'
  },
  componentName: {
    type: String,
    default: null
  }
})

const emit = defineEmits([
  'save',
  'delete',
  'cancel',
  'download-file'
])

// --------------------------------------------------
// Form State
// --------------------------------------------------

const form = reactive({})
const loading = ref(false)
const validationErrors = reactive({})
const fileErrors = reactive({})
const selectedFiles = reactive({})
const translations = ref({})
const fileInputVersion = ref(0)

const expandedField = reactive({
  open: false,
  field: null,
  value: '',
  label: '',
  mode: 'view'
})

// --------------------------------------------------
// Display Settings
// --------------------------------------------------

const isRtl = computed(
  () => languageMeta.value?.is_rtl === true
)

const calendarCode = computed(
  () => languageMeta.value?.calendar_code || 'gregorian'
)

const dateInputDirection = computed(
  () => isRtl.value ? 'rtl' : 'ltr'
)

function getDateInputType() {
  return calendarCode.value === 'gregorian'
    ? 'date'
    : 'text'
}

function getDatePlaceholder() {
  return languageMeta.value?.date_format || 'YYYY-MM-DD'
}

// --------------------------------------------------
// Component Configuration
// --------------------------------------------------

const fieldOrder = computed(
  () => props.config?.field_order || []
)

const fieldMeta = computed(
  () => props.config?.fields || {}
)

const fieldTypes = computed(() => {
  const result = {}

  Object.entries(
    fieldMeta.value
  ).forEach(
    ([field, meta]) => {
      result[field] = String(
        meta?.control_type ||
        meta?.type ||
        'text'
      ).trim().toLowerCase()
    }
  )

  return result
})

const hiddenFields = computed(
  () => Object.entries(fieldMeta.value)
    .filter(
      ([, meta]) => meta?.visible_in_form === false
    )
    .map(
      ([field]) => field
    )
)

const readonlyFields = computed(
  () => Object.entries(fieldMeta.value)
    .filter(
      ([, meta]) => meta?.is_readonly === true
    )
    .map(
      ([field]) => field
    )
)

const showStateControl = computed(
  () =>
    props.mode === 'update' &&
    fieldMeta.value?.c_state !== undefined
)

const validationRules = computed(
  () => fieldMeta.value
)

// --------------------------------------------------
// Domain Identity Helpers
// --------------------------------------------------

function firstDefined(...values) {
  for (const value of values) {
    if (
      value !== undefined &&
      value !== null &&
      value !== ''
    ) {
      return value
    }
  }

  return undefined
}

function isObject(value) {
  return (
    value !== null &&
    typeof value === 'object' &&
    !Array.isArray(value)
  )
}

function isDdlbField(meta) {
  const controlType = String(
    meta?.control_type ||
    meta?.type ||
    ''
  ).trim().toLowerCase()

  return (
    ['ddlistbox', 'ddlb'].includes(controlType) ||
    meta?.is_ddlistbox === true
  )
}

// --------------------------------------------------
// Domain Configuration
//
// Each DDLB field receives its own complete domain
// identity: schema_name, table_name, and field_name.
// --------------------------------------------------

const domainConfigs = computed(() => {
  const result = {}

  const componentConfig = props.config || {}

  const componentDomain = isObject(
    componentConfig.domain_identity
  )
    ? componentConfig.domain_identity
    : isObject(componentConfig.domain_config)
      ? componentConfig.domain_config
      : {}

  const componentSchema = firstDefined(
    componentDomain.schema_name,
    componentDomain.schemaName,
    componentDomain.schm_name,
    componentConfig.schema_name,
    componentConfig.schemaName,
    componentConfig.schm_name
  )

  const componentTable = firstDefined(
    componentDomain.table_name,
    componentDomain.tableName,
    componentDomain.tbl_name,
    componentConfig.table_name,
    componentConfig.tableName,
    componentConfig.tbl_name
  )

  for (const field of fieldOrder.value) {
    const meta = fieldMeta.value[field] || {}

    if (!isDdlbField(meta)) {
      continue
    }

    const fieldDomain = isObject(meta.domain)
      ? meta.domain
      : isObject(meta.domain_config)
        ? meta.domain_config
        : isObject(meta.field_domain_config)
          ? meta.field_domain_config
          : {}

    const schemaName = firstDefined(
      fieldDomain.schema_name,
      fieldDomain.schemaName,
      fieldDomain.schm_name,
      meta.schema_name,
      meta.schemaName,
      meta.schm_name,
      componentSchema
    )

    const tableName = firstDefined(
      fieldDomain.table_name,
      fieldDomain.tableName,
      fieldDomain.tbl_name,
      meta.table_name,
      meta.tableName,
      meta.tbl_name,
      componentTable
    )

    const fieldName = firstDefined(
      fieldDomain.field_name,
      fieldDomain.fieldName,
      meta.domain_field_name,
      meta.domainFieldName,
      typeof meta.domain === 'string'
        ? meta.domain
        : undefined,
      field
    )

    result[field] = {
      schema_name: schemaName,
      table_name: tableName,
      field_name: fieldName
    }
  }

  return result
})

// --------------------------------------------------
// Domain Options
//
// One composable instance manages all DDLB fields.
// --------------------------------------------------

const domainOptionsMap = useDomainOptionsMap(
  domainConfigs
)

function getDomainOptions(field) {
  return domainOptionsMap.value?.[field] || []
}

// --------------------------------------------------
// File Helpers
// --------------------------------------------------

function getFileAccept(field) {
  const meta = fieldMeta.value[field] || {}

  const acceptedTypes = firstDefined(
    meta.accepted_mime_types,
    meta.accept,
    meta.file_accept
  )

  if (Array.isArray(acceptedTypes)) {
    return acceptedTypes.join(',')
  }

  return acceptedTypes || undefined
}

function getMaxFileSize(field) {
  const value = Number(
    fieldMeta.value[field]?.max_file_size_bytes
  )

  return Number.isFinite(value) && value > 0
    ? value
    : null
}


function isFileAvailable(field) {
  const fileMetadata = form.__file_fields?.[field]

  if (typeof fileMetadata === 'boolean') {
    return fileMetadata
  }

  return fileMetadata?.available === true
}

function getExistingFileSize(field) {
  const fileMetadata = form.__file_fields?.[field]

  if (
    fileMetadata &&
    typeof fileMetadata === 'object'
  ) {
    return Number(fileMetadata.file_size_bytes) || 0
  }

  return 0
}


function formatFileSize(size) {
  if (!Number.isFinite(size) || size < 0) {
    return ''
  }

  if (size < 1024) {
    return `${size} B`
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function onFileChange(field, event) {
  delete fileErrors[field]

  const file = event.target.files?.[0] || null

  if (!file) {
    delete selectedFiles[field]
    return
  }

  const maxFileSize = getMaxFileSize(field)

  if (
    maxFileSize !== null &&
    file.size > maxFileSize
  ) {
    fileErrors[field] =
      translations.value.file_too_large ||
      'The selected file exceeds the allowed size.'

    delete selectedFiles[field]
    event.target.value = ''
    return
  }

  const acceptedTypes = getFileAccept(field)

  if (
    acceptedTypes &&
    !isAcceptedFileType(file, acceptedTypes)
  ) {
    fileErrors[field] =
      translations.value.invalid_file_type ||
      'The selected file type is not allowed.'

    delete selectedFiles[field]
    event.target.value = ''
    return
  }

  selectedFiles[field] = file
}

function isAcceptedFileType(file, acceptedTypes) {
  const accepted = acceptedTypes
    .split(',')
    .map(
      item => item.trim().toLowerCase()
    )
    .filter(Boolean)

  if (!accepted.length) {
    return true
  }

  const fileName = file.name.toLowerCase()
  const mimeType = file.type.toLowerCase()

  return accepted.some(type => {
    if (type.startsWith('.')) {
      return fileName.endsWith(type)
    }

    if (type.endsWith('/*')) {
      return mimeType.startsWith(
        type.slice(0, -1)
      )
    }

    return mimeType === type
  })
}

function requestFileDownload(field) {
  if (!isFileAvailable(field)) {
    return
  }

  emit(
    'download-file',
    field
  )
}

function clearSelectedFiles() {
  Object.keys(selectedFiles).forEach(
    key => delete selectedFiles[key]
  )

  Object.keys(fileErrors).forEach(
    key => delete fileErrors[key]
  )

  fileInputVersion.value++
}

// --------------------------------------------------
// Form Synchronization
// --------------------------------------------------

function syncForm() {
  Object.keys(form).forEach(
    key => delete form[key]
  )

  Object.assign(
    form,
    props.modelValue || {}
  )

  clearSelectedFiles()
}

function applyDefaultValues() {
  const defaults = props.config?.default_values || {}

  Object.entries(defaults).forEach(
    ([key, value]) => {
      if (
        form[key] === undefined ||
        form[key] === null ||
        form[key] === ''
      ) {
        form[key] = value === 'today'
          ? new Date().toISOString().split('T')[0]
          : value
      }
    }
  )
}

// --------------------------------------------------
// Field Access Rules
// --------------------------------------------------

function getFieldMode(field) {
  const meta = fieldMeta.value[field] || {}

  return String(
    meta.mod ||
    props.mode ||
    'view'
  ).toLowerCase()
}

function isFieldReadonly(field) {
  if (readonlyFields.value.includes(field)) {
    return true
  }

  return ![
    'insert',
    'update',
    'edit'
  ].includes(
    getFieldMode(field)
  )
}

// --------------------------------------------------
// Expanded Field
// --------------------------------------------------

function normalizeExpandedValue(field, value) {
  const originalValue = form[field]

  if (
    fieldTypes.value[field] === 'checkbox' ||
    typeof originalValue === 'boolean'
  ) {
    if (
      value === true ||
      value === false
    ) {
      return value
    }

    const normalized = String(value)
      .trim()
      .toLowerCase()

    return [
      'true',
      '1',
      'yes',
      'on'
    ].includes(normalized)
  }

  if (typeof originalValue === 'number') {
    const numericValue = Number(value)

    return Number.isNaN(numericValue)
      ? originalValue
      : numericValue
  }

  return value == null
    ? ''
    : String(value)
}

function getExpandedValue(field) {
  const value = form[field]

  if (
    fieldTypes.value[field] === 'checkbox' ||
    typeof value === 'boolean'
  ) {
    return value ? 'true' : 'false'
  }

  if (
    value === null ||
    value === undefined
  ) {
    return ''
  }

  if (typeof value === 'object') {
    return JSON.stringify(
      value,
      null,
      2
    )
  }

  return String(value)
}

function openExpandedField(field) {
  if (
    !fieldOrder.value.includes(field) ||
    fieldTypes.value[field] === 'file'
  ) {
    return
  }

  expandedField.field = field
  expandedField.value = getExpandedValue(field)
  expandedField.label = translations.value[field] || field
  expandedField.mode = isFieldReadonly(field)
    ? 'view'
    : 'edit'

  expandedField.open = true
}

function onExpandedInput(value) {
  expandedField.value = value
}

function onExpandedSave(value) {
  if (
    !expandedField.field ||
    isFieldReadonly(expandedField.field)
  ) {
    closeExpandedField()
    return
  }

  form[expandedField.field] = normalizeExpandedValue(
    expandedField.field,
    value
  )

  closeExpandedField()
}

function closeExpandedField() {
  expandedField.open = false
  expandedField.field = null
  expandedField.value = ''
  expandedField.label = ''
  expandedField.mode = 'view'
}

// --------------------------------------------------
// Translation
// --------------------------------------------------

const {
  translate
} = useTranslation()

async function loadTranslations() {
  if (!props.config) {
    return
  }

  const result = {}

  for (const key of fieldOrder.value) {
    result[key] = await translate(
      key,
      language.value,
      props.config.field_labels_context || 'DefaultForm'
    )
  }

  const uiKeys = [
    'record',
    'field',
    'fields',
    'record_state',
    'change_record_state',
    'view',
    'insert',
    'update',
    'delete',
    'required_field',
    'invalid_url_format',
    'max_length',
    'existing_file',
    'download_file',
    'file_too_large',
    'invalid_file_type',
    'no_file_selected'
  ]

  for (const key of uiKeys) {
    result[key] = await translate(
      key,
      language.value,
      'DefaultForm'
    )
  }

  translations.value = result
}

// --------------------------------------------------
// Form Validation
// --------------------------------------------------

function validateForm() {
  Object.keys(validationErrors).forEach(
    key => delete validationErrors[key]
  )

  let valid = true

  for (const field in validationRules.value) {
    const rules = validationRules.value[field] || {}

    if (rules.required !== true) {
      continue
    }

    if (
      fieldTypes.value[field] === 'file'
    ) {
      const hasNewFile = Boolean(
        selectedFiles[field]
      )

      const hasExistingFile = (
        isFileAvailable(field)
      )

      if (
        !hasNewFile &&
        !hasExistingFile
      ) {
        validationErrors[field] =
          translations.value.required_field ||
          'Required field'

        valid = false
      }

      continue
    }

    const value = form[field]

    if (
      value === null ||
      value === undefined ||
      value === ''
    ) {
      validationErrors[field] =
        translations.value.required_field ||
        'Required field'

      valid = false
    }
  }

  return valid
}

// --------------------------------------------------
// FormData Construction
// --------------------------------------------------

function appendFormValue(
  formData,
  key,
  value
) {
  if (
    value === undefined ||
    value === null
  ) {
    return
  }

  if (value instanceof File) {
    formData.append(
      key,
      value,
      value.name
    )
    return
  }

  if (typeof value === 'boolean') {
    formData.append(
      key,
      String(value)
    )
    return
  }

  if (
    typeof value === 'object'
  ) {
    formData.append(
      key,
      JSON.stringify(value)
    )
    return
  }

  formData.append(
    key,
    String(value)
  )
}

function buildFormData() {
  const formData = new FormData()

  for (const field of fieldOrder.value) {
    if (
      fieldTypes.value[field] === 'file'
    ) {
      const file = selectedFiles[field]

      if (file) {
        formData.append(
          field,
          file,
          file.name
        )
      }

      continue
    }

    appendFormValue(
      formData,
      field,
      form[field]
    )
  }

  return formData
}

// --------------------------------------------------
// Form Actions
// --------------------------------------------------

async function onSave() {
  if (loading.value) {
    return
  }

  if (!validateForm()) {
    return
  }

  loading.value = true

  try {
    const payload = buildFormData()

    emit(
      'save',
      payload
    )
  } finally {
    loading.value = false
  }
}

function onDeleteClick() {
  emit('delete')
}

function onCancel() {
  clearSelectedFiles()
  emit('cancel')
}

// --------------------------------------------------
// Watchers
// --------------------------------------------------

watch(
  () => props.modelValue,
  () => {
    syncForm()
    applyDefaultValues()
  },
  {
    immediate: true,
    deep: true
  }
)

watch(
  [
    fieldOrder,
    () => props.config?.field_labels_context
  ],
  loadTranslations,
  {
    immediate: true,
    deep: true
  }
)

watch(
  language,
  loadTranslations
)

// --------------------------------------------------
// Important Learning Points
// --------------------------------------------------
//
// 1. Form fields are generated from component metadata.
// 2. Domain identity consists of schema, table, and field.
// 3. Each DDLB field receives an independent domain identity.
// 4. Domain options are loaded through useDomainOptionsMap.
// 5. Domain values are never hard-coded in the form.
// 6. Domain labels are supplied by the backend.
// 7. Language changes reload all domain options.
// 8. Metadata changes update the domain configuration map.
// 9. Readonly behavior belongs to field metadata.
// 10. Form validation is driven by field metadata.
// 11. File controls are activated through control_type=file.
// 12. Binary file values are kept outside the regular form state.
// 13. File uploads are submitted through FormData.
// 14. Existing file availability is read from __file_fields.
// 15. File download requests are delegated to the parent component.
// 16. Primary-key semantics belong to component_key.py.
// 17. Where-clause semantics belong to component_where.py.
</script>
 
<style scoped>
.input {
  width: 100%;
  padding: 0.6rem 0.8rem;
  border-radius: 0.6rem;
  background-color: var(--color-input);
  border: 1px solid var(--color-border);
  min-height: 38px;
  transition:
    border-color .16s ease,
    box-shadow .16s ease,
    background-color .16s ease;
  color: var(--color-input-text);
}

.input:focus {
  border-color: #827de0;
  box-shadow:
    0 0 0 2px
    rgba(136,134,174,.4);
  outline: none;
}

.file-input {
  padding: 0.4rem;
  cursor: pointer;
}

.file-input:disabled {
  cursor: not-allowed;
  opacity: .6;
}

.file-status {
  display: flex;
  align-items: center;
  gap: .5rem;
  min-width: 0;
  padding: .5rem .65rem;
  border: 1px solid var(--color-border);
  border-radius: .6rem;
  background-color: var(--color-input);
  color: var(--color-input-text);
  font-size: .75rem;
}

.file-indicator {
  width: .5rem;
  height: .5rem;
  flex-shrink: 0;
  border-radius: 50%;
  background-color: #827de0;
}

.file-indicator.existing {
  background-color: #16a34a;
}

.file-size {
  flex-shrink: 0;
  opacity: .65;
}

.file-download {
  flex-shrink: 0;
  color: var(--color-input-text);
  text-decoration: underline;
  cursor: pointer;
}

.state-control {
  display: inline-flex;
  align-items: center;
  gap: .65rem;
  min-width: 190px;
  padding: .45rem .7rem;
  border: 1px solid var(--color-border);
  border-radius: .75rem;
  background-color: var(--color-input);
  color: var(--color-input-text);
  cursor: pointer;
}

.state-content {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.state-label {
  font-size: .72rem;
  opacity: .65;
}

.state-value {
  font-size: .88rem;
  font-weight: 700;
}
</style>
