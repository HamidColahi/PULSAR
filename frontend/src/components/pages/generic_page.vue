
<!--
 File: Pulsar/frontend/src/components/pages/generic_page.vue
 Description: Dynamic page runtime resolver with metadata-driven Panel Function and file handling
 Author: MHKolahi@gmail.com
 In collaboration with GPT4 Chat Assistant: Bahram
 Last Modified: 2026-11-26 12:25 (Asia/Baku)
-->
<template>
  <div
    class="pulsar-shell"
    :dir="languageMeta?.is_rtl === true ? 'rtl' : 'ltr'"
    :style="themeStyle"
  >
    <TopControls
      :pageTitleKey="pageTitleKey"
      :aiAvatarContextVariables="aiAvatarContextVariables"
      :style="themeStyle"
    />

    <div
      class="mx-auto flex h-screen w-full max-w-[1800px] flex-col px-3 pb-4 pt-[84px] sm:px-5"
    >
      <div
        v-if="pageLoading"
        class="pulsar-surface flex min-h-40 items-center justify-center text-sm text-muted"
      >
        Loading...
      </div>

      <div
        v-else-if="pageError"
        class="pulsar-surface border-red-200 p-5 text-sm text-red-600 dark:border-red-900/50"
      >
        {{ pageError }}
      </div>

      <template v-else>
        <dw_toolbar
          class="mb-2.5"
          :style="themeStyle"
          :disabled="gridLoading || !!gridError"
          :translations="gridConfig?.translations || {}"
          :hasSelection="hasSelection"
          :c_page_view="props.c_page_view"
          :c_page_insert="reportGeneratorEnabled ? false : props.c_page_insert"
          :c_page_update="reportGeneratorEnabled ? false : props.c_page_update"
          :c_page_delete="reportGeneratorEnabled ? false : props.c_page_delete"
          :c_page_renderer="reportGeneratorEnabled ? false : props.c_page_renderer"
          @insert="handleInsert"
          @update="handleUpdate"
          @view="handleView"
          @delete="handleDelete"
          @renderer="handleRenderer"
          @refresh="handleRefresh"
        />

        <div
          class="flex min-h-[calc(100vh-550px)] overflow-hidden rounded-[14px] border bg-panel shadow-sm"
          :style="surfaceStyle"
          dir="ltr"
        >
          <ContextPanel
            v-if="contextPanelId"
            :class="languageMeta?.is_rtl === true ? 'order-1' : 'order-2'"
            :style="themeStyle"
            :contextId="contextPanelId"
            :cartableKey="pageTitleKey"
            :sourceComponent="derivedGridName"
            :selectedRecord="selectedRecord"
            :parentRecordContext="parentRecordContext"
            @open-function="handleOpenFunction"
          />

          <main
            class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden p-2.5 sm:p-3"
            :class="languageMeta?.is_rtl === true ? 'order-2' : 'order-1'"
          >
            <!-- Parent Record Context -->
            <div
              v-if="parentRecordContext.length > 0"
              class="mb-2 flex shrink-0 flex-wrap items-center gap-x-2 gap-y-1 rounded-lg border border-border bg-panel px-3 py-2 text-xs"
              :dir="languageMeta?.is_rtl === true ? 'rtl' : 'ltr'"
              role="status"
            >
              <span class="font-semibold text-primary">
                {{ parentRecordTitle }}:
              </span>

              <template
                v-for="(parent, parentIndex) in parentRecordContext"
                :key="`${parent.component_name || 'parent'}-${parentIndex}`"
              >
                <span
                  v-if="parentIndex > 0"
                  class="text-muted"
                >
                  |
                </span>

                <span
                  v-for="field in parent.fields"
                  :key="`${parentIndex}-${field}`"
                  class="whitespace-nowrap"
                >
                  <span class="font-medium text-muted">
                    {{ parent.fieldLabels?.[field] || field }}
                  </span>

                  <span class="mx-1">=</span>

                  <span class="font-semibold">
                    {{ parent.values?.[field] ?? '' }}
                  </span>
                </span>
              </template>
            </div>

            <ReportGenerator
              ref="reportGeneratorRef"
              v-if="reportGeneratorEnabled && gridConfig"
              :style="themeStyle"
              :page-key="props.pageTitleKey"
              :source-component-name="derivedGridName"
              :grid-component="gridComponent"
              :config="gridRuntimeConfig"
              :page-config="reportPageConfig"
              :base-config="gridBase"
              :items="records"
              :runtime-context="props.runtimeContext"
              :selected-record="navigationRecord"
              @row-selected="handleRowSelected"
            />

            <component
              v-else-if="gridConfig"
              :is="gridComponent"
              :style="themeStyle"
              :config="gridRuntimeConfig"
              :base-config="gridBase"
              :items="records"
              @row-selected="handleRowSelected"
            />
          </main>
        </div>
      </template>
    </div>

    <Teleport to="body">
      <div
        v-if="showForm"
        class="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/45 p-3 backdrop-blur-[2px]"
      >
        <div
          class="max-h-[92vh] w-full max-w-6xl overflow-y-auto rounded-2xl border border-border bg-panel p-2 shadow-2xl sm:p-3"
          :style="surfaceStyle"
        >
          <div
            v-if="formError"
            class="mb-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-400"
            :dir="languageMeta?.is_rtl === true ? 'rtl' : 'ltr'"
          >
            {{ formError }}
          </div>

          <component
            v-if="showForm && (formMode === 'insert' || selectedRecord)"
            :is="formComponent"
            :style="themeStyle"
            :config="activeFormConfig"
            :modelValue="selectedRecord"
            :mode="formMode"
            :componentName="derivedFormName"
            @save="onFormSave"
            @delete="onFormDelete"
            @download-file="onFormDownload"
            @cancel="closeForm"
          />
        </div>
      </div>
    </Teleport>
  </div>

  <Teleport to="body">
    <div
      v-if="showPanelFunctionDialog"
      class="fixed inset-0 z-[110] flex items-center justify-center bg-slate-950/50 p-3 backdrop-blur-[2px]"
      :dir="languageMeta?.is_rtl === true ? 'rtl' : 'ltr'"
      role="presentation"
    >
      <section
        class="flex max-h-[90vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl border border-border bg-panel shadow-2xl"
        :style="surfaceStyle"
        role="dialog"
        aria-modal="true"
        aria-label="Panel Function Result"
      >
        <header
          class="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-3"
        >
          <h2 class="text-sm font-semibold">
            {{ panelFunctionResult?.display?.title || 'Panel Function Result' }}
          </h2>

          <button
            type="button"
            class="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-slate-800"
            :disabled="panelFunctionLoading"
            @click="resetPanelFunction"
          >
            Close
          </button>
        </header>

        <div class="min-h-0 flex-1 overflow-auto p-4">
          <div
            v-if="panelFunctionLoading"
            class="rounded-lg border border-border bg-panel px-3 py-4 text-sm text-muted"
            role="status"
            aria-live="polite"
          >
            Executing Panel Function...
          </div>

          <div
            v-else-if="panelFunctionError"
            class="rounded-lg border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-600 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-400"
            role="alert"
          >
            {{ panelFunctionError }}
          </div>

          <FunctionResultViewer
            v-else-if="panelFunctionResult !== null"
            :result="panelFunctionResult?.result ?? null"
            :display="panelFunctionResult?.display ?? null"
            :loading="false"
            :error="null"
            :title="panelFunctionResult?.display?.title || 'Panel Function Result'"
          />
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import {
  ref,
  watch,
  onMounted,
  computed
} from 'vue'

