
<!-- ===============================================
File: frontend/src/components/grids/dynamic_dw_search.vue
Description: Metadata-driven dynamic search and filter component
Author: MHKolahi@gmail.com
Last Modified: 2026-11-26 14:02 (Asia/Baku)
In collaboration with GPT4 Chat Assistant: Bahram
=============================================== -->

<template>
  <div
    :dir="isRtl ? 'rtl' : 'ltr'"
    class="pulsar-surface overflow-x-auto p-2.5"
  >
    <div class="mb-2 flex items-center gap-2 px-1">
      <span class="pulsar-section-label">
        {{ translations.search || 'Search' }}
      </span>

      <span class="text-[11px] text-muted">
        {{ fields.length }} fields
      </span>

      <div class="flex-1"></div>

      <button
        type="button"
        @click="clearFilters"
        :title="translations.clear || 'Clear'"
        class="pulsar-action h-8 min-h-8 px-2 text-xs"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          class="h-4 w-4"
        >
          <path
            d="M3 6h18M8 6V4h8v2M10 11v6M14 11v6M5 6l1 15h12l1-15"
          />
        </svg>

        <span class="hidden sm:inline">
          {{ translations.clear || 'Clear' }}
        </span>
      </button>
    </div>

    <div
      class="min-w-max overflow-hidden rounded-lg border border-border"
    >
      <table class="w-full table-auto text-xs">
        <thead class="bg-panel-alt">
          <tr>
            <th
              class="w-16 border-b border-border px-2 py-2 text-center font-semibold text-muted"
            >
              ↕
            </th>

            <th
              v-for="field in fields"
              :key="field"
              class="border-b border-l border-border px-2 py-2 text-center font-semibold text-label"
            >
              {{ translations[field] || field }}
            </th>
          </tr>
        </thead>

        <tbody>
          <tr>
            <td
              class="border-b border-border px-2 py-1.5 text-center font-medium text-muted"
            >
              {{ translations.from || 'From' }}
            </td>

            <td
              v-for="field in fields"
              :key="'from-' + field"
              class="border-b border-l border-border p-1"
            >
              <select
                v-if="isDropdown(field)"
                v-model="fromValues[field]"
                class="pulsar-field h-8 min-h-8 py-1 text-xs"
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
                v-else
                v-model="fromValues[field]"
                :type="getInputType(field)"
                :placeholder="getDatePlaceholder(field)"
                :dir="getInputDirection(field)"
                class="pulsar-field h-8 min-h-8 py-1 text-xs"
              />
            </td>
          </tr>

          <tr>
            <td
              class="px-2 py-1.5 text-center font-medium text-muted"
            >
              {{ translations.to || 'To' }}
            </td>

            <td
              v-for="field in fields"
              :key="'to-' + field"
              class="border-l border-border p-1"
            >
              <select
                v-if="isDropdown(field)"
                v-model="toValues[field]"
                class="pulsar-field h-8 min-h-8 py-1 text-xs"
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
                v-else
                v-model="toValues[field]"
                :type="getInputType(field)"
                :placeholder="getDatePlaceholder(field)"
                :dir="getInputDirection(field)"
                class="pulsar-field h-8 min-h-8 py-1 text-xs"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import {
  ref,
  computed,
  watch,
  effectScope,
  onBeforeUnmount
} from 'vue'

import {
  language,
  languageMeta
} from '@/stores/uiStore'

import {
  useTranslation
} from '@/composables/useTranslation'

import {
  useDomainOptions
} from '@/composables/useDomainOptions'


