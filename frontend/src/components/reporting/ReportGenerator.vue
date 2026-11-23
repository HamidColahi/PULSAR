<!-- ===============================================
File: frontend/src/components/reporting/ReportGenerator.vue
Description: Metadata-driven Report Generator designer and manager
Modified: 2026-11-24 (Asia/Baku)
In collaboration with GPT4 Chat Assistant: Bahram
=============================================== -->

<template>
  <section class="flex min-h-0 min-w-0 flex-1 flex-col gap-2">
    <header class="flex shrink-0 flex-wrap items-end gap-2 rounded-xl border border-border bg-panel p-2">
      <div class="min-w-[180px] flex-1">
        <label class="mb-1 block text-[10px] text-muted">{{ labels.manager }}</label>
        <select v-model="selectedReportId" class="w-full rounded-lg border border-border bg-panel px-2.5 py-2 text-xs" @change="handleSelectReport">
          <option value="">{{ labels.unsaved }}</option>
          <option v-for="report in reports" :key="report.report_id" :value="report.report_id">
            {{ report.report_title }} · {{ accessLabel(report.access_mode) }}
          </option>
        </select>
      </div>

      <div class="min-w-[180px] flex-1">
        <label class="mb-1 block text-[10px] text-muted">{{ labels.title }}</label>
        <input v-model="reportTitle" :disabled="Boolean(selectedReportId) && !canEdit" class="w-full rounded-lg border border-border bg-panel px-2.5 py-2 text-xs disabled:opacity-60" :placeholder="labels.title" />
      </div>

      <div class="flex flex-wrap gap-1.5">
        <button class="report-action report-primary" :disabled="loading || !canSave" @click="saveReport">{{ labels.save }}</button>
        <button class="report-action" :disabled="loading" @click="saveAs">{{ labels.saveAs }}</button>
        <button class="report-action" :disabled="loading" @click="resetDesign">{{ labels.reset }}</button>
        <button class="report-action" :disabled="loading" @click="runReport">{{ labels.run }}</button>
        <button class="report-action" :disabled="loading" @click="panelOpen = !panelOpen">{{ panelOpen ? labels.hideDesigner : labels.showDesigner }}</button>
        <button v-if="canShare" class="report-action" :disabled="loading" @click="openDesigner('sharing')">{{ labels.share }}</button>
        <button v-if="canPublish && sharingPolicy !== 'PUBLIC'" class="report-action" :disabled="loading || !selectedReportId" @click="publishReport">{{ labels.publish }}</button>
        <button v-if="canPublish && sharingPolicy === 'PUBLIC'" class="report-action" :disabled="loading || !selectedReportId" @click="unpublishReport">{{ labels.unpublish }}</button>
        <button v-if="selectedReportId && canDelete" class="report-action report-danger" :disabled="loading" @click="deleteReport">{{ labels.delete }}</button>
      </div>
    </header>

    <div class="flex min-h-0 min-w-0 flex-1 gap-2 overflow-hidden">
      <aside v-if="panelOpen" class="flex w-[290px] shrink-0 flex-col overflow-hidden rounded-xl border border-border bg-panel">
        <nav class="grid grid-cols-4 border-b border-border">
          <button v-for="tab in tabs" :key="tab.id" class="border-b-2 px-1 py-2 text-[10px] font-semibold" :class="activeTab === tab.id ? 'border-primary text-primary' : 'border-transparent text-muted hover:text-input'" @click="activeTab = tab.id">
            {{ labels[tab.label] }}
          </button>
        </nav>

        <div class="min-h-0 flex-1 overflow-y-auto p-3">
          <section v-if="activeTab === 'columns'" class="space-y-2">
            <div class="text-xs font-semibold">{{ labels.columns }}</div>
            <div v-for="column in columns" :key="column.field_name" class="rounded-lg border border-border p-2">
              <label class="flex items-center gap-2 text-xs">
                <input v-model="column.is_visible" type="checkbox" @change="runReport" />
                <span class="min-w-0 flex-1 truncate">{{ fieldLabel(column.field_name) }}</span>
              </label>
              <div class="mt-2 flex items-center gap-2">
                <label class="text-[10px] text-muted">{{ labels.width }}</label>
                <input v-model.number="column.width_px" type="number" min="48" max="2000" class="w-20 rounded border border-border bg-panel px-1.5 py-1 text-xs" @change="runReport" />
              </div>
            </div>
          </section>

          <section v-else-if="activeTab === 'filters'" class="space-y-3">
            <div class="text-xs font-semibold">{{ labels.filterDesigner }}</div>

            <div
              v-for="(group, groupIndex) in filterGroups"
              :key="group.local_id"
              class="space-y-2 rounded-lg border border-border p-2"
            >
              <div class="flex items-center gap-2">
                <span class="flex-1 text-[10px] font-semibold text-muted">{{ labels.group }} {{ groupIndex + 1 }}</span>
                <select v-model="group.logical_operator" class="rounded border border-border bg-panel px-2 py-1 text-xs">
                  <option value="AND">AND</option>
                  <option value="OR">OR</option>
                </select>
                <button class="text-xs text-red-500" @click="removeGroup(groupIndex)">×</button>
              </div>

              <div
                v-for="(filter, index) in group.conditions"
                :key="filter.local_id"
                class="space-y-2 rounded-lg border border-border bg-panel p-2"
              >
                <div class="flex items-center justify-between">
                  <span class="text-[10px] font-semibold text-muted">{{ labels.condition }} {{ index + 1 }}</span>
                  <button class="text-xs text-red-500" @click="removeFilter(groupIndex, index)">×</button>
                </div>
                <select v-model="filter.field_name" class="w-full rounded border border-border bg-panel px-2 py-1.5 text-xs">
                  <option value="">{{ labels.selectField }}</option>
                  <option v-for="field in searchableFields" :key="field" :value="field">{{ fieldLabel(field) }}</option>
                </select>
                <select v-model="filter.operator_code" class="w-full rounded border border-border bg-panel px-2 py-1.5 text-xs">
                  <option v-for="operator in operators" :key="operator" :value="operator">{{ labels['operator_' + operator] || operator }}</option>
                </select>
                <select v-model="filter.parameter_code" class="w-full rounded border border-border bg-panel px-2 py-1.5 text-xs">
                  <option value="">{{ labels.fixedValue }}</option>
                  <option v-for="parameter in parameters" :key="parameter" :value="parameter">{{ labels['parameter_' + parameter] || parameter }}</option>
                </select>
                <input
                  v-if="!filter.parameter_code && !['IS_NULL', 'IS_NOT_NULL'].includes(filter.operator_code)"
                  v-model="filter.value"
                  class="w-full rounded border border-border bg-panel px-2 py-1.5 text-xs"
                  :placeholder="labels.value"
                />
              </div>

              <button class="report-action w-full" @click="addFilter(groupIndex)">{{ labels.addCondition }}</button>
            </div>

            <button class="report-action w-full" @click="addGroup">{{ labels.addGroup }}</button>
            <button class="report-action report-primary w-full" :disabled="loading" @click="runReport">{{ labels.applyFilters }}</button>
          </section>

          <section v-else-if="activeTab === 'sorting'" class="space-y-2">
            <div class="text-xs font-semibold">{{ labels.sorting }}</div>
            <div v-for="column in sortableColumns" :key="column.field_name" class="rounded-lg border border-border p-2">
              <div class="mb-1 text-xs">{{ fieldLabel(column.field_name) }}</div>
              <div class="flex gap-2">
                <select v-model="column.sort_direction" class="min-w-0 flex-1 rounded border border-border bg-panel px-2 py-1.5 text-xs" @change="setSortDirection(column)">
                  <option :value="null">{{ labels.noSort }}</option>
                  <option value="asc">{{ labels.ascending }}</option>
                  <option value="desc">{{ labels.descending }}</option>
                </select>
                <input v-if="column.sort_direction" v-model.number="column.sort_order" type="number" min="1" class="w-14 rounded border border-border bg-panel px-1.5 py-1 text-xs" :aria-label="labels.sortOrder" />
              </div>
            </div>
            <p class="text-[10px] leading-5 text-muted">{{ labels.forcedSortNote }}</p>
            <button class="report-action report-primary w-full" :disabled="loading" @click="runReport">{{ labels.applySorting }}</button>
          </section>

          <section v-else class="space-y-3">
            <div class="text-xs font-semibold">{{ labels.sharing }}</div>
            <div class="space-y-1">
              <label class="text-[10px] text-muted">{{ labels.searchUsers }}</label>
              <div class="flex gap-2">
                <input v-model="shareUserQuery" class="min-w-0 flex-1 rounded border border-border bg-panel px-2 py-1.5 text-xs" :placeholder="labels.shareUserSearch" @input="targetUserId = ''" @keyup.enter="searchShareUsers" />
                <button class="report-action" :disabled="loading || shareUserQuery.trim().length < 2" @click="searchShareUsers">{{ labels.search }}</button>
              </div>
              <div v-if="shareUsers.length" class="max-h-32 overflow-y-auto rounded border border-border">
                <button
                  v-for="user in shareUsers"
                  :key="user.c_user_id"
                  class="flex w-full flex-col border-b border-border px-2 py-1.5 text-left last:border-0 hover:bg-hover"
                  @click="selectShareUser(user)"
                >
                  <span class="text-xs font-medium">{{ user.c_user_full_name || user.c_user_email }}</span>
                  <span class="text-[10px] text-muted">{{ user.c_user_email }}</span>
                </button>
              </div>
              <div v-if="targetUserId" class="rounded bg-hover px-2 py-1.5 text-[10px] text-label">
                {{ labels.selectedShareUser }}: {{ shareUserQuery || targetUserId }}
                <button class="ml-2 text-red-500" @click="targetUserId = ''">×</button>
              </div>
            </div>
            <select v-model="sharePermission" class="w-full rounded border border-border bg-panel px-2 py-1.5 text-xs">
              <option value="VIEW">{{ labels.viewPermission }}</option>
              <option value="EDIT">{{ labels.editPermission }}</option>
            </select>
            <button class="report-action report-primary w-full" :disabled="loading || !selectedReportId || !targetUserId.trim()" @click="shareReport">{{ labels.share }}</button>
            <div class="border-t border-border pt-3">
              <div class="mb-2 text-xs font-semibold">{{ labels.sharedUsers }}</div>
              <div v-for="share in shares" :key="share.share_id" class="mb-2 flex items-center gap-2 rounded-lg border border-border p-2">
                <div class="min-w-0 flex-1">
                  <div class="truncate text-xs font-medium">{{ share.c_user_full_name || share.c_user_email }}</div>
                  <div class="truncate text-[10px] text-muted">{{ share.permission_level }} · {{ share.c_user_email }}</div>
                </div>
                <button v-if="share.is_active" class="text-[10px] text-red-500" @click="unshareReport(share.target_user_id)">{{ labels.remove }}</button>
              </div>
              <p v-if="shares.length === 0" class="text-[10px] text-muted">{{ labels.noShares }}</p>
            </div>
          </section>
        </div>
      </aside>

      <main class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <div v-if="error" class="mb-2 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-700" role="alert">{{ error }}</div>
        <div v-if="loading" class="mb-2 text-xs text-muted" role="status">{{ labels.loading }}</div>
        <component
          :is="gridComponent"
          :config="config"
          :base-config="baseConfig"
          :items="gridItems"
          :report-mode="true"
          :report-columns="columns"
          @report-columns-change="updateColumns"
          @row-selected="$emit('row-selected', $event)"
        />
        <footer class="mt-2 flex shrink-0 items-center justify-between rounded-lg border border-border bg-panel px-3 py-2 text-[10px] text-muted">
          <span>{{ labels.rows }} {{ totalRows ? offset + 1 : 0 }}–{{ Math.min(offset + pageSize, totalRows) }} {{ labels.of }} {{ totalRows }}</span>
          <div class="flex gap-1.5">
            <button class="report-action" :disabled="loading || offset <= 0" @click="previousPage">{{ labels.previous }}</button>
            <button class="report-action" :disabled="loading || offset + pageSize >= totalRows" @click="nextPage">{{ labels.next }}</button>
          </div>
        </footer>
      </main>
    </div>
  </section>