import {
  useRoute
} from 'vue-router'

import axios from '@/utils/axiosInstance'

import {
  language,
  languageMeta
} from '@/stores/uiStore'

import TopControls from '@/components/top_controls.vue'
import dw_toolbar from '@/components/dw_toolbar.vue'
import ContextPanel from '@/components/panels/context_panel.vue'
import FunctionResultViewer from '@/components/common/function_result_viewer.vue'
import ReportGenerator from '@/components/reporting/ReportGenerator.vue'

import {
  useTranslation
} from '@/composables/useTranslation'

import {
  useComponentBase
} from '@/composables/useComponentBase.js'

import {
  useComponentConfig
} from '@/composables/useComponentConfig.js'

import {
  useComponentData
} from '@/composables/useComponentData.js'

import {
  useComponentWhere
} from '@/composables/useComponentWhere.js'

import {
  useComponentKey
} from '@/composables/useComponentKey.js'

import {
  usePageNavigation
} from '@/composables/usePageNavigation.js'

import {
  usePageLevelTheme
} from '@/composables/usePageLevelTheme.js'

import {
  usePanelFunction
} from '@/composables/usePanelFunction.js'

const showPanelFunctionDialog = ref(false)

const props = defineProps({
  c_page_view: { type: Boolean, default: true },
  c_page_insert: { type: Boolean, default: true },
  c_page_update: { type: Boolean, default: true },
  c_page_delete: { type: Boolean, default: true },
  c_page_renderer: { type: Boolean, default: true },
  gridComponent: { type: Object, required: true },
  formComponent: { type: Object, required: true },
  pageTitleKey: { type: String, default: null },
  pageLevel: { type: String, default: null },
  gridName: { type: String, default: null },
  gridFieldMode: { type: String, default: 'list' },
  formName: { type: String, default: null },
  formFieldMode: { type: String, default: 'view' },
  where_clause: { type: [Object, String], default: () => ({}) },
  runtimeContext: { type: Object, default: () => ({}) },
  visualLevel: { type: Number, default: null }
})

