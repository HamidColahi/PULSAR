<!--
File: PULSAR/frontend/src/components/common/structured_report_renderer.vue
Description: Generic metadata-driven renderer for nested structured Function reports
Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
Last Modified: 2026-11-22 23:26 (Asia/Baku)
-->
<template>
  <article class="structured-report" :dir="direction">
    <header v-if="headerTitle || headerBadges.length" class="structured-report-header">
      <h2 v-if="headerTitle">{{ translateLabel('header', headerTitle) }}</h2>
      <div v-if="headerBadges.length" class="structured-report-badges">
        <span
          v-for="badge in headerBadges"
          :key="badge.path"
          class="structured-report-badge"
          :class="badgeClass(badge.value)"
        >
          <strong v-if="badge.label">{{ translateLabel(`badge.${badge.path}`, badge.label) }}:</strong>
          {{ formatValue(badge.value) }}
        </span>
      </div>
    </header>

    <section
      v-for="(section, index) in visibleSections"
      :key="section.id || section.key || index"
      class="structured-report-section"
      :class="`section-${section.type || 'fields'}`"
    >
      <h3 v-if="section.title">{{ translateLabel(`section.${section.key}`, section.title) }}</h3>

      <dl v-if="section.type === 'fields'" class="structured-report-fields">
        <template
          v-for="field in section.fields || []"
          :key="field.path"
        >
          <dt>{{ translateLabel(`field.${field.path}`, field.label || field.path) }}</dt>
          <dd>
            <span
              v-if="field.display === 'status'"
              class="structured-report-badge"
              :class="badgeClass(resolvePath(resolvePath(data, section.path), field.path))"
            >
              {{ formatValue(resolvePath(resolvePath(data, section.path), field.path)) }}
            </span>
            <pre v-else-if="isComplex(resolvePath(resolvePath(data, section.path), field.path))">{{ formatValue(resolvePath(resolvePath(data, section.path), field.path)) }}</pre>
            <span v-else>{{ formatValue(resolvePath(resolvePath(data, section.path), field.path)) }}</span>
          </dd>
        </template>
      </dl>

      <ul
        v-else-if="section.type === 'list' || section.type === 'alerts' || section.type === 'actions'"
        class="structured-report-list"
      >
        <li
          v-for="(item, itemIndex) in asArray(resolvePath(data, section.path))"
          :key="item.id || item.action_code || itemIndex"
          :class="{ 'structured-report-alert': section.type === 'alerts' }"
        >
          <template v-if="typeof item === 'string'">
            {{ item }}
          </template>
          <template v-else-if="section.type === 'actions'">
            <strong>{{ item.label || item.title || item.action_code || 'Action' }}</strong>
            <span v-if="item.work_product"> — {{ item.work_product }}</span>
            <span v-if="item.rule_row_no"> (Table 1, Row {{ item.rule_row_no }})</span>
            <p v-if="item.description">{{ item.description }}</p>
          </template>
          <template v-else>
            <strong v-if="item.title">{{ item.title }}</strong>
            <span>{{ item.message || item.description || item.text || formatValue(item) }}</span>
          </template>
        </li>
      </ul>

      <div v-else-if="section.type === 'table'" class="structured-report-table-wrap">
        <table class="structured-report-table">
          <thead>
            <tr>
              <th v-for="column in section.columns || []" :key="column.path">
                {{ column.label || column.path }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, rowIndex) in asArray(resolvePath(data, section.path))"
              :key="row.id || row.row_no || rowIndex"
            >
              <td v-for="column in section.columns || []" :key="column.path">
                {{ formatValue(resolvePath(row, column.path)) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="section.type === 'record'" class="structured-report-record">
        <dl class="structured-report-fields">
          <template
            v-for="field in section.fields || []"
            :key="field.path"
          >
            <dt>{{ translateLabel(`field.${field.path}`, field.label || field.path) }}</dt>
            <dd>{{ formatValue(resolvePath(resolvePath(data, section.path), field.path)) }}</dd>
          </template>
        </dl>
      </div>

      <p v-else-if="section.type === 'text'" class="structured-report-text">
        {{ formatValue(resolvePath(data, section.path)) }}
      </p>

      <pre v-else class="structured-report-json">{{ formatValue(resolvePath(data, section.path)) }}</pre>
    </section>

    <section v-if="unmappedKeys.length" class="structured-report-section">
      <h3>{{ translateLabel('additional_data', definition.unmapped_title || 'Additional Data') }}</h3>
      <dl class="structured-report-fields">
        <template v-for="key in unmappedKeys" :key="key">
          <dt>{{ key }}</dt>
          <dd><pre>{{ formatValue(data[key]) }}</pre></dd>
        </template>
      </dl>
    </section>
  </article>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useTranslation } from '@/composables/useTranslation'

const { translate, currentLanguage } = useTranslation()
const translations = ref({})

const props = defineProps({
  data: {
    type: [Object, Array, String, Number, Boolean],
    default: null
  },
  definition: {
    type: Object,
    default: () => ({})
  },
  direction: {
    type: String,
    default: 'ltr'
  }
})

const headerTitle = computed(() => props.definition.header?.title || props.definition.title || '')

const translationKeys = computed(() => {
  const prefix = props.definition.translation_prefix
  if (!prefix) return ['pulsar.common.yes', 'pulsar.common.no', 'pulsar.function_result.null_value']

  const keys = [
    'pulsar.common.yes',
    'pulsar.common.no',
    'pulsar.function_result.null_value',
    `${prefix}.header`,
    `${prefix}.additional_data`
  ]

  for (const badge of props.definition.header?.badges || []) {
    keys.push(`${prefix}.badge.${badge.path}`)
  }

  for (const section of props.definition.sections || []) {
    if (section.key) keys.push(`${prefix}.section.${section.key}`)
    for (const field of section.fields || []) {
      if (field.path) keys.push(`${prefix}.field.${field.path}`)
    }
    for (const column of section.columns || []) {
      if (column.path) keys.push(`${prefix}.field.${column.path}`)
    }
  }

  return [...new Set(keys)]
})

async function loadTranslations() {
  const languageCode = currentLanguage.value
  const keys = translationKeys.value
  const loaded = {}

  await Promise.all(keys.map(async key => {
    loaded[key] = await translate(key, languageCode)
  }))

  if (languageCode === currentLanguage.value) {
    translations.value = loaded
  }
}

watch([translationKeys, currentLanguage], loadTranslations, {
  deep: true,
  immediate: true
})

function translateLabel(suffix, fallback) {
  const prefix = props.definition.translation_prefix
  if (!prefix) return fallback
  const key = `${prefix}.${suffix}`
  const value = translations.value[key]
  return value && value !== key ? value : fallback
}
const headerBadges = computed(() => {
  const configured = props.definition.header?.badges
  if (!Array.isArray(configured)) return []
  return configured.map(item => ({
    ...item,
    value: resolvePath(props.data, item.path)
  })).filter(item => item.value !== null && item.value !== undefined && item.value !== '')
})

const visibleSections = computed(() => (
  Array.isArray(props.definition.sections)
    ? props.definition.sections.filter(section => (
        section && typeof section === 'object' &&
        (section.visible !== false) &&
        hasValue(resolvePath(props.data, section.path), section)
      ))
    : []
))

const unmappedKeys = computed(() => {
  if (!props.definition.show_unmapped || !props.data || typeof props.data !== 'object' || Array.isArray(props.data)) {
    return []
  }
  const mapped = new Set((props.definition.sections || []).map(section => section.path).filter(Boolean))
  return Object.keys(props.data).filter(key => !mapped.has(key))
})

function resolvePath(source, path) {
  if (!path) return source
  return String(path).split('.').reduce((value, key) => {
    if (value === null || value === undefined) return undefined
    return value[key]
  }, source)
}

function hasValue(value, section) {
  if (section.type === 'fields' || section.type === 'record') {
    return Array.isArray(section.fields) && section.fields.length > 0
  }
  if (section.type === 'table' || section.type === 'list' || section.type === 'alerts' || section.type === 'actions') {
    return Array.isArray(value) && value.length > 0
  }
  return value !== null && value !== undefined && value !== ''
}

function asArray(value) {
  return Array.isArray(value) ? value : []
}

function isComplex(value) {
  return value !== null && typeof value === 'object'
}

function formatValue(value) {
  if (value === null || value === undefined || value === '') {
    const key = 'pulsar.function_result.null_value'
    return translations.value[key] && translations.value[key] !== key
      ? translations.value[key]
      : '—'
  }
  if (typeof value === 'boolean') {
    const key = value ? 'pulsar.common.yes' : 'pulsar.common.no'
    return translations.value[key] && translations.value[key] !== key
      ? translations.value[key]
      : (value ? 'Yes' : 'No')
  }
  if (isComplex(value)) return JSON.stringify(value, null, 2)
  return String(value)
}

function badgeClass(value) {
  const normalized = String(value ?? '').trim().toUpperCase()
  if (['SUCCESS', 'READY', 'MATCHED', 'COMPLETED', 'APPROVED'].includes(normalized)) return 'badge-success'
  if (['WARNING', 'PENDING', 'DRAFT', 'CONTINUE'].includes(normalized)) return 'badge-warning'
  if (['ERROR', 'FAILED', 'CONFLICT', 'STOPPED'].includes(normalized)) return 'badge-danger'
  return 'badge-neutral'
}
</script>

<style scoped>
.structured-report {
  display: grid;
  gap: 1rem;
  min-width: 0;
  color: var(--text-primary, #1f2937);
}
.structured-report-header,
.structured-report-section {
  min-width: 0;
  padding: 1rem 1.125rem;
  border: 1px solid var(--border-color, #dbe1ea);
  border-radius: 0.75rem;
  background: var(--surface-primary, #fff);
}
.structured-report-header {
  display: grid;
  gap: 0.75rem;
}
.structured-report-header h2,
.structured-report-section h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
}
.structured-report-section h3 {
  margin-bottom: 0.875rem;
}
.structured-report-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.structured-report-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  width: fit-content;
  padding: 0.25rem 0.625rem;
  border: 1px solid var(--border-color, #d1d5db);
  border-radius: 999px;
  background: var(--surface-secondary, #f9fafb);
  font-size: 0.75rem;
  font-weight: 600;
}
.badge-success {
  border-color: #86efac;
  background: #f0fdf4;
  color: #166534;
}
.badge-warning {
  border-color: #fcd34d;
  background: #fffbeb;
  color: #92400e;
}
.badge-danger {
  border-color: #fca5a5;
  background: #fef2f2;
  color: #991b1b;
}
.badge-neutral {
  color: var(--text-secondary, #6b7280);
}
.structured-report-fields {
  display: grid;
  grid-template-columns: minmax(8rem, 0.35fr) minmax(0, 1fr);
  gap: 0.625rem 1rem;
  margin: 0;
}
.structured-report-fields dt {
  color: var(--text-secondary, #6b7280);
  font-size: 0.8125rem;
  font-weight: 600;
}
.structured-report-fields dd {
  min-width: 0;
  margin: 0;
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}
.structured-report-fields pre,
.structured-report-json {
  max-width: 100%;
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.8125rem;
}
.structured-report-list {
  display: grid;
  gap: 0.625rem;
  margin: 0;
  padding-inline-start: 1.25rem;
}
.structured-report-list li {
  padding-inline-start: 0.25rem;
  line-height: 1.6;
  overflow-wrap: anywhere;
}
.structured-report-alert {
  color: var(--error-text, #b91c1c);
}
.structured-report-list p {
  margin-top: 0.25rem;
  color: var(--text-secondary, #6b7280);
}
.structured-report-table-wrap {
  width: 100%;
  overflow-x: auto;
}
.structured-report-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}
.structured-report-table th,
.structured-report-table td {
  padding: 0.625rem 0.75rem;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  text-align: start;
  vertical-align: top;
  overflow-wrap: anywhere;
}
.structured-report-table th {
  background: var(--surface-secondary, #f3f4f6);
  font-weight: 700;
}
.structured-report-text {
  margin: 0;
  line-height: 1.7;
  white-space: pre-wrap;
}
@media (max-width: 640px) {
  .structured-report-fields {
    grid-template-columns: minmax(0, 1fr);
    gap: 0.25rem;
  }
  .structured-report-fields dd {
    margin-bottom: 0.5rem;
  }
}
</style>