</template>

<script setup>
import {
  computed,
  onMounted,
  ref,
  watch
} from 'vue'

import axios from '@/utils/axiosInstance'
import { language } from '@/stores/uiStore'
import { useTranslation } from '@/composables/useTranslation'

const props = defineProps({
  pageKey: { type: String, required: true },
  sourceComponentName: { type: String, required: true },
  gridComponent: { type: Object, required: true },
  config: { type: Object, required: true },
  baseConfig: { type: Object, default: () => ({}) },
  items: { type: Array, default: () => [] },
  runtimeContext: { type: Object, default: () => ({}) },
  selectedRecord: { type: Object, default: () => ({}) }
})

defineEmits(['row-selected'])

const { translate } = useTranslation()

const loading = ref(false)
const error = ref('')
const reports = ref([])
const selectedReportId = ref('')
const reportTitle = ref('')
const reportDescription = ref('')
const sharingPolicy = ref('PRIVATE')
const columns = ref([])
const filterGroups = ref([])
const shares = ref([])
const permissions = ref([])
const gridItems = ref([...props.items])
const totalRows = ref(0)
const pageSize = 100
const offset = ref(0)
const panelOpen = ref(true)
const activeTab = ref('columns')
const targetUserId = ref('')
const shareUserQuery = ref('')
const shareUsers = ref([])
const sharePermission = ref('VIEW')
const labels = ref({})
const fieldTranslations = ref({})

