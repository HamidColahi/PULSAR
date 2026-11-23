
<!-- ===============================================
File: frontend/src/components/grids/dynamic_dw_grid.vue
Description: Metadata-driven dynamic data grid with user-specific multi-column sorting
Last Modified: 2026-11-23 23:58 (Asia/Baku)
Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
=============================================== -->

<script setup>
import {
  ref,
  computed,
  watch,
  effectScope,
  onBeforeUnmount
} from 'vue'

import {
  useTranslation
} from '@/composables/useTranslation'

import axios from '@/utils/axiosInstance'

import {
  useDomainOptions
} from '@/composables/useDomainOptions'

import {
  useDateFormat
} from '@/composables/useDateFormat'

import {
  darkMode,
  language,
  languageMeta
} from '@/stores/uiStore'

import dynamic_dw_search from './dynamic_dw_search.vue'
import field_expander from '@/components/field_expander.vue'


// --------------------------------------------------
// Props
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

  items: {
    type: Array,
    required: true
  },

  mode: {
    type: String,
    default: 'view'
  }
})


// --------------------------------------------------
// Emits
// --------------------------------------------------
const emit = defineEmits([
  'row-selected'
])


// --------------------------------------------------
// State
// --------------------------------------------------
const filters = ref({})
const translations = ref({})
const domainOptionsMap = ref({})
const domainOptionRefs = ref({})
const selectedRowLocal = ref(null)
const sortSpec = ref([])
const sortPreferenceReady = ref(false)
const sortLabels = ref({
  none: 'No sorting',
  asc: 'Sort ascending',
  desc: 'Sort descending'
})

const expandedField = ref({
  open: false,
  field: null,
  label: '',
  value: ''
})

const lang = computed(
  () => language.value
)

const isRtl = computed(() => {
  return languageMeta.value?.is_rtl === true
})

const {
  translate
} = useTranslation()

const {
  formatDate
} = useDateFormat()


// --------------------------------------------------
// Row Selection
// --------------------------------------------------
function selectRow(item) {
  selectedRowLocal.value = item || null

  emit(
    'row-selected',
    item || null
  )
}


// --------------------------------------------------
// Expanded Field
// --------------------------------------------------
function openExpandedField(item, col) {
  expandedField.value = {
    open: true,
    field: col.field,
    label:
      translations.value[col.field] ||
      col.field,
    value: formatValue(
      item,
      col
    )
  }
}

function closeExpandedField() {
  expandedField.value = {
    open: false,
    field: null,
    label: '',
    value: ''
  }
}


// --------------------------------------------------
// DDLB Metadata
// --------------------------------------------------
function isDDLB(meta) {
  if (!meta) {
    return false
  }

  return (
    String(
      meta.domain_control_type || ''
    ).toUpperCase() === 'DDLB' ||
    meta.is_ddlistbox === true
  )
}

const ddlistboxFields = computed(() => {

  const fieldMetadata =
    props.config?.fields || {}

  return Object.entries(
    fieldMetadata
  )
    .filter(
      ([, meta]) => isDDLB(meta)
    )
    .map(
      ([field]) => field
    )
})


// --------------------------------------------------
// Domain Option Scopes
// --------------------------------------------------
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

  const meta =
    props.config?.fields?.[field] || {}

  const base =
    props.baseConfig || {}

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
function loadDomainOptions(fieldsToLoad) {

  stopDomainOptionScopes()

  const refs = {}

  domainOptionsMap.value = {}

  for (const field of fieldsToLoad) {

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
      refs[field] = optionsRef
      domainOptionScopes.set(
        field,
        scope
      )
    } else {
      scope.stop()
    }
  }

  domainOptionRefs.value = refs
}

watch(
  ddlistboxFields,
  fieldsToLoad => {
    loadDomainOptions(
      fieldsToLoad
    )
  },
  {
    immediate: true
  }
)


// --------------------------------------------------
// Domain Label
// --------------------------------------------------
function getLabel(field, value) {

  const options =
    domainOptionsMap.value[field] || []

  const option = options.find(
    item =>
      String(item.value) ===
      String(value)
  )

  return option?.label ?? value
}