const route = useRoute()

const {
  currentLevel
} = usePageNavigation()

const visualLevel = computed(() => currentLevel.value)

const {
  themeStyle,
  surfaceStyle
} = usePageLevelTheme(visualLevel)

const {
  translate
} = useTranslation()

const pageLoading = ref(false)
const pageError = ref(null)
const reportGeneratorEnabled = ref(false)
const reportPageConfig = ref({ is_enabled: false, allow_sharing: true, allow_public: false })
const formError = ref(null)

const {
  loading: panelFunctionLoading,
  error: panelFunctionError,
  result: panelFunctionResult,
  executeFunction,
  reset: resetPanelFunctionState
} = usePanelFunction()

async function handleOpenFunction(payload) {
  if (panelFunctionLoading.value) return

  resetPanelFunctionState()
  showPanelFunctionDialog.value = true

  try {
    await executeFunction(payload)
  } catch (err) {
    console.error(
      'generic_page: Panel Function execution failed',
      err
    )
  }
}

function resetPanelFunction() {
  if (panelFunctionLoading.value) return

  showPanelFunctionDialog.value = false
  resetPanelFunctionState()
}

const navigationRecord = ref(null)
const parentRecordContext = ref([])

const parentSourceComponent = computed(() => {
  return props.runtimeContext?.source_component || null
})

const parentRecordTitle = ref('Parent Record')

async function translateParentRecordContext() {
  parentRecordTitle.value = await translate(
    'parent_record',
    language.value,
    'Default'
  )

  if (!parentRecordTitle.value || parentRecordTitle.value === 'parent_record') {
    parentRecordTitle.value = await translate(
      'parent_record',
      language.value,
      'DefaultGrid'
    )
  }

  for (const parent of parentRecordContext.value) {
    const labels = {}

    for (const field of parent.fields || []) {
      const translated = await translate(
        field,
        language.value,
        parent.field_labels_context || 'DefaultGrid'
      )

      labels[field] = translated && translated !== field
        ? translated
        : field
    }

    parent.fieldLabels = labels
  }
}