const tabs = [
  { id: 'columns', label: 'columns' },
  { id: 'filters', label: 'filters' },
  { id: 'sorting', label: 'sorting' },
  { id: 'sharing', label: 'sharing' }
]

const operators = [
  'EQ', 'NE', 'CONTAINS', 'STARTS_WITH', 'ENDS_WITH',
  'GT', 'GTE', 'LT', 'LTE', 'IN', 'NOT_IN',
  'BETWEEN', 'NOT_BETWEEN', 'IS_NULL', 'IS_NOT_NULL'
]

const parameters = [
  'TODAY', 'NOW', 'CURRENT_USER', 'CURRENT_PROFILE',
  'CURRENT_MONTH', 'CURRENT_YEAR'
]

const labelDictionary = {
  manager: 'report.manager',
  unsaved: 'report.unsaved',
  title: 'report.title',
  save: 'report.save',
  saveAs: 'report.saveAs',
  reset: 'report.reset',
  run: 'report.run',
  showDesigner: 'report.showDesigner',
  hideDesigner: 'report.hideDesigner',
  share: 'report.share',
  publish: 'report.publish',
  unpublish: 'report.unpublish',
  delete: 'report.delete',
  columns: 'report.columns',
  width: 'report.width',
  filters: 'report.filters',
  filterDesigner: 'report.filterDesigner',
  match: 'report.match',
  condition: 'report.condition',
  group: 'report.group',
  addGroup: 'report.addGroup',
  selectField: 'report.selectField',
  fixedValue: 'report.fixedValue',
  value: 'report.value',
  addCondition: 'report.addCondition',
  applyFilters: 'report.applyFilters',
  sorting: 'report.sorting',
  noSort: 'report.noSort',
  ascending: 'report.ascending',
  descending: 'report.descending',
  sortOrder: 'report.sortOrder',
  forcedSortNote: 'report.forcedSortNote',
  applySorting: 'report.applySorting',
  sharing: 'report.sharing',
  targetUserId: 'report.targetUserId',
  searchUsers: 'report.searchUsers',
  shareUserSearch: 'report.shareUserSearch',
  selectedShareUser: 'report.selectedShareUser',
  search: 'report.search',
  viewPermission: 'report.viewPermission',
  editPermission: 'report.editPermission',
  sharedUsers: 'report.sharedUsers',
  remove: 'report.remove',
  noShares: 'report.noShares',
  loading: 'report.loading',
  defaultTitle: 'report.defaultTitle',
  errorExecution: 'report.error.execution',
  errorLoad: 'report.error.load',
  errorSave: 'report.error.save',
  errorCopy: 'report.error.copy',
  errorDelete: 'report.error.delete',
  errorShare: 'report.error.share',
  errorUnshare: 'report.error.unshare',
  errorPublish: 'report.error.publish',
  errorUnpublish: 'report.error.unpublish',
  errorInitialize: 'report.error.initialize',
  previous: 'report.previous',
  next: 'report.next',
  rows: 'report.rows',
  of: 'report.of',
  access_owner: 'report.access.owner',
  access_sharedEdit: 'report.access.sharedEdit',
  access_sharedView: 'report.access.sharedView',
  access_publicView: 'report.access.publicView'
}