// --------------------------------------------------
// Filtering
// --------------------------------------------------
const filteredItems = computed(() => {

  if (
    !filters.value ||
    Object.keys(
      filters.value
    ).length === 0
  ) {
    return props.items
  }

  return props.items.filter(
    item => {

      return Object.entries(
        filters.value
      ).every(
        ([field, range]) => {

          let val = item[field]

          const type =
            props.config.fields?.[field]?.control_type ||
            props.config.fields?.[field]?.type ||
            'text'

          if (
            val === null ||
            val === undefined
          ) {
            return false
          }

          let from = range?.from
          let to = range?.to

          if (type === 'number') {

            from =
              from !== undefined
                ? Number(from)
                : undefined

            to =
              to !== undefined
                ? Number(to)
                : undefined
          }

          if (type === 'date') {

            const valueDate = new Date(val)

            if (
              Number.isNaN(
                valueDate.getTime()
              )
            ) {
              return false
            }

            val = valueDate

            if (from) {
              from = new Date(from)

              if (
                Number.isNaN(
                  from.getTime()
                )
              ) {
                return false
              }
            }

            if (to) {
              to = new Date(to)

              if (
                Number.isNaN(
                  to.getTime()
                )
              ) {
                return false
              }
            }
          }

          if (type !== 'number') {

            if (
              from &&
              (
                !to ||
                to === ''
              )
            ) {
              const valStr =
                String(val).toLowerCase()

              const fromStr =
                String(from).toLowerCase()

              return valStr.includes(
                fromStr
              )
            }

            if (
              from !== undefined &&
              to !== undefined &&
              from !== '' &&
              to !== ''
            ) {
              return (
                val >= from &&
                val <= to
              )
            }

            return true
          }

          if (
            from !== undefined &&
            val < from
          ) {
            return false
          }

          if (
            to !== undefined &&
            val > to
          ) {
            return false
          }

          return true
        }
      )
    }
  )
})


// --------------------------------------------------
// Supervisor and User Multi-Column Sorting
// --------------------------------------------------
const componentName = computed(() => {
  return props.config?.component_name ||
    props.baseConfig?.component_name ||
    ''
})

const forcedSortSpec = ref([])

function getSortMode(field) {
  return Number(props.config?.fields?.[field]?.field_sort ?? 0)
}

function isSortEnabled(field) {
  return [1, 2, 3].includes(getSortMode(field))
}

function isForcedSort(field) {
  return [2, 3].includes(getSortMode(field))
}

function getSortDirection(field) {
  const forced = forcedSortSpec.value.find(
    item => item.field === field
  )

  if (forced) {
    return forced.direction
  }

  return sortSpec.value.find(
    item => item.field === field
  )?.direction || 'none'
}

function getSortPriority(field) {
  const forcedIndex = forcedSortSpec.value.findIndex(
    item => item.field === field
  )

  if (forcedIndex >= 0) {
    return forcedIndex + 1
  }

  const userTerm = sortSpec.value.find(
    item => item.field === field
  )

  return userTerm
    ? forcedSortSpec.value.length + userTerm.field_sort_order
    : 0
}

function getSortLabel(field) {
  const direction = getSortDirection(field)
  const label = sortLabels.value[direction] || sortLabels.value.none
  const priority = getSortPriority(field)

  if (isForcedSort(field)) {
    return `${label}, ${sortLabels.value.forced}, priority ${priority}`
  }

  return priority > 0
    ? `${label}, priority ${priority}`
    : label
}