function restoreParentRecordContext() {
  const raw = props.runtimeContext?.parent_record_context

  if (!Array.isArray(raw)) {
    parentRecordContext.value = []
    return
  }

  parentRecordContext.value = raw
    .filter(item =>
      item &&
      Array.isArray(item.fields) &&
      item.fields.length > 0 &&
      item.values &&
      typeof item.values === 'object'
    )
    .map(item => ({
      component_name: item.component_name || null,
      fields: [...item.fields],
      values: { ...item.values },
      field_labels_context: item.field_labels_context || 'DefaultGrid',
      fieldLabels: {}
    }))
}

async function appendCurrentParentRecord() {
  if (!navigationRecord.value || !parentSourceComponent.value) return

  try {
    const result = await resolveKey({
      component_name: parentSourceComponent.value,
      field_mode: 'list',
      record: navigationRecord.value
    })

    if (!result?.fields?.length || !result?.values) return

    parentRecordContext.value = [
      ...parentRecordContext.value,
      {
        component_name: parentSourceComponent.value,
        fields: [...result.fields],
        values: { ...result.values },
        field_labels_context: 'DefaultGrid',
        fieldLabels: {}
      }
    ]

    await translateParentRecordContext()
  } catch (err) {
    console.error('generic_page: parent record key resolution failed', err)
  }
}

const selectedRecord = ref(null)
const selectedId = ref(null)
const reportGeneratorRef = ref(null)
const showForm = ref(false)
const formMode = ref('view')

const hasSelection = computed(() => {
  return selectedId.value !== null &&
    selectedId.value !== undefined &&
    selectedId.value !== ''
})

const contextPanelId = computed(() => {
  return props.runtimeContext?.context_id ||
    props.runtimeContext?.id ||
    null
})

function deriveComponentName(sfcObj) {
  return sfcObj?.__name ||
    sfcObj?.name ||
    sfcObj?.displayName ||
    null
}

const derivedGridName = props.gridName || deriveComponentName(props.gridComponent)
const derivedFormName = props.formName || deriveComponentName(props.formComponent)

const aiAvatarContextVariables = computed(() => {
  return {
    schema_version: 1,

    page: {
      page_key: props.pageTitleKey || null,
      page_title_key: props.pageTitleKey || null,
      grid_component: derivedGridName || null,
      form_component: derivedFormName || null,
      context_id: contextPanelId.value || null
    },

    navigation: {
      parent_component: parentSourceComponent.value || null,
      parent_record_context: parentRecordContext.value.map(parent => ({
        component_name: parent.component_name || null,
        fields: Array.isArray(parent.fields)
          ? parent.fields.filter(
              field => typeof field === 'string'
            )
          : [],
        field_labels: {
          ...(parent.fieldLabels || {})
        }
      }))
    },

    selected_record: selectedRecord.value &&
      typeof selectedRecord.value === 'object' &&
      !Array.isArray(selectedRecord.value)
      ? { ...selectedRecord.value }
      : null,

    ui_state: {
      page_loading: pageLoading.value,
      page_error: Boolean(pageError.value),
      grid_loading: gridLoading.value,
      grid_error: Boolean(gridError.value),
      form_visible: showForm.value,
      form_mode: formMode.value,
      has_selection: hasSelection.value
    },

    grid: {
      component: derivedGridName || null,
      field_mode: props.gridFieldMode || null,
      configuration_available: Boolean(gridConfig.value),
      record_count: Array.isArray(records.value)
        ? records.value.length
        : 0
    }
  }
})

const gridApi = useComponentData(derivedGridName || '', 'dw', props.gridFieldMode)
const formApi = useComponentData(derivedFormName || '', 'dw', props.formFieldMode)

const {
  resolveWhere
} = useComponentWhere()

const {
  resolveKey
} = useComponentKey()

const {
  records,
  loading: gridLoading,
  error: gridError,
  loadData: loadGridData
} = gridApi