// --------------------------------------------------
// Props & Emits
// --------------------------------------------------
const props = defineProps({
  config: {
    type: Object,
    required: true
  },

  baseConfig: {
    type: Object,
    default: () => ({})
  },

  filters: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits([
  'update:filters',
  'search'
])


// --------------------------------------------------
// Search Values
// --------------------------------------------------
const fromValues = ref({})
const toValues = ref({})


// --------------------------------------------------
// Reactive Value Comparison
// --------------------------------------------------
function areValueMapsEqual(left = {}, right = {}) {
  const leftKeys = Object.keys(left)
  const rightKeys = Object.keys(right)

  if (leftKeys.length !== rightKeys.length) {
    return false
  }

  return leftKeys.every(key => {
    return (
      Object.prototype.hasOwnProperty.call(right, key) &&
      Object.is(left[key], right[key])
    )
  })
}

function areFiltersEqual(left = {}, right = {}) {
  const leftKeys = Object.keys(left)
  const rightKeys = Object.keys(right)

  if (leftKeys.length !== rightKeys.length) {
    return false
  }

  return leftKeys.every(field => {
    if (!Object.prototype.hasOwnProperty.call(right, field)) {
      return false
    }

    const leftRange = left[field] || {}
    const rightRange = right[field] || {}

    return (
      Object.is(leftRange.from ?? '', rightRange.from ?? '') &&
      Object.is(leftRange.to ?? '', rightRange.to ?? '')
    )
  })
}


// --------------------------------------------------
// Fields
// --------------------------------------------------
const fields = computed(() => {
  return (props.config?.field_order || []).filter(
    field => props.config?.fields?.[field]?.visible_in_search !== false
  )
})

function getFieldMeta(field) {
  return props.config?.fields?.[field] || {}
}

function getControlType(field) {
  const meta = getFieldMeta(field)

  return (
    meta.control_type ||
    meta.type ||
    'text'
  )
}

function isDateField(field) {
  return getControlType(field) === 'date'
}


// --------------------------------------------------
// Domain Control Metadata
// --------------------------------------------------
function isDropdown(field) {
  const meta = getFieldMeta(field)

  const domainControlType =
    String(
      meta.domain_control_type || ''
    ).toUpperCase()

  if (domainControlType) {
    return domainControlType === 'DDLB'
  }

  return (
    meta.is_ddlistbox === true ||
    getControlType(field) === 'ddlistbox'
  )
}


// --------------------------------------------------
// Language & Calendar Metadata
// --------------------------------------------------
const isRtl = computed(() => {
  return languageMeta.value?.is_rtl === true
})

const calendarCode = computed(() => {
  return (
    languageMeta.value?.calendar_code ||
    'gregorian'
  )
})

function getInputType(field) {
  if (!isDateField(field)) {
    return 'text'
  }

  return (
    calendarCode.value === 'gregorian'
      ? 'date'
      : 'text'
  )
}

function getInputDirection(field) {
  if (isDateField(field)) {
    return isRtl.value
      ? 'rtl'
      : 'ltr'
  }

  return isRtl.value
    ? 'rtl'
    : 'auto'
}

function getDatePlaceholder(field) {
  if (!isDateField(field)) {
    return ''
  }

  return (
    languageMeta.value?.date_format ||
    'YYYY-MM-DD'
  )
}


// --------------------------------------------------
// Domain Option Scopes
// --------------------------------------------------
const domainOptionsMap = ref({})
const domainOptionScopes = new Map()

function stopDomainOptionScopes() {
  for (const scope of domainOptionScopes.values()) {
    scope.stop()
  }

  domainOptionScopes.clear()
}


// --------------------------------------------------
// Domain Identity
// --------------------------------------------------
function getDomainIdentity(field) {
  const meta = getFieldMeta(field)
  const base = props.baseConfig || {}

  return {
    schemaName:
      meta.schema_name ||
      meta.schm_name ||
      base.schema_name ||
      base.schm_name ||
      null,

    tableName:
      meta.table_name ||
      meta.tbl_name ||
      base.table_name ||
      base.tbl_name ||
      null,

    fieldName:
      meta.field_name ||
      field
  }
}


// --------------------------------------------------
// Load Domain Options
// --------------------------------------------------
function loadDomainOptions() {
  stopDomainOptionScopes()

  domainOptionsMap.value = {}

  for (const field of fields.value) {
    if (!isDropdown(field)) {
      continue
    }

    const scope = effectScope()

    let optionsRef = null

    scope.run(() => {
      const domainConfig = computed(() => {
        return getDomainIdentity(field)
      })

      optionsRef = useDomainOptions(
        domainConfig
      )

      watch(
        optionsRef,
        value => {
          domainOptionsMap.value = {
            ...domainOptionsMap.value,
            [field]: Array.isArray(value)
              ? value
              : []
          }
        },
        {
          immediate: true,
          deep: true
        }
      )
    })

    if (optionsRef) {
      domainOptionScopes.set(
        field,
        scope
      )
    } else {
      scope.stop()
    }
  }
}


// --------------------------------------------------
// Domain Metadata & Base Changes
// --------------------------------------------------
watch(
  [
    fields,
    () => props.baseConfig?.schm_name,
    () => props.baseConfig?.tbl_name,
    () => props.baseConfig?.schema_name,
    () => props.baseConfig?.table_name
  ],
  loadDomainOptions,
  {
    immediate: true
  }
)

function getDomainOptions(field) {
  return domainOptionsMap.value[field] || []
}


// --------------------------------------------------
// Translation
// --------------------------------------------------
const {
  translate
} = useTranslation()

const translations = ref({})

async function loadTranslations() {
  if (!props.config) {
    return
  }

  const currentLanguage =
    language.value || 'en'

  const labels = {}

  labels.search = await translate(
    'search',
    currentLanguage,
    'SearchToolbar'
  )

  labels.clear = await translate(
    'clear',
    currentLanguage,
    'SearchToolbar'
  )

  labels.from = await translate(
    'from',
    currentLanguage,
    'SearchToolbar'
  )

  labels.to = await translate(
    'to',
    currentLanguage,
    'SearchToolbar'
  )

  for (const field of fields.value) {
    labels[field] = await translate(
      field,
      currentLanguage,
      props.config.field_labels_context ||
        'DefaultSearch'
    )
  }

  translations.value = labels
}

watch(
  language,
  loadTranslations,
  {
    immediate: true
  }
)


// --------------------------------------------------
// External Filter State
// --------------------------------------------------
watch(
  () => props.filters,
  value => {
    const nextFrom = {}
    const nextTo = {}

    if (
      value &&
      typeof value === 'object'
    ) {
      for (const field of fields.value) {
        const range = value[field]

        if (
          !range ||
          typeof range !== 'object'
        ) {
          continue
        }

        if (range.from !== undefined) {
          nextFrom[field] = range.from
        }

        if (range.to !== undefined) {
          nextTo[field] = range.to
        }
      }
    }

    if (!areValueMapsEqual(fromValues.value, nextFrom)) {
      fromValues.value = nextFrom
    }

    if (!areValueMapsEqual(toValues.value, nextTo)) {
      toValues.value = nextTo
    }
  },
  {
    immediate: true,
    deep: true
  }
)


// --------------------------------------------------
// Filters
// --------------------------------------------------
watch(
  [fromValues, toValues],
  () => {
    const combined = {}

    for (const field of fields.value) {
      const from = fromValues.value[field]
      const to = toValues.value[field]

      if (
        (from !== undefined && from !== '') ||
        (to !== undefined && to !== '')
      ) {
        combined[field] = {
          from: normalizeDateValue(field, from),
          to: normalizeDateValue(field, to)
        }
      }
    }

    const currentFilters =
      props.filters &&
      typeof props.filters === 'object'
        ? props.filters
        : {}

    if (!areFiltersEqual(combined, currentFilters)) {
      emit('update:filters', combined)
    }
  },
  {
    deep: true
  }
)


// --------------------------------------------------
// Date Normalization
// --------------------------------------------------
function normalizeDateValue(field, value) {
  if (
    !value ||
    !isDateField(field)
  ) {
    return value
  }

  return value
}


// --------------------------------------------------
// Actions
// --------------------------------------------------
function doSearch() {
  emit('search')
}

function clearFilters() {
  fromValues.value = {}
  toValues.value = {}

  emit('update:filters', {})

  emit('search')
}


// --------------------------------------------------
// Lifecycle
// --------------------------------------------------
onBeforeUnmount(() => {
  stopDomainOptionScopes()
})


// ===============================================
// Important Learning Points
// ===============================================
// 1. Search fields remain metadata-driven.
// 2. Domain identity consists of schema, table, and field.
// 3. components_base supplies the physical schema and table.
// 4. field_domain_config determines the DDLB control type.
// 5. field_domain_values is the source of DDLB options.
// 6. Translation is resolved by the backend domain service.
// 7. The active language is handled by useDomainOptions.
// 8. Metadata changes reload the affected domain options.
// 9. DDDW fields are not treated as DDLB fields.
// 10. Legacy is_ddlistbox remains supported temporarily.
// 11. Search filters remain synchronized with the parent.
// 12. Date input behavior remains driven by language metadata.
// 13. Domain option watchers are isolated in effect scopes.
// 14. Domain option scopes are stopped when the component is unmounted.
// 15. Search remains independent of primary_key semantics.
// 16. Search remains independent of where_clause semantics.
// 17. Search does not create or resolve parm[n].
// 18. No domain values are hard-coded in the frontend.
</script>