async function loadSortPreference() {
  const name = componentName.value

  sortPreferenceReady.value = false

  if (!name) {
    forcedSortSpec.value = []
    sortSpec.value = []
    sortPreferenceReady.value = true
    return
  }

  try {
    const response = await axios.get('/config/grid_sort', {
      params: {
        component_name: name,
        field_mode: props.config?.field_mode || 'list'
      }
    })

    const fieldMetadata = props.config?.fields || {}
    const allowedUserFields = new Set(
      Object.entries(fieldMetadata)
        .filter(([, meta]) => Number(meta?.field_sort ?? 0) === 1)
        .map(([field]) => field)
    )

    const allowedForcedFields = new Set(
      Object.entries(fieldMetadata)
        .filter(([, meta]) => [2, 3].includes(Number(meta?.field_sort ?? 0)))
        .map(([field]) => field)
    )

    forcedSortSpec.value = (
      Array.isArray(response.data?.forced_sort_spec)
        ? response.data.forced_sort_spec
        : []
    )
      .filter(item =>
        allowedForcedFields.has(item?.field) &&
        ['asc', 'desc'].includes(item?.direction)
      )
      .sort((a, b) =>
        Number(a.field_sort_order) - Number(b.field_sort_order)
      )

    sortSpec.value = (
      Array.isArray(response.data?.user_sort_spec)
        ? response.data.user_sort_spec
        : []
    )
      .filter(item =>
        allowedUserFields.has(item?.field) &&
        ['asc', 'desc'].includes(item?.direction) &&
        Number.isInteger(Number(item?.field_sort_order)) &&
        Number(item.field_sort_order) > 0
      )
      .map(item => ({
        field: item.field,
        direction: item.direction,
        field_sort_order: Number(item.field_sort_order)
      }))
      .sort((a, b) =>
        a.field_sort_order - b.field_sort_order
      )
  } catch (err) {
    forcedSortSpec.value = []
    sortSpec.value = []
    console.error('dynamic_dw_grid: failed to load sort preference', err)
  } finally {
    sortPreferenceReady.value = true
  }
}

let sortSaveQueue = Promise.resolve()

async function persistSortPreference() {
  if (!sortPreferenceReady.value || !componentName.value) {
    return
  }

  const payload = {
    component_name: componentName.value,
    field_mode: props.config?.field_mode || 'list',
    sort_spec: sortSpec.value.map(item => ({ ...item }))
  }

  sortSaveQueue = sortSaveQueue
    .catch(() => undefined)
    .then(() => axios.put('/config/grid_sort', payload))

  try {
    await sortSaveQueue
  } catch (err) {
    console.error('dynamic_dw_grid: failed to save sort preference', err)
  }
}

function normalizeUserSortOrder(items) {
  return items.map((item, index) => ({
    ...item,
    field_sort_order: index + 1
  }))
}

function cycleSort(field) {
  if (getSortMode(field) !== 1) {
    return
  }

  const nextDirection = {
    none: 'asc',
    asc: 'desc',
    desc: 'none'
  }[getSortDirection(field)]

  const current = sortSpec.value.find(
    item => item.field === field
  )

  if (nextDirection === 'none') {
    sortSpec.value = normalizeUserSortOrder(
      sortSpec.value.filter(item => item.field !== field)
    )
  } else if (current) {
    sortSpec.value = sortSpec.value.map(item =>
      item.field === field
        ? { ...item, direction: nextDirection }
        : item
    )
  } else {
    sortSpec.value = [
      ...sortSpec.value,
      {
        field,
        direction: nextDirection,
        field_sort_order: sortSpec.value.length + 1
      }
    ]
  }

  persistSortPreference()
}

function compareSortValues(left, right, field, direction) {
  const meta = props.config?.fields?.[field] || {}
  const type = String(meta.control_type || meta.type || '').toLowerCase()

  let a = left?.[field]
  let b = right?.[field]

  if (a === null || a === undefined || a === '') {
    return b === null || b === undefined || b === '' ? 0 : 1
  }

  if (b === null || b === undefined || b === '') {
    return -1
  }

  let result = 0

  if (['number', 'numeric', 'integer', 'decimal', 'float'].includes(type)) {
    const numberA = Number(a)
    const numberB = Number(b)
    result = Number.isNaN(numberA) || Number.isNaN(numberB)
      ? String(a).localeCompare(String(b), lang.value, { numeric: true })
      : numberA - numberB
  } else if (type === 'date' || type === 'datetime' || type === 'timestamp') {
    const dateA = new Date(a).getTime()
    const dateB = new Date(b).getTime()
    result = Number.isNaN(dateA) || Number.isNaN(dateB)
      ? String(a).localeCompare(String(b), lang.value, { numeric: true })
      : dateA - dateB
  } else if (typeof a === 'boolean' && typeof b === 'boolean') {
    result = Number(a) - Number(b)
  } else {
    const valueA = isDDLB(meta) ? getLabel(field, a) : a
    const valueB = isDDLB(meta) ? getLabel(field, b) : b
    result = String(valueA).localeCompare(
      String(valueB),
      lang.value,
      { numeric: true, sensitivity: 'base' }
    )
  }

  return direction === 'desc' ? -result : result
}