const {
  loadData: loadFormData
} = formApi

const {
  baseConfig: gridBase,
  fetchBase: fetchGridBase
} = useComponentBase(derivedGridName || '', props.gridFieldMode)

const {
  config: gridConfig,
  fetchConfig: fetchGridConfig
} = useComponentConfig(derivedGridName || '', props.gridFieldMode)

const formBaseApis = {
  insert: useComponentBase(derivedFormName || '', 'insert'),
  view: useComponentBase(derivedFormName || '', 'view'),
  update: useComponentBase(derivedFormName || '', 'update'),
  delete: useComponentBase(derivedFormName || '', 'delete')
}

const formConfigApis = {
  insert: useComponentConfig(derivedFormName || '', 'insert'),
  view: useComponentConfig(derivedFormName || '', 'view'),
  update: useComponentConfig(derivedFormName || '', 'update'),
  delete: useComponentConfig(derivedFormName || '', 'delete')
}

const gridRuntimeConfig = computed(() => gridConfig.value || {})

const activeFormConfig = computed(() => {
  return formConfigApis[formMode.value]?.config?.value ||
    formConfigApis.view?.config?.value ||
    {}
})

async function loadFormModeConfig(mode) {
  const baseApi = formBaseApis[mode] || formBaseApis.view
  const configApi = formConfigApis[mode] || formConfigApis.view

  if (baseApi?.fetchBase) await baseApi.fetchBase()
  if (configApi?.fetchConfig) await configApi.fetchConfig()
}

function cleanObject(obj) {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return {}

  return Object.fromEntries(
    Object.entries(obj).filter(([, value]) =>
      value !== null &&
      value !== undefined &&
      value !== ''
    )
  )
}

function buildQueryParams(filters = {}) {
  return Object.fromEntries(
    Object.entries(cleanObject(filters)).map(([field, value]) => [
      `where_clause[${field}]`,
      value
    ])
  )
}

async function resolveWhereFilters(
  componentName,
  fieldMode,
  selectedRecordContext = null
) {
  const result = await resolveWhere({
    component_name: componentName,
    field_mode: fieldMode,
    selected_record: selectedRecordContext || navigationRecord.value || {},
    runtime_context: props.runtimeContext || {}
  })

  return result?.filters || {}
}

async function buildFormQueryParams() {
  const filters = await resolveWhereFilters(
    derivedFormName,
    formMode.value,
    selectedRecord.value
  )

  return buildQueryParams(filters)
}

async function loadReportPageConfiguration() {
  const response = await axios.get(
    '/reports/pages/' + encodeURIComponent(props.pageTitleKey) + '/configuration'
  )
  reportPageConfig.value = response.data || { is_enabled: false, allow_sharing: true, allow_public: false }
  reportGeneratorEnabled.value = reportPageConfig.value.is_enabled === true
}

async function loadRecords(options = {}) {
  if (reportGeneratorEnabled.value) {
    return []
  }

  const filters = options.filters || {}

  const resolvedFilters = await resolveWhereFilters(
    derivedGridName,
    props.gridFieldMode,
    navigationRecord.value
  )

  const finalQuery = buildQueryParams({
    ...resolvedFilters,
    ...filters
  })

  try {
    return await loadGridData({
      mode: 'list',
      params: finalQuery
    })
  } catch (err) {
    console.error('generic_page: loadRecords error', err)
    throw err
  }
}

async function resolveRecordIdentity(
  record,
  componentName = derivedGridName,
  fieldMode = 'list'
) {
  if (!record) {
    selectedId.value = null
    return null
  }

  const result = await resolveKey({
    component_name: componentName,
    field_mode: fieldMode,
    record
  })

  selectedId.value = result?.identity || null
  return result
}

async function handleRowSelected(row) {
  selectedRecord.value = row || null
  formError.value = null

  if (!row) {
    selectedId.value = null
    return
  }

  try {
    await resolveRecordIdentity(row, derivedGridName, props.gridFieldMode)
  } catch (err) {
    selectedId.value = null
    console.error('generic_page: selected record identity resolution failed', err)
  }
}