for (const operator of operators) {
  labelDictionary['operator_' + operator] = 'report.operator.' + operator
}
for (const parameter of parameters) {
  labelDictionary['parameter_' + parameter] = 'report.parameter.' + parameter
}

async function loadLabels() {
  const result = {}
  for (const [name, key] of Object.entries(labelDictionary)) {
    result[name] = await translate(key, language.value)
  }
  labels.value = result
}

async function loadFieldLabels() {
  const fieldNames = props.config?.field_order ||
    Object.keys(props.config?.fields || {})
  const result = {}

  for (const field of fieldNames) {
    const translated = await translate(field, language.value)
    if (translated && translated !== field) {
      result[field] = translated
    }
  }

  fieldTranslations.value = result
}

const defaultColumns = computed(() => {
  const order = props.config?.field_order || []
  const fields = props.config?.fields || {}

  return order
    .filter(field => fields[field]?.visible_in_grid === true)
    .map((field, index) => ({
      field_name: field,
      display_order: index + 1,
      width_px: null,
      is_visible: true,
      sort_direction: null,
      sort_order: null
    }))
})

const searchableFields = computed(() => {
  return Object.entries(props.config?.fields || {})
    .filter(([, meta]) => meta?.visible_in_search === true)
    .map(([field]) => field)
})