const effectiveSortSpec = computed(() => [
  ...forcedSortSpec.value,
  ...sortSpec.value
])

const sortedItems = computed(() => {
  const source = [...filteredItems.value]
  const effectiveSpec = effectiveSortSpec.value

  if (!effectiveSpec.length) {
    return source
  }

  return source
    .map((item, index) => ({ item, index }))
    .sort((left, right) => {
      for (const term of effectiveSpec) {
        const result = compareSortValues(
          left.item,
          right.item,
          term.field,
          term.direction
        )

        if (result !== 0) {
          return result
        }
      }

      return left.index - right.index
    })
    .map(entry => entry.item)
})

watch(
  componentName,
  loadSortPreference,
  { immediate: true }
)


// --------------------------------------------------
// Translations
// --------------------------------------------------
async function loadTranslations() {

  if (!props.config) {
    return
  }

  const keys = [
    ...(props.config.field_order || []),
    'actions',
    'no_data_found',
    'records'
  ]

  const result = {}

  for (const key of keys) {

    result[key] = await translate(
      key,
      lang.value,
      props.config.field_labels_context ||
        'DefaultGrid'
    )
  }

  translations.value = result

  const [none, asc, desc, forced] = await Promise.all([
    translate('pulsar.grid.sortNone', lang.value, 'Default'),
    translate('pulsar.grid.sortAscending', lang.value, 'Default'),
    translate('pulsar.grid.sortDescending', lang.value, 'Default'),
    translate('pulsar.grid.sortForced', lang.value, 'Default')
  ])

  sortLabels.value = {
    none: none && none !== 'pulsar.grid.sortNone' ? none : 'No sorting',
    asc: asc && asc !== 'pulsar.grid.sortAscending' ? asc : 'Sort ascending',
    desc: desc && desc !== 'pulsar.grid.sortDescending' ? desc : 'Sort descending',
    forced: forced && forced !== 'pulsar.grid.sortForced' ? forced : 'Forced sorting'
  }
}

watch(
  lang,
  loadTranslations,
  {
    immediate: true
  }
)


// --------------------------------------------------
// Fields
// --------------------------------------------------
const fields = computed(() => {

  return (
    props.config?.field_order || []
  ).map(field => {

    const meta =
      props.config?.fields?.[field] || {}

    return {
      field,

      type:
        meta.control_type ||
        meta.type ||
        'text',

      control_type:
        meta.control_type ||
        meta.type ||
        'text'
    }
  })
})


// --------------------------------------------------
// Value Formatting
// --------------------------------------------------
function formatValue(item, col) {

  const val = item[col.field]

  const meta =
    props.config?.fields?.[col.field] || {}

  if (isDDLB(meta)) {
    return getLabel(
      col.field,
      val
    )
  }

  if (
    col.type === 'date' &&
    val
  ) {
    return formatDate(val)
  }

  return val
}


// --------------------------------------------------
// Search
// --------------------------------------------------
function onSearch() {
  return filteredItems.value
}


// --------------------------------------------------
// Configuration Changes
// --------------------------------------------------
watch(
  () => props.config,
  () => {
    loadTranslations()
  },
  {
    immediate: true
  }
)


// --------------------------------------------------
// Items Changes
// --------------------------------------------------
watch(
  () => props.items,
  items => {

    if (
      !items.includes(
        selectedRowLocal.value
      )
    ) {
      selectedRowLocal.value = null
    }
  }
)


// --------------------------------------------------
// Lifecycle
// --------------------------------------------------
onBeforeUnmount(() => {
  stopDomainOptionScopes()
})