async function buildFormRecordIdentity(record) {
  if (!record) return null

  const result = await resolveKey({
    component_name: derivedFormName,
    field_mode: formMode.value,
    record
  })

  return result?.identity || null
}

function restoreSelectedRecord() {
  const raw = route.query?.selected_record

  if (!raw) {
    navigationRecord.value = null
    parentRecordContext.value = []
    return
  }

  try {
    const parsed = JSON.parse(String(raw))

    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      navigationRecord.value = { ...parsed }
      return
    }

    navigationRecord.value = null
    parentRecordContext.value = []
  } catch (err) {
    console.error('generic_page: invalid selected_record route data', err)
    navigationRecord.value = null
    parentRecordContext.value = []
  }
}

async function openForm(mode, record = null) {
  formMode.value = mode
  formError.value = null

  await loadFormModeConfig(mode)

  if (mode === 'insert') {
    selectedRecord.value = {}
    selectedId.value = null
    showForm.value = true
    return
  }

  if (!hasSelection.value) {
    console.warn('generic_page: form requested without selected grid record')
    return
  }

  const targetRecord = record || selectedRecord.value

  if (!targetRecord) {
    console.warn('generic_page: form requested without target record')
    return
  }

  selectedRecord.value = { ...targetRecord }

  try {
    selectedId.value = await buildFormRecordIdentity(selectedRecord.value)
  } catch (err) {
    console.error('generic_page: record identity resolution failed', err)
    return
  }

  showForm.value = true
}

async function onFormSave(formData) {
  const data = typeof FormData !== 'undefined' && formData instanceof FormData
    ? formData
    : { ...(formData || {}) }

  formError.value = null

  try {
    let result = null

    if (formMode.value === 'insert') {
      result = await loadFormData({
        mode: 'insert',
        payload: data,
        params: await buildFormQueryParams()
      })
    } else if (formMode.value === 'update') {
      const id = selectedId.value

      if (id === null || id === undefined || id === '') {
        throw new Error('Primary key identity is required for update')
      }

      result = await loadFormData({
        mode: 'update',
        id,
        payload: data,
        params: await buildFormQueryParams()
      })
    } else {
      return
    }

    const savedRecord = result?.item || result?.data || result || null
    showForm.value = false

    if (savedRecord) {
      selectedRecord.value = { ...savedRecord }

      try {
        selectedId.value = await buildFormRecordIdentity(selectedRecord.value)
      } catch (err) {
        console.error('generic_page: saved record identity resolution failed', err)
        selectedId.value = null
      }
    } else {
      selectedRecord.value = null
      selectedId.value = null
    }

    await loadRecords()
  } catch (err) {
    console.error('generic_page: save failed', err)

    const messageKey = err?.response?.data?.detail?.message_key

    if (messageKey) {
      formError.value = await translate(messageKey, language.value)
    } else {
      formError.value = err?.response?.data?.detail ||
        err?.message ||
        'Component data request failed'
    }
  }
}

async function resolveDownloadError(err) {
  let responseData = err?.response?.data

  if (responseData instanceof Blob) {
    const text = await responseData.text()

    try {
      responseData = JSON.parse(text)
    } catch {
      return text || err?.message || 'File download failed'
    }
  }

  const detail = responseData?.detail

  if (detail?.message_key) {
    return await translate(detail.message_key, language.value)
  }

  if (typeof detail === 'string') {
    return detail
  }

  return err?.message || 'File download failed'
}