const sortableColumns = computed(() => {
  return columns.value.filter(column =>
    Number(props.config?.fields?.[column.field_name]?.field_sort || 0) === 1
  )
})

function hasEffectivePermission(code) {
  return permissions.value.some(item =>
    item.permission_code === code &&
    item.is_effective === true &&
    item.page_key === props.pageKey
  )
}

const canEdit = computed(() => {
  if (!selectedReportId.value) return true
  const report = reports.value.find(item => item.report_id === selectedReportId.value)

  if (report?.access_mode === 'OWNER') return true

  if (report?.sharing_policy === 'PUBLIC') {
    return hasEffectivePermission('PAGE.SUPERVISOR')
  }

  return report?.access_mode === 'SHARED_EDIT' ||
    hasEffectivePermission('REPORT.DESIGN.EDIT')
})

const canDelete = computed(() => {
  const report = reports.value.find(item => item.report_id === selectedReportId.value)
  return report?.access_mode === 'OWNER' ||
    hasEffectivePermission('REPORT.DESIGN.DELETE')
})

const canShare = computed(() => Boolean(selectedReportId.value) && canEdit.value)

const canPublish = computed(() =>
  hasEffectivePermission('PAGE.SUPERVISOR') &&
  hasEffectivePermission('REPORT.PUBLIC.PUBLISH')
)

const canSave = computed(() => !selectedReportId.value || canEdit.value)

function errorMessage(errorObject, fallback) {
  const detail = errorObject?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail.message === 'string') return detail.message
  return errorObject?.message || fallback
}

function fieldLabel(field) {
  return fieldTranslations.value[field] ||
    props.config?.translations?.[field] ||
    props.config?.fields?.[field]?.label ||
    field
}

function accessLabel(mode) {
  const key = {
    OWNER: 'access_owner',
    SHARED_EDIT: 'access_sharedEdit',
    SHARED_VIEW: 'access_sharedView',
    PUBLIC_VIEW: 'access_publicView'
  }[mode] || 'access_publicView'

  return labels.value[key] || mode
}

function buildFilterTree() {
  return filterGroups.value
    .map((group, groupIndex) => {
      const children = group.conditions
        .filter(filter => filter.field_name && filter.operator_code)
        .map((filter, index) => {
          let value = filter.value === '' ? null : filter.value

          if (['IN', 'NOT_IN', 'BETWEEN', 'NOT_BETWEEN'].includes(filter.operator_code)) {
            value = String(value || '')
              .split(',')
              .map(item => item.trim())
              .filter(Boolean)
          }

          return {
            node_type: 'CONDITION',
            field_name: filter.field_name,
            operator_code: filter.operator_code,
            value,
            parameter_code: filter.parameter_code || null,
            display_order: index + 1,
            children: []
          }
        })

      if (!children.length) return null

      return {
        node_type: 'GROUP',
        logical_operator: group.logical_operator,
        display_order: groupIndex + 1,
        children
      }
    })
    .filter(Boolean)
}