</script>


<template>
  <div
    :class="{ dark: darkMode }"
    :dir="isRtl ? 'rtl' : 'ltr'"
    class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden"
  >

    <div class="shrink-0">
      <dynamic_dw_search
        :config="props.config"
        :base-config="props.baseConfig"
        v-model:filters="filters"
        @search="onSearch"
      />
    </div>

    <div
      class="pulsar-surface flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden"
      style="
        border-color: var(--pulsar-level-border);
        background-color: var(--pulsar-level-surface);
      "
    >

      <div
        class="flex shrink-0 items-center justify-between border-b px-3 py-2.5"
        style="border-color:var(--pulsar-level-border)"
      >

        <div class="flex items-center gap-2">

          <span
            class="h-2 w-2 rounded-full"
            style="background:var(--pulsar-level-accent)"
          ></span>

          <span
            class="text-xs font-semibold text-label"
          >
            {{
              props.config?.title ||
              'Records'
            }}
          </span>

        </div>

        <span
          class="text-[11px] text-muted"
        >
          {{ filteredItems.length }}
          {{ translations.records || 'records' }}
        </span>

      </div>


      <div
        class="min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-auto overscroll-contain pb-2.5"
      >

        <table
          class="min-w-full table-auto border-collapse text-xs text-input"
        >

          <thead
            class="pulsar-grid-header sticky top-0 z-10 text-label"
          >

            <tr>

              <th
                class="w-10 border-b px-3 py-2.5 text-left font-semibold"
                style="border-color:var(--pulsar-level-border)"
              >
                #
              </th>

              <th
                v-for="col in fields"
                :key="col.field"
                class="whitespace-nowrap border-b border-l px-3 py-2.5 text-left font-semibold"
                style="border-color:var(--pulsar-level-border)"
              >
                <span class="inline-flex items-center gap-1.5">
                  <span>{{
                    translations[col.field] ||
                    col.field
                  }}</span>
                  <button
                    v-if="isSortEnabled(col.field)"
                    type="button"
                    :disabled="!sortPreferenceReady || isForcedSort(col.field)"
                    class="inline-flex h-5 w-5 items-center justify-center rounded transition focus-visible:outline focus-visible:outline-1 disabled:cursor-not-allowed disabled:opacity-100"
                    :class="isForcedSort(col.field)
                      ? 'text-amber-500 cursor-not-allowed'
                      : getSortDirection(col.field) !== 'none'
                        ? 'text-primary hover:bg-hover'
                        : 'text-muted hover:bg-hover hover:text-primary'"
                    :aria-label="getSortLabel(col.field)"
                    :title="getSortLabel(col.field)"
                    @click.stop="cycleSort(col.field)"
                  >
                    <span
                      v-if="getSortDirection(col.field) === 'asc'"
                      class="text-sm font-bold leading-none"
                    >↑</span>
                    <span
                      v-else-if="getSortDirection(col.field) === 'desc'"
                      class="text-sm font-bold leading-none"
                    >↓</span>
                    <span
                      v-else
                      class="text-sm leading-none"
                    >↕</span>
                    <span
                      v-if="getSortPriority(col.field) > 0"
                      class="ml-0.5 text-[8px] leading-none"
                    >{{ getSortPriority(col.field) }}</span>
                  </button>
                </span>
              </th>

            </tr>

          </thead>


          <tbody>

            <tr
              v-for="(
                item, index
              ) in sortedItems"
              :key="index"
              @click="selectRow(item)"
              :class="
                selectedRowLocal === item
                  ? 'pulsar-row-selected'
                  : 'pulsar-row'
              "
              class="group cursor-pointer border-b last:border-b-0 transition-colors"
              style="border-color:var(--pulsar-level-border)"
            >

              <td
                class="px-3 py-2.5 text-muted tabular-nums"
              >
                {{ index + 1 }}
              </td>

              <td
                v-for="col in fields"
                :key="col.field"
                @dblclick.stop="
                  openExpandedField(
                    item,
                    col
                  )
                "
                class="whitespace-nowrap border-l px-3 py-2.5"
                style="border-color:var(--pulsar-level-border)"
              >
                {{
                  formatValue(
                    item,
                    col
                  )
                }}
              </td>

            </tr>


            <tr
              v-if="filteredItems.length === 0"
            >

              <td
                :colspan="fields.length + 1"
                class="px-4 py-12 text-center text-sm text-empty"
              >
                {{
                  translations.no_data_found ||
                  'No data found'
                }}
              </td>

            </tr>

          </tbody>

        </table>

      </div>

    </div>


    <!-- Universal Expanded Field Viewer -->
    <field_expander
      :open="expandedField.open"
      :modelValue="expandedField.value"
      :label="expandedField.label"
      :mode="props.mode"
      @update:open="
        value => {
          if (!value) {
            closeExpandedField()
          }
        }
      "
      @close="closeExpandedField"
    />

  </div>