async function onFormDownload(fieldName) {
  formError.value = null

  try {
    if (typeof fieldName !== 'string' || !fieldName.trim()) {
      throw new Error('File field name is required')
    }

    let id = selectedId.value

    if (id === null || id === undefined || id === '') {
      id = await buildFormRecordIdentity(selectedRecord.value)
    }

    if (id === null || id === undefined || id === '') {
      throw new Error('Primary key identity is required for file download')
    }

    if (typeof formApi.downloadFile !== 'function') {
      throw new Error('File download is not available in useComponentData')
    }

    const file = await formApi.downloadFile({
      id,
      fieldName,
      params: await buildFormQueryParams()
    })

    if (!(file?.blob instanceof Blob)) {
      throw new Error('The server returned an invalid file response')
    }

    const objectUrl = URL.createObjectURL(file.blob)
    const downloadLink = document.createElement('a')

    downloadLink.href = objectUrl
    downloadLink.download = file.filename || fieldName
    downloadLink.style.display = 'none'

    document.body.appendChild(downloadLink)
    downloadLink.click()
    document.body.removeChild(downloadLink)

    window.setTimeout(() => {
      URL.revokeObjectURL(objectUrl)
    }, 1000)
  } catch (err) {
    console.error('generic_page: file download failed', err)
    formError.value = await resolveDownloadError(err)
  }
}

async function onFormDelete(deletedId) {
  const id = deletedId || selectedId.value
  formError.value = null

  if (id === null || id === undefined || id === '') {
    formError.value = await translate('record_identity_required', language.value)
    return
  }

  try {
    await loadFormData({
      mode: 'delete',
      id,
      params: await buildFormQueryParams()
    })

    await loadRecords()
    showForm.value = false
    selectedRecord.value = null
    selectedId.value = null
  } catch (err) {
    const messageKey = err?.response?.data?.detail?.message_key

    if (messageKey) {
      formError.value = await translate(messageKey, language.value)
    } else {
      formError.value = err?.response?.data?.detail ||
        err?.message ||
        'Component data request failed'
    }
  }
}

function closeForm() {
  formError.value = null
  showForm.value = false
}

function handleInsert() {
  openForm('insert')
}

function handleUpdate() {
  if (!hasSelection.value) return
  openForm('update', selectedRecord.value)
}

function handleView() {
  if (!hasSelection.value) return
  openForm('view', selectedRecord.value)
}

function handleDelete() {
  if (!hasSelection.value) return
  openForm('delete', selectedRecord.value)
}

function handleRenderer() {
  // Renderer hook reserved for future metadata-driven renderer behavior.
}

async function handleRefresh() {
  try {
    if (reportGeneratorEnabled.value) {
      await reportGeneratorRef.value?.runReport()
      return
    }

    await loadRecords()
  } catch (err) {
    console.error('generic_page: refresh failed', err)
  }
}

async function initializePage() {
  pageLoading.value = true
  pageError.value = null

  try {
    if (!derivedGridName) throw new Error('Grid component name is not available')

    restoreSelectedRecord()
    restoreParentRecordContext()
    await appendCurrentParentRecord()
    await translateParentRecordContext()

    selectedRecord.value = null
    selectedId.value = null

    await fetchGridBase()
    await fetchGridConfig()
    await loadReportPageConfiguration()

    if (!reportGeneratorEnabled.value) {
      if (!derivedFormName) throw new Error('Form component name is not available')
      await formBaseApis.view.fetchBase()
      await formConfigApis.view.fetchConfig()
      await loadRecords()
    }
  } catch (err) {
    console.error('generic_page: initialization failed', err)
    pageError.value = err?.message || 'Failed to initialize page'
  } finally {
    pageLoading.value = false
  }
}

onMounted(initializePage)

watch(
  () => route.query?.selected_record,
  async () => {
    restoreSelectedRecord()
    restoreParentRecordContext()
    await appendCurrentParentRecord()
    await translateParentRecordContext()

    selectedRecord.value = null
    selectedId.value = null
    showForm.value = false
    formError.value = null

    if (!pageLoading.value && !reportGeneratorEnabled.value) {
      try {
        await loadRecords()
      } catch (err) {
        console.error('generic_page: selected record scope reload failed', err)
      }
    }
  }
)