function loadFilterTree(tree) {
  const nodes = Array.isArray(tree) ? tree : []
  const groups = nodes.filter(node => node.node_type === 'GROUP')

  if (groups.length) {
    filterGroups.value = groups.map((group, groupIndex) => ({
      local_id: String(groupIndex) + '-group',
      logical_operator: group.logical_operator || 'AND',
      conditions: (group.children || [])
        .filter(node => node.node_type === 'CONDITION')
        .map((node, index) => ({
          local_id: String(groupIndex) + '-' + String(index) + '-' + (node.field_name || 'condition'),
          field_name: node.field_name || searchableFields.value[0] || '',
          operator_code: node.operator_code || 'EQ',
          value: Array.isArray(node.value) ? node.value.join(', ') : (node.value ?? ''),
          parameter_code: node.parameter_code || '',
          display_order: node.display_order || index + 1
        }))
    }))
    return
  }

  const conditions = nodes.filter(node => node.node_type === 'CONDITION')
  filterGroups.value = conditions.length
    ? [{
        local_id: 'legacy-group',
        logical_operator: 'AND',
        conditions: conditions.map((node, index) => ({
          local_id: 'legacy-' + String(index) + '-' + (node.field_name || 'condition'),
          field_name: node.field_name || searchableFields.value[0] || '',
          operator_code: node.operator_code || 'EQ',
          value: Array.isArray(node.value) ? node.value.join(', ') : (node.value ?? ''),
          parameter_code: node.parameter_code || '',
          display_order: node.display_order || index + 1
        }))
      }]
    : []
}

function addGroup() {
  filterGroups.value.push({
    local_id: String(Date.now()) + '-' + String(Math.random()),
    logical_operator: 'AND',
    conditions: [{
      local_id: String(Date.now()) + '-' + String(Math.random()),
      field_name: searchableFields.value[0] || '',
      operator_code: 'EQ',
      value: '',
      parameter_code: '',
      display_order: 1
    }]
  })
}

function removeGroup(groupIndex) {
  filterGroups.value.splice(groupIndex, 1)
}

function addFilter(groupIndex) {
  const group = filterGroups.value[groupIndex]
  if (!group) return

  group.conditions.push({
    local_id: String(Date.now()) + '-' + String(Math.random()),
    field_name: searchableFields.value[0] || '',
    operator_code: 'EQ',
    value: '',
    parameter_code: '',
    display_order: group.conditions.length + 1
  })
}

function removeFilter(groupIndex, filterIndex) {
  const group = filterGroups.value[groupIndex]
  if (!group) return
  group.conditions.splice(filterIndex, 1)
}


function updateColumns(nextColumns) {
  columns.value = nextColumns.map((column, index) => ({
    ...column,
    display_order: index + 1
  }))
}

async function resetDesign() {
  columns.value = defaultColumns.value.map(item => ({ ...item }))
  await loadDefaultSortPreference()
  filterGroups.value = []
  await runReport()
}

function reportPayload() {
  return {
    page_key: props.pageKey,
    source_component_name: props.sourceComponentName,
    report_title: reportTitle.value.trim(),
    report_desc: reportDescription.value,
    columns: columns.value,
    filters: buildFilterTree()
  }
}

async function runReport(resetPage = true) {
  if (resetPage) offset.value = 0
  loading.value = true
  error.value = ''

  try {
    const payload = reportPayload()
    const response = await axios.post('/reports/preview', {
      page_key: payload.page_key,
      source_component_name: payload.source_component_name,
      columns: payload.columns,
      filters: payload.filters,
      selected_record: props.selectedRecord || {},
      runtime_context: props.runtimeContext || {},
      limit: pageSize,
      offset: offset.value
    })
    gridItems.value = response.data?.rows || []
    totalRows.value = Number(response.data?.total || 0)
  } catch (err) {
    error.value = errorMessage(err, labels.value.errorExecution)
  } finally {
    loading.value = false
  }
}

async function previousPage() {
  if (offset.value <= 0) return
  offset.value = Math.max(0, offset.value - pageSize)
  await runReport(false)
}

async function nextPage() {
  if (offset.value + pageSize >= totalRows.value) return
  offset.value += pageSize
  await runReport(false)
}