</template>


<style scoped>
.pulsar-grid-header {
  background:
    linear-gradient(
      to bottom,
      var(--pulsar-level-border),
      var(--pulsar-level-surface)
    );

  box-shadow:
    0 2px 5px
    color-mix(
      in srgb,
      var(--pulsar-level-border) 65%,
      transparent
    );
}

.pulsar-grid-header th {
  background:
    linear-gradient(
      to bottom,
      var(--pulsar-level-border),
      var(--pulsar-level-surface)
    );

  color: var(--pulsar-level-text);
  font-weight: 700;
  letter-spacing: 0.01em;
  border-bottom-width: 2px;
}

.pulsar-grid-header th:first-child {
  color: var(--pulsar-level-muted);
}

.pulsar-grid-header th:not(:first-child) {
  border-left-color: var(--pulsar-level-border);
}

.pulsar-row:hover {
  background-color: var(--pulsar-level-hover);
}

.pulsar-row-selected {
  background-color: var(--pulsar-level-accent-soft);
  box-shadow:
    inset 3px 0 0
    var(--pulsar-level-accent);
}

[dir='rtl'] .pulsar-row-selected {
  box-shadow:
    inset -3px 0 0
    var(--pulsar-level-accent);
}
</style>


<!--
Important Learning Points:

1. Grid direction is derived from active language metadata.
2. Date display uses the shared metadata-driven date formatter.
3. Domain options are retrieved using physical field identity.
4. DDLB fields are identified by domain_control_type.
5. Legacy is_ddlistbox remains supported for API compatibility.
6. Schema and table names are received through baseConfig.
7. field_domain_values is the source of DDLB options.
8. Translation is handled by the backend domain service.
9. Language changes automatically reload domain options.
10. Domain option watchers are isolated in effect scopes.
11. Domain option scopes are stopped when the component is unmounted.
12. No domain values are hard-coded in the grid.
13. DDDW options are not loaded by this component.
14. Search remains fixed above the grid viewport.
15. Grid header and record list remain inside the grid surface.
16. Vertical scrolling is isolated to the grid record viewport.
17. Horizontal scrolling is isolated to the grid record viewport.
18. Flex children use min-h-0 so overflow remains inside the grid.
19. Overscroll is contained to prevent page-level scroll chaining.
20. Grid exposes the complete selected record through row-selected.
21. Grid does not accept or interpret primary_key metadata.
22. Grid does not interpret where_clause metadata.
23. Grid does not create parm[n].
24. Grid does not construct record identity.
25. Primary-key semantics are centralized in component_key.py.
26. Where-clause semantics are centralized in component_where.py.
27. Selected-record state remains data-oriented and independent of PK semantics.
28. Grid visual accents are driven by PULSAR page-level CSS variables.
29. Visual theme remains independent from page_type and runtime data semantics.
30. Grid header has a distinct visual surface while remaining level-theme driven.
31. Sticky header remains visually separated from scrolling record rows.
32. Every grid field supports universal Double Click expansion.
33. Expanded field behavior requires no field-specific metadata or option.
34. Grid passes its current mode to the universal field expander.
35. Grid uses the existing formatted field value for expanded viewing.
36. Double Click stops row-selection propagation while opening the expanded viewer.
-->