watch(language, async () => {
  await translateParentRecordContext()

  if (!pageLoading.value && !reportGeneratorEnabled.value) {
    try {
      await loadRecords()
    } catch (err) {
      console.error('generic_page: language reload failed', err)
    }
  }
})

// Important Learning Points:
// 1. generic_page coordinates dynamic Grid, Form, ContextPanel, and Panel Function execution.
// 2. navigationRecord is the source record received from the parent page.
// 3. selectedRecord belongs exclusively to the current target Grid.
// 4. ContextPanel receives only the current Grid selectedRecord.
// 5. ContextPanel receives derivedGridName as sourceComponent metadata.
// 6. sourceComponent identifies the navigation source component only.
// 7. sourceComponent is not interpreted as a primary-key definition.
// 8. Parent Record identity is resolved through useComponentKey.
// 9. Parent Record Context is a navigation chain independent of target Grid selection.
// 10. route.selected_record never becomes the current Grid selection.
// 11. navigationRecord is used by metadata-driven where resolution.
// 12. Target Grid selection is established only by handleRowSelected.
// 13. Target Grid selection controls ContextPanel button availability.
// 14. Target Grid selection controls CRUD availability.
// 15. Record identity is resolved only after target Grid selection.
// 16. Record identity is resolved through useComponentKey.
// 17. Simple and composite primary-key semantics belong in component_key.py.
// 18. generic_page does not interpret where_clause.
// 19. where_clause resolution belongs to useComponentWhere/component_where.py.
// 20. selected_record and runtime_context remain separate contexts.
// 21. parent_record_context is navigation metadata and not CRUD identity.
// 22. profile_id remains part of the authenticated runtime context.
// 23. profile_id is never converted into parm[n].
// 24. Form query parameters are converted to where_clause[field] transport.
// 25. CRUD record identity remains an opaque value supplied by useComponentKey.
// 26. Dynamic pages remain metadata-driven.
// 27. No table-specific primary-key fields are hard-coded here.
// 28. Parent Record title and primary-key field labels use the translation dictionary.
// 29. Parent Record visual alignment follows the active page language direction.
// 30. Visual Level Theme is independent from page_type.
// 31. generic_page consumes Theme tokens and does not define the palette.
// 32. Navigation level is resolved from usePageNavigation as the single runtime source.
// 33. Visual theme level is independent from selectedRecord, navigationRecord, runtime_context, and page_type.
// 34. generic_page does not calculate or mutate navigation depth.
// 35. Delete business-rule errors are translated and displayed in the active Form.
// 36. Backend business errors remain authoritative and are identified by message_key.
// 37. generic_page does not interpret fn_has_child or child-record semantics.
// 38. parentRecordContext is initialized as an empty reactive array before template rendering.
// 39. Panel Function execution is delegated to usePanelFunction.
// 40. Panel Function receives its function name, Cartable key, context, and selected record from ContextPanel.
// 41. Panel Function results are rendered by the metadata-driven FunctionResultViewer.
// 42. Panel Function errors and loading state are surfaced independently of Form and Grid state.
// 43. Backend authorization and validation remain mandatory for Panel Function execution.
// 44. The /functions/execute endpoint must exist and be verified in the Backend.
// 45. generic_page does not execute arbitrary frontend code from Panel Function metadata.
// 46. ParentRecordContext is rendered above the current Grid.
// 47. ParentRecordContext presentation consumes the existing navigation context without resolving identity independently.
// 48. FormData payloads are passed to useComponentData without object spreading.
// 49. File download requests use the opaque record identity resolved by useComponentKey.
// 50. File transport and Blob handling belong to useComponentData, not generic_page.
// 51. File field names are supplied by the metadata-driven Form component.
// 52. generic_page does not hard-code binary database fields or table names.
</script>

<style scoped>
/* Visual Level Theme is provided by usePageLevelTheme(). */
</style>