async function loadDefaultSortPreference() {
  try {
    const response = await axios.get('/config/grid_sort', {
      params: {
        component_name: props.sourceComponentName,
        field_mode: props.config?.field_mode || 'list'
      }
    })

    const sortSpec = Array.isArray(response.data?.user_sort_spec)
      ? response.data.user_sort_spec
      : []

    const sortMap = new Map(
      sortSpec
        .filter(item =>
          ['asc', 'desc'].includes(item.direction) &&
          Number(item.field_sort_order) > 0 &&
          Number(props.config?.fields?.[item.field]?.field_sort || 0) === 1
        )
        .map(item => [item.field, item])
    )

    columns.value = columns.value.map(column => {
      const sort = sortMap.get(column.field_name)
      return {
        ...column,
        sort_direction: sort?.direction || null,
        sort_order: sort ? Number(sort.field_sort_order) : null
      }
    })
  } catch {
    columns.value = columns.value.map(column => ({
      ...column,
      sort_direction: null,
      sort_order: null
    }))
  }
}

async function loadReports() {
  const response = await axios.get('/reports/pages/' + encodeURIComponent(props.pageKey))
  reports.value = response.data || []

  if (reports.value.length) {
    await selectReport(reports.value[0].report_id)
  } else {
    selectedReportId.value = ''
    reportTitle.value = labels.value.defaultTitle
    columns.value = defaultColumns.value.map(item => ({ ...item }))
    await loadDefaultSortPreference()
    filterGroups.value = []
    sharingPolicy.value = 'PRIVATE'
    await runReport()
  }
}

async function selectReport(reportId) {
  if (!reportId) {
    selectedReportId.value = ''
    reportTitle.value = labels.value.defaultTitle
    reportDescription.value = ''
    sharingPolicy.value = 'PRIVATE'
    columns.value = defaultColumns.value.map(item => ({ ...item }))
    await loadDefaultSortPreference()
    filterGroups.value = []
    await runReport()
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await axios.get('/reports/' + reportId)
    const report = response.data

    selectedReportId.value = reportId
    reportTitle.value = report.report_title
    reportDescription.value = report.report_desc || ''
    sharingPolicy.value = report.sharing_policy
    columns.value = (report.columns || []).map(item => ({ ...item }))
    loadFilterTree(report.filters || [])
    await loadShares()
    await runReport()
  } catch (err) {
    error.value = errorMessage(err, labels.value.errorLoad)
  } finally {
    loading.value = false
  }
}

async function handleSelectReport() {
  await selectReport(selectedReportId.value)
}

async function refreshReportList() {
  const currentId = selectedReportId.value
  const response = await axios.get('/reports/pages/' + encodeURIComponent(props.pageKey))
  reports.value = response.data || []
  if (currentId && reports.value.some(item => item.report_id === currentId)) {
    selectedReportId.value = currentId
  }
}

async function saveReport() {
  if (!canSave.value) return
  loading.value = true
  error.value = ''

  try {
    if (selectedReportId.value) {
      const response = await axios.put('/reports/' + selectedReportId.value, {
        report_title: reportTitle.value.trim(),
        report_desc: reportDescription.value,
        columns: columns.value,
        filters: buildFilterTree()
      })
      await refreshReportList()
      if (response.data?.sharing_policy) sharingPolicy.value = response.data.sharing_policy
    } else {
      const response = await axios.post('/reports', reportPayload())
      selectedReportId.value = response.data.report_id
      sharingPolicy.value = 'PRIVATE'
      await refreshReportList()
    }
    await loadShares()
  } catch (err) {
    error.value = errorMessage(err, labels.value.errorSave)
  } finally {
    loading.value = false
  }
}

async function saveAs() {
  loading.value = true
  error.value = ''

  try {
    const originalTitle = reportTitle.value.trim() || labels.value.defaultTitle
    const response = await axios.post('/reports', {
      ...reportPayload(),
      report_title: originalTitle + ' Copy'
    })
    selectedReportId.value = response.data.report_id
    reportTitle.value = originalTitle + ' Copy'
    sharingPolicy.value = 'PRIVATE'
    await refreshReportList()
    await loadShares()
  } catch (err) {
    error.value = errorMessage(err, labels.value.errorCopy)
  } finally {
    loading.value = false
  }
}

async function deleteReport() {
  if (!selectedReportId.value || !canDelete.value) return
  loading.value = true
  error.value = ''

  try {
    await axios.delete('/reports/' + selectedReportId.value)
    selectedReportId.value = ''
    sharingPolicy.value = 'PRIVATE'
    reportTitle.value = labels.value.defaultTitle
    columns.value = defaultColumns.value.map(item => ({ ...item }))
    filterGroups.value = []
    shares.value = []
    await refreshReportList()
    await runReport()
  } catch (err) {
    error.value = errorMessage(err, labels.value.errorDelete)
  } finally {
    loading.value = false
  }
}

async function loadShares() {
  if (!selectedReportId.value || !canShare.value) {
    shares.value = []
    return
  }

  try {
    const response = await axios.get('/reports/' + selectedReportId.value + '/shares')
    shares.value = response.data || []
  } catch {
    shares.value = []
  }
}

async function searchShareUsers() {
  if (!selectedReportId.value || shareUserQuery.value.trim().length < 2) return
  loading.value = true
  error.value = ''

  try {
    const response = await axios.get(
      '/reports/' + selectedReportId.value + '/users/lookup',
      { params: { query: shareUserQuery.value.trim() } }
    )
    shareUsers.value = response.data || []
  } catch (err) {
    error.value = errorMessage(err, labels.value.errorShare)
  } finally {
    loading.value = false
  }
}

function selectShareUser(user) {
  targetUserId.value = user.c_user_id
  shareUserQuery.value = user.c_user_full_name || user.c_user_email
  shareUsers.value = []
}

async function shareReport() {
  if (!selectedReportId.value || !targetUserId.value.trim()) return
  loading.value = true
  error.value = ''

  try {
    await axios.post('/reports/' + selectedReportId.value + '/shares', {
      target_user_id: targetUserId.value.trim(),
      permission_level: sharePermission.value
    })
    targetUserId.value = ''
    shareUserQuery.value = ''
    shareUsers.value = []
    await loadShares()
    await refreshReportList()
  } catch (err) {
    error.value = errorMessage(err, labels.value.errorShare)
  } finally {
    loading.value = false
  }
}

async function unshareReport(userId) {
  loading.value = true
  error.value = ''

  try {
    await axios.delete('/reports/' + selectedReportId.value + '/shares/' + userId)
    await loadShares()
    await refreshReportList()
  } catch (err) {
    error.value = errorMessage(err, labels.value.errorUnshare)
  } finally {
    loading.value = false
  }
}

async function publishReport() {
  if (!selectedReportId.value || !canPublish.value) return
  loading.value = true
  error.value = ''

  try {
    await axios.post('/reports/' + selectedReportId.value + '/publish')
    sharingPolicy.value = 'PUBLIC'
    await refreshReportList()
  } catch (err) {
    error.value = errorMessage(err, labels.value.errorPublish)
  } finally {
    loading.value = false
  }
}

async function unpublishReport() {
  if (!selectedReportId.value || !canPublish.value) return
  loading.value = true
  error.value = ''

  try {
    const response = await axios.post('/reports/' + selectedReportId.value + '/unpublish')
    sharingPolicy.value = response.data?.sharing_policy || 'PRIVATE'
    await refreshReportList()
  } catch (err) {
    error.value = errorMessage(err, labels.value.errorUnpublish)
  } finally {
    loading.value = false
  }
}

function openDesigner(tab) {
  panelOpen.value = true
  activeTab.value = tab
  loadShares()
}

onMounted(async () => {
  await loadLabels()
  await loadFieldLabels()

  try {
    const response = await axios.get('/permissions/me')
    permissions.value = response.data || []
    await loadReports()
  } catch (err) {
    error.value = errorMessage(err, labels.value.errorInitialize)
  }
})

watch(language, async () => {
  await loadLabels()
  await loadFieldLabels()
})

watch(
  () => props.items,
  items => {
    if (!selectedReportId.value && Array.isArray(items)) {
      gridItems.value = [...items]
    }
  },
  { deep: true }
)

watch(
  () => props.selectedRecord,
  () => {
    runReport()
  },
  { deep: true }
)
</script>

<style scoped>
.report-action {
  border: 1px solid var(--pulsar-level-border);
  border-radius: 0.55rem;
  padding: 0.48rem 0.7rem;
  color: var(--pulsar-level-text);
  font-size: 0.68rem;
  font-weight: 600;
  background: var(--pulsar-level-surface);
  transition: background 120ms ease, border-color 120ms ease;
}
.report-action:hover {
  background: var(--pulsar-level-hover);
}
.report-action:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}
.report-primary {
  border-color: var(--pulsar-level-accent);
  color: var(--pulsar-level-accent);
}
.report-danger {
  color: #dc2626;
}
</style>
