<!--
File: Pulsar/frontend/src/components/common/function_result_viewer.vue
Description: Generic metadata-driven renderer for PostgreSQL Panel Function results.
Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
Last Modified: 2026-11-21 20:00 (Asia/Baku)
-->

<template>
  <section
    class="function-result-viewer"
    :dir="resultDirection"
  >
    <header class="report-header">
      <div class="report-heading">
        <h3 v-if="resolvedTitle" class="result-title">
          {{ resolvedTitle }}
        </h3>
      </div>

      <div class="direction-controls">
        
        <button
          type="button"
          class="direction-button"
          :class="{ 'direction-active': directionOverride === 'ltr' }"
          :aria-pressed="directionOverride === 'ltr'"
          :title="translated('pulsar.function_result.direction_ltr')"
          @click="setResultDirection('ltr')"
        >
          LTR
        </button>

        <button
          type="button"
          class="direction-button"
          :class="{ 'direction-active': directionOverride === 'rtl' }"
          :aria-pressed="directionOverride === 'rtl'"
          :title="translated('pulsar.function_result.direction_rtl')"
          @click="setResultDirection('rtl')"
        >
          RTL
        </button>

        <button
          v-if="hasPaliAnalyst"
          type="button"
          class="direction-button pali-analyst-toggle"
          :class="{ 'direction-active': paliAnalystEnabled }"
          :aria-pressed="paliAnalystEnabled"
          :title="avatarManagerDescription || translated('pulsar.pali_analyst.button')"
          :aria-label="translated('pulsar.pali_analyst.button')"
          @click="paliAnalystEnabled = !paliAnalystEnabled"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
            <circle cx="12" cy="12" r="6" />
            <circle cx="12" cy="12" r="2" />
          </svg>
          <span>{{ translated('pulsar.pali_analyst.button') }}</span>
        </button>
      </div>

      <span v-if="loading" class="result-status">
        {{ translated('pulsar.function_result.processing') }}
      </span>
    </header>

    <div
      class="result-analysis-layout"
      :class="{ 'pali-analysis-open': paliAnalystEnabled }"
    >
      <div class="result-viewport">
      <div v-if="loading" class="result-state" role="status">
        {{ translated('pulsar.function_result.loading') }}
      </div>

      <div v-else-if="error" class="result-error" role="alert">
        {{ resolvedError }}
      </div>

      <div v-else-if="isEmpty" class="result-state">
        {{ translated('pulsar.function_result.empty') }}
      </div>

      <template v-else>
        <div
          v-if="displayType === 'table'"
          class="report-section"
        >
          <div class="table-wrapper">
            <table class="result-table">
              <thead>
                <tr>
                  <th
                    v-for="column in tableColumns"
                    :key="column.field"
                  >
                    {{ resolveColumnTitle(column) }}
                  </th>
                </tr>
              </thead>

              <tbody>
                <tr
                  v-for="(row, rowIndex) in tableRows"
                  :key="rowIndex"
                >
                  <td
                    v-for="column in tableColumns"
                    :key="column.field"
                    :class="{
                      'cell-object': isComplexValue(row[column.field])
                    }"
                  >
                    <pre
                      v-if="isComplexValue(row[column.field])"
                      class="cell-json"
                    >{{ prettyJson(row[column.field]) }}</pre>

                    <span v-else>
                      {{ formatCell(row[column.field]) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div
          v-else-if="displayType === 'chart'"
          class="report-section chart-section"
        >
          <div class="chart-wrapper">
            <svg
              v-if="chartPoints.length"
              class="result-chart"
              :viewBox="`0 0 ${chartWidth} ${chartHeight}`"
              role="img"
              :aria-label="
                resolvedTitle ||
                translated('pulsar.function_result.chart_label')
              "
            >
              <line
                :x1="chartPadding"
                :y1="zeroY"
                :x2="chartWidth - chartPadding"
                :y2="zeroY"
                class="chart-axis"
              />

              <line
                :x1="chartPadding"
                :y1="chartPadding"
                :x2="chartPadding"
                :y2="chartHeight - chartPadding"
                class="chart-axis"
              />

              <polyline
                v-if="
                  chartConfig.chart_type !== 'bar' &&
                  chartPoints.length > 1
                "
                :points="chartPolyline"
                class="chart-line"
              />

              <g
                v-for="point in chartPoints"
                :key="point.index"
              >
                <rect
                  v-if="chartConfig.chart_type === 'bar'"
                  :x="point.barX - point.barWidth / 2"
                  :y="point.barY"
                  :width="point.barWidth"
                  :height="point.barHeight"
                  class="chart-bar"
                  rx="2"
                />

                <circle
                  v-else
                  :cx="point.x"
                  :cy="point.y"
                  r="4"
                  class="chart-point"
                />

                <text
                  :x="point.x"
                  :y="chartHeight - chartPadding + 18"
                  class="chart-label"
                  text-anchor="middle"
                >
                  {{ point.label }}
                </text>
              </g>
            </svg>

            <div v-else class="result-state">
              {{ translated('pulsar.function_result.chart_no_data') }}
            </div>
          </div>

          <div
            v-if="chartPoints.length"
            class="chart-legend"
          >
            <span
              v-for="point in chartPoints"
              :key="point.index"
              class="chart-legend-item"
            >
              <span class="legend-label">{{ point.label }}</span>
              <strong>{{ point.value }}</strong>
            </span>
          </div>
        </div>

        <div
          v-else-if="displayType === 'tree'"
          class="report-section tree-section"
        >
          <div
            v-if="treeConfig.show_root && treeRootLabel"
            class="tree-root-label"
          >
            {{ treeRootLabel }}
          </div>

          <div class="tree-content">
            <TreeNode
              v-for="(node, index) in treeRoots"
              :key="treeNodeKey(node, index)"
              :node="node"
              :tree-config="treeConfig"
              :depth="0"
              :expand-all="treeConfig.expand_all"
              :format-cell="formatCell"
              :translated="translated"
            />
          </div>
        </div>

        <div
          v-else-if="displayType === 'json' && isStructuredObject"
          class="report-section json-report"
        >
          <div class="report-overview">
            <div
              v-for="entry in reportEntries"
              :key="entry.key"
              class="report-field"
              :class="{
                'report-field-complex': isComplexValue(entry.value)
              }"
            >
              <div class="report-field-label">
                {{ entry.key }}
              </div>

              <div
                v-if="isComplexValue(entry.value)"
                class="report-field-content"
              >
                <pre class="nested-json">{{ prettyJson(entry.value) }}</pre>
              </div>

              <div v-else class="report-field-value">
                {{ formatCell(entry.value) }}
              </div>
            </div>
          </div>
        </div>

        <div
          v-else-if="displayType === 'json'"
          class="report-section"
        >
          <pre class="result-json">{{ prettyJson(data) }}</pre>
        </div>

        <div
          v-else-if="displayType === 'text'"
          class="report-section"
        >
          <pre class="result-text">{{ textValue }}</pre>
        </div>

        <div
          v-else-if="displayType === 'value'"
          class="report-section result-value"
        >
          {{ formatCell(data) }}
        </div>

        <div
          v-else
          class="result-error"
          role="alert"
        >
          {{ translated('pulsar.function_result.unsupported_display_type') }}
        </div>
      </template>
      </div>

      <PaliAnalystPanel
        v-if="paliAnalystEnabled"
        :model-value="true"
        :result="props.result"
        :display="props.display"
        @update:model-value="paliAnalystEnabled = $event"
      />
    </div>
  </section>
</template>

<script setup>
import {
  computed,
  defineComponent,
  h,
  ref,
  watch
} from 'vue'
import { useTranslation } from '@/composables/useTranslation'
import { languageMeta } from '@/stores/uiStore'
import PaliAnalystPanel from '@/components/tools/pali_analyst_panel.vue'

const { translate, currentLanguage } = useTranslation()

const props = defineProps({
  result: {
    type: [Object, Array, String, Number, Boolean],
    default: null
  },
  display: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    default: ''
  }
})

const paliAnalystEnabled = ref(false)

const hasPaliAnalyst = computed(() => {
  const managerId = Number(props.display?.metadata?.avatar_manager_id)
  const outputConfigId = Number(props.display?.metadata?.output_config_id)

  return Number.isInteger(managerId) &&
    managerId > 0 &&
    Number.isInteger(outputConfigId) &&
    outputConfigId > 0
})

const avatarManagerDescription = computed(() => (
  props.display?.metadata?.avatar_manager_desc || ''
))

watch(hasPaliAnalyst, enabled => {
  if (!enabled) paliAnalystEnabled.value = false
})

const SUPPORTED_DISPLAY_TYPES = new Set([
  'json',
  'table',
  'chart',
  'text',
  'value',
  'tree'
])

const chartWidth = 720
const chartHeight = 300
const chartPadding = 40

const translations = ref({})
const directionOverride = ref(null)

const rawTitle = computed(() => (
  props.title || props.display?.title || ''
))

const resolvedTitle = computed(() => {
  const title = rawTitle.value

  if (!title) return ''

  return translations.value[title] || title
})

const resultDirection = computed(() => {
  if (directionOverride.value !== null) {
    return directionOverride.value
  }

  return languageMeta.value?.is_rtl === true ? 'rtl' : 'ltr'
})

function setResultDirection(direction) {
  if (direction === 'ltr' || direction === 'rtl') {
    directionOverride.value = direction
  }
}

function resetResultDirection() {
  directionOverride.value = null
}

function inferDisplayType(value) {
  if (Array.isArray(value)) {
    return value.every(
      row => row && typeof row === 'object' && !Array.isArray(row)
    ) ? 'table' : 'json'
  }

  if (value !== null && typeof value === 'object') {
    return 'json'
  }

  if (typeof value === 'string') {
    return 'text'
  }

  return 'value'
}

const data = computed(() => {
  if (props.display && 'data' in props.display) {
    return props.display.data
  }

  return props.result
})

const displayType = computed(() => {
  const configuredType = props.display?.display_type

  if (
    typeof configuredType === 'string' &&
    SUPPORTED_DISPLAY_TYPES.has(configuredType)
  ) {
    return configuredType
  }

  if (configuredType) {
    return 'unsupported'
  }

  return inferDisplayType(data.value)
})

const isStructuredObject = computed(() => (
  data.value !== null &&
  typeof data.value === 'object' &&
  !Array.isArray(data.value)
))

function objectEntries(value) {
  if (
    value === null ||
    typeof value !== 'object' ||
    Array.isArray(value)
  ) {
    return []
  }

  return Object.entries(value).map(([key, entryValue]) => ({
    key,
    value: entryValue
  }))
}

const reportEntries = computed(() => objectEntries(data.value))

const tableRows = computed(() => {
  if (Array.isArray(data.value)) {
    return data.value.filter(
      row => row && typeof row === 'object' && !Array.isArray(row)
    )
  }

  if (data.value && typeof data.value === 'object') {
    return [data.value]
  }

  return []
})

const tableColumns = computed(() => {
  const configured = props.display?.columns

  if (Array.isArray(configured) && configured.length) {
    return configured
      .filter(column => column && column.field != null)
      .map(column => ({
        field: String(column.field),
        title: String(column.title ?? column.field)
      }))
  }

  const fields = new Set()

  tableRows.value.forEach(row => {
    Object.keys(row).forEach(field => fields.add(field))
  })

  return [...fields].map(field => ({
    field,
    title: field
  }))
})

const translationKeys = computed(() => [
  ...(rawTitle.value ? [rawTitle.value] : []),
  'pulsar.function_result.processing',
  'pulsar.function_result.loading',
  'pulsar.function_result.empty',
  'pulsar.function_result.chart_label',
  'pulsar.function_result.chart_no_data',
  'pulsar.function_result.null_value',
  'pulsar.function_result.tree_expand',
  'pulsar.function_result.tree_collapse',
  'pulsar.function_result.unsupported_display_type',
  'pulsar.function_result.direction_auto',
  'pulsar.function_result.direction_ltr',
  'pulsar.function_result.direction_rtl',
  'pulsar.common.yes',
  'pulsar.common.no',
  ...tableColumns.value.map(
    column => `pulsar.function_result.columns.${column.field}`
  )
])

async function loadTranslations() {
  const languageCode = currentLanguage.value
  const keys = [...new Set(translationKeys.value)]
  const loaded = {}

  await Promise.all(
    keys.map(async key => {
      loaded[key] = await translate(key, languageCode)
    })
  )

  if (languageCode !== currentLanguage.value) return

  translations.value = {
    ...translations.value,
    ...loaded
  }
}

function translated(key) {
  return translations.value[key] || key
}

watch(
  [translationKeys, currentLanguage],
  loadTranslations,
  { deep: true, immediate: true }
)

const chartConfig = computed(() => props.display?.chart || {})

const chartData = computed(() => {
  const rows = chartConfig.value.data

  if (Array.isArray(rows)) return rows
  if (Array.isArray(data.value)) return data.value

  if (data.value && typeof data.value === 'object') {
    return [data.value]
  }

  return []
})

const chartPoints = computed(() => {
  const rows = chartData.value
  const categoryField = chartConfig.value.category_field
  const valueField = chartConfig.value.value_field

  if (!rows.length || !categoryField || !valueField) return []

  const numericRows = rows
    .map((row, index) => {
      const rawValue = row?.[valueField]

      if (
        rawValue === null ||
        rawValue === undefined ||
        rawValue === ''
      ) {
        return null
      }

      const value = Number(rawValue)

      if (!Number.isFinite(value)) return null

      return {
        index,
        label: String(row?.[categoryField] ?? ''),
        value
      }
    })
    .filter(Boolean)

  if (!numericRows.length) return []

  const minValue = Math.min(0, ...numericRows.map(item => item.value))
  const maxValue = Math.max(0, ...numericRows.map(item => item.value))
  const valueRange = maxValue - minValue || 1

  const plotWidth = chartWidth - chartPadding * 2
  const plotHeight = chartHeight - chartPadding * 2
  const slotWidth = plotWidth / numericRows.length
  const barWidth = Math.min(36, slotWidth * 0.65)
  const zeroY = chartPadding + (maxValue / valueRange) * plotHeight

  return numericRows.map((item, index) => {
    const y =
      chartPadding +
      ((maxValue - item.value) / valueRange) * plotHeight

    const x = numericRows.length === 1
      ? chartWidth / 2
      : chartPadding + index * plotWidth / (numericRows.length - 1)

    const barX = chartPadding + slotWidth * index + slotWidth / 2

    return {
      ...item,
      x,
      y,
      barWidth,
      barY: Math.min(y, zeroY),
      barHeight: Math.max(1, Math.abs(zeroY - y)),
      barX
    }
  })
})

const zeroY = computed(() => {
  if (!chartPoints.value.length) {
    return chartHeight - chartPadding
  }

  const minValue = Math.min(
    0,
    ...chartPoints.value.map(point => point.value)
  )
  const maxValue = Math.max(
    0,
    ...chartPoints.value.map(point => point.value)
  )
  const valueRange = maxValue - minValue || 1
  const plotHeight = chartHeight - chartPadding * 2

  return chartPadding + (maxValue / valueRange) * plotHeight
})

const chartPolyline = computed(() => (
  chartPoints.value
    .map(point => `${point.x},${point.y}`)
    .join(' ')
))

const treeConfig = computed(() => props.display?.tree || {})

const treeData = computed(() => treeConfig.value.data ?? data.value)

function normalizeTreeNode(node, config, depth = 0) {
  const childrenField = config.children_field || 'children'
  const keyField = config.key_field || 'key'
  const labelField = config.label_field || 'label'

  if (!node || typeof node !== 'object' || Array.isArray(node)) {
    return {
      key: `${depth}:${String(node ?? '')}`,
      label: String(node ?? ''),
      children: [],
      value: node
    }
  }

  const normalized = {
    ...node,
    key: node[keyField] ?? `${depth}:${node[labelField] ?? 'node'}`,
    label: node[labelField] ?? node[keyField] ?? '',
    children: []
  }

  const directChildren = node[childrenField]

  if (Array.isArray(directChildren)) {
    normalized.children.push(
      ...directChildren.map(
        child => normalizeTreeNode(child, config, depth + 1)
      )
    )
  }

  return normalized
}

const treeRoots = computed(() => {
  const value = treeData.value
  const roots = Array.isArray(value)
    ? value
    : value && typeof value === 'object'
      ? [value]
      : []

  return roots.map(
    node => normalizeTreeNode(node, treeConfig.value)
  )
})

const treeRootLabel = computed(() => {
  if (!treeConfig.value.show_root) return ''

  const field = treeConfig.value.root_label_field
  const root = treeRoots.value[0]

  if (!field || !root) return ''

  return String(root[field] ?? root.label ?? '')
})

function treeNodeKey(node, index) {
  return node && typeof node === 'object' && node.key != null
    ? String(node.key)
    : index
}

const textValue = computed(() => (
  typeof data.value === 'string'
    ? data.value
    : prettyJson(data.value)
))

const isEmpty = computed(() => {
  if (displayType.value === 'unsupported') return false

  if (displayType.value === 'tree') {
    return treeRoots.value.length === 0
  }

  if (data.value === null || data.value === undefined) return true
  if (Array.isArray(data.value)) return data.value.length === 0

  return (
    typeof data.value === 'object' &&
    Object.keys(data.value).length === 0
  )
})

const resolvedError = computed(() => {
  const errorCode = props.error.trim()

  if (!errorCode) return ''

  return translations.value[errorCode] || errorCode
})

function resolveColumnTitle(column) {
  const translationKey =
    `pulsar.function_result.columns.${column.field}`

  const translatedTitle = translated(translationKey)

  return translatedTitle !== translationKey
    ? translatedTitle
    : column.title
}

function isComplexValue(value) {
  return value !== null && typeof value === 'object'
}

function prettyJson(value) {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value ?? '')
  }
}

function formatCell(value) {
  if (value === null || value === undefined) {
    return translated('pulsar.function_result.null_value')
  }

  if (typeof value === 'object') {
    return prettyJson(value)
  }

  if (typeof value === 'boolean') {
    return translated(
      value ? 'pulsar.common.yes' : 'pulsar.common.no'
    )
  }

  return String(value)
}

const TreeNode = defineComponent({
  name: 'FunctionResultTreeNode',
  props: {
    node: {
      type: [Object, Array, String, Number, Boolean],
      required: true
    },
    treeConfig: {
      type: Object,
      required: true
    },
    depth: {
      type: Number,
      default: 0
    },
    expandAll: {
      type: Boolean,
      default: false
    },
    formatCell: {
      type: Function,
      required: true
    },
    translated: {
      type: Function,
      required: true
    }
  },
  setup(nodeProps) {
    const expanded = ref(nodeProps.expandAll)

    watch(
      () => nodeProps.expandAll,
      value => {
        expanded.value = value
      }
    )

    const label = computed(() => String(nodeProps.node?.label ?? ''))

    const children = computed(() => (
      Array.isArray(nodeProps.node?.children)
        ? nodeProps.node.children
        : []
    ))

    const entries = computed(() => {
      const node = nodeProps.node

      if (!node || typeof node !== 'object' || Array.isArray(node)) {
        return []
      }

      const excluded = new Set([
        'key',
        'label',
        'children'
      ])

      const childrenField = nodeProps.treeConfig.children_field || 'children'
      const keyField = nodeProps.treeConfig.key_field || 'key'
      const labelField = nodeProps.treeConfig.label_field || 'label'

      excluded.add(childrenField)
      excluded.add(keyField)
      excluded.add(labelField)

      return Object.entries(node).filter(([key, value]) => (
        !excluded.has(key) &&
        (value === null || typeof value !== 'object')
      ))
    })

    function nodeKey(node, index) {
      return node?.key != null
        ? String(node.key)
        : `${nodeProps.depth}-${index}`
    }

    return () => h(
      'div',
      {
        class: 'tree-node',
        style: { '--tree-depth': nodeProps.depth }
      },
      [
        h('div', { class: 'tree-node-heading' }, [
          children.value.length
            ? h(
                'button',
                {
                  type: 'button',
                  class: 'tree-toggle',
                  'aria-expanded': String(expanded.value),
                  'aria-label': nodeProps.translated(
                    expanded.value
                      ? 'pulsar.function_result.tree_collapse'
                      : 'pulsar.function_result.tree_expand'
                  ),
                  onClick: () => {
                    expanded.value = !expanded.value
                  }
                },
                expanded.value ? '−' : '+'
              )
            : h('span', { class: 'tree-toggle-placeholder' }),

          h('span', { class: 'tree-node-label' }, label.value),

          ...entries.value.map(([key, value]) => h(
            'span',
            { class: 'tree-node-property', key },
            [
              h('strong', { class: 'tree-property-name' }, `${key}: `),
              h(
                'span',
                { class: 'tree-property-value' },
                nodeProps.formatCell(value)
              )
            ]
          ))
        ]),

        expanded.value && children.value.length
          ? h(
              'div',
              { class: 'tree-node-children' },
              children.value.map((child, index) => h(TreeNode, {
                key: nodeKey(child, index),
                node: child,
                treeConfig: nodeProps.treeConfig,
                depth: nodeProps.depth + 1,
                expandAll: nodeProps.expandAll,
                formatCell: nodeProps.formatCell,
                translated: nodeProps.translated
              }))
            )
          : null
      ]
    )
  }
})
</script>

<style scoped>
.function-result-viewer {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: 100%;
  min-width: 0;
  color: var(--text-primary, #1f2937);
}

.result-analysis-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1rem;
  min-width: 0;
  align-items: stretch;
}

.result-analysis-layout.pali-analysis-open {
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
}

.pali-analyst-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.pali-analyst-toggle svg {
  width: 1rem;
  height: 1rem;
  flex: 0 0 auto;
}

@media (max-width: 960px) {
  .result-analysis-layout.pali-analysis-open {
    grid-template-columns: minmax(0, 1fr);
  }
}

/* Keep the report title and direction controls outside the scrolling area. */
.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem 1rem;
  padding: 1rem 1.25rem;
  border: 1px solid var(--border-color, #dbe1ea);
  border-inline-start: 4px solid var(--chart-color, #2563eb);
  border-radius: 0.75rem;
  background: var(--surface-primary, #ffffff);
  box-shadow: 0 2px 8px rgb(15 23 42 / 4%);
}

.report-heading {
  flex: 1 1 12rem;
  min-width: 0;
}

.result-title {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 700;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.direction-controls {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.direction-button {
  padding: 0.375rem 0.625rem;
  border: 1px solid var(--border-color, #d1d5db);
  border-radius: 0.375rem;
  background: var(--surface-secondary, #f9fafb);
  color: var(--text-primary, #374151);
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition:
    background-color 120ms ease,
    color 120ms ease,
    border-color 120ms ease;
}

.direction-button:hover {
  background: var(--hover-background, #eff6ff);
}

.direction-button.direction-active {
  border-color: var(--chart-color, #2563eb);
  background: var(--chart-color, #2563eb);
  color: #ffffff;
}

.direction-button:focus-visible {
  outline: 2px solid var(--chart-color, #2563eb);
  outline-offset: 2px;
}

.result-status {
  flex: 0 0 auto;
  font-size: 0.875rem;
  color: var(--text-secondary, #6b7280);
}

/* Shared viewport for vertical and horizontal result scrolling. */
.result-viewport {
  width: 100%;
  min-width: 0;
  max-width: 100%;
  max-height: 65vh;
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  border-radius: 0.75rem;
}

.report-section {
  min-width: 0;
  padding: 1rem;
  border: 1px solid var(--border-color, #dbe1ea);
  border-radius: 0.75rem;
  background: var(--surface-primary, #ffffff);
  box-shadow: 0 2px 8px rgb(15 23 42 / 3%);
}

.result-state {
  padding: 1.5rem 1rem;
  border: 1px dashed var(--border-color, #d1d5db);
  border-radius: 0.75rem;
  text-align: center;
  color: var(--text-secondary, #6b7280);
  background: var(--surface-secondary, #f9fafb);
}

.result-error {
  padding: 1rem 1.25rem;
  border: 1px solid var(--error-color, #dc2626);
  border-radius: 0.75rem;
  color: var(--error-text, #b91c1c);
  background: var(--error-background, rgb(220 38 38 / 7%));
  overflow-wrap: anywhere;
}

/* Tables scroll horizontally inside the shared viewport. */
.table-wrapper {
  width: 100%;
  min-width: 0;
  overflow-x: auto;
  overflow-y: clip;
  border: 1px solid var(--border-color, #dbe1ea);
  border-radius: 0.625rem;
}

.result-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.875rem;
}

.result-table th,
.result-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  text-align: start;
  vertical-align: top;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.result-table th {
  background: var(--surface-secondary, #f3f4f6);
  font-weight: 700;
  color: var(--text-primary, #1f2937);
}

.result-table tbody tr {
  background: var(--surface-primary, #ffffff);
  transition: background-color 120ms ease;
}

.result-table tbody tr:nth-child(even) {
  background: var(--surface-secondary, #f9fafb);
}

.result-table tbody tr:hover {
  background: var(--hover-background, #eff6ff);
}

.result-table tbody tr:last-child td {
  border-bottom: none;
}

.cell-object {
  min-width: 12rem;
}

/* Long JSON and text use the shared viewport instead of nested scrollbars. */
.cell-json,
.result-json,
.result-text,
.nested-json {
  max-width: 100%;
  max-height: none;
  margin: 0;
  overflow: visible;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.8125rem;
  line-height: 1.65;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  direction: auto;
  text-align: start;
}

.json-report {
  padding: 1.25rem;
}

.report-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr));
  gap: 1rem;
}

.report-field {
  min-width: 0;
  padding: 1rem;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 0.625rem;
  background: var(--surface-secondary, #f9fafb);
}

.report-field-complex {
  grid-column: 1 / -1;
}

.report-field-label {
  margin-bottom: 0.5rem;
  color: var(--text-secondary, #6b7280);
  font-size: 0.8125rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.report-field-content {
  min-width: 0;
}

.nested-json {
  padding: 0.875rem;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 0.5rem;
  background: var(--surface-primary, #ffffff);
}

.report-field-value,
.result-value {
  color: var(--text-primary, #1f2937);
  font-size: 0.9375rem;
  font-weight: 500;
  line-height: 1.6;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

/* Tree output participates in the shared viewport. */
.tree-section {
  min-width: 0;
  overflow: visible;
}

.tree-root-label {
  margin-bottom: 0.75rem;
  font-weight: 700;
}

.tree-content {
  min-width: 0;
}

.tree-node {
  position: relative;
  min-width: 0;
  margin-inline-start: calc(var(--tree-depth, 0) * 1rem);
}

.tree-node-heading {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 0.5rem;
  min-width: 0;
  padding: 0.5rem 0;
}

.tree-toggle,
.tree-toggle-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 1.5rem;
  width: 1.5rem;
  height: 1.5rem;
}

.tree-toggle {
  border: 1px solid var(--border-color, #d1d5db);
  border-radius: 0.25rem;
  background: var(--surface-secondary, #f9fafb);
  cursor: pointer;
}

.tree-node-label {
  font-weight: 600;
  overflow-wrap: anywhere;
}

.tree-node-property {
  color: var(--text-secondary, #6b7280);
  overflow-wrap: anywhere;
}

.tree-property-name {
  color: var(--text-primary, #374151);
}

.tree-node-children {
  margin-inline-start: 0.75rem;
  padding-inline-start: 0.75rem;
  border-inline-start: 1px solid var(--border-color, #d1d5db);
}

.chart-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.chart-wrapper {
  width: 100%;
  min-width: 0;
  overflow: visible;
}

.result-chart {
  display: block;
  width: 100%;
  min-width: 360px;
  max-height: 360px;
}

.chart-axis {
  stroke: var(--border-color, #9ca3af);
  stroke-width: 1;
}

.chart-line {
  fill: none;
  stroke: var(--chart-color, #2563eb);
  stroke-width: 2.5;
  stroke-linejoin: round;
  stroke-linecap: round;
}

.chart-point,
.chart-bar {
  fill: var(--chart-color, #2563eb);
  stroke: var(--surface-primary, #ffffff);
  stroke-width: 1.5;
}

.chart-label {
  fill: var(--text-secondary, #6b7280);
  font-size: 10px;
}

.chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.625rem;
}

.chart-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 0.5rem;
  background: var(--surface-secondary, #f9fafb);
  font-size: 0.8125rem;
}

.legend-label {
  color: var(--text-secondary, #6b7280);
}

@media (max-width: 640px) {
  .report-header {
    align-items: flex-start;
    flex-direction: column;
    padding: 0.875rem 1rem;
  }

  .direction-controls {
    width: 100%;
  }

  .report-section,
  .json-report {
    padding: 0.75rem;
  }

  .report-overview {
    grid-template-columns: minmax(0, 1fr);
  }

  .report-field-complex {
    grid-column: auto;
  }

  .result-table th,
  .result-table td {
    padding: 0.625rem 0.75rem;
  }

  .result-viewport {
    max-height: 65vh;
  }
}

@media print {
  .function-result-viewer {
    color: #111827;
    gap: 0.75rem;
  }

  .result-viewport {
    max-width: none;
    max-height: none;
    overflow: visible;
    scrollbar-gutter: auto;
  }

  .direction-controls {
    display: none;
  }

  .report-header,
  .report-section,
  .report-field {
    box-shadow: none;
    break-inside: avoid;
    background: #ffffff;
    border-color: #d1d5db;
  }

  .report-field-complex {
    break-inside: auto;
  }

  .table-wrapper {
    overflow: visible;
  }

  .result-table th {
    background: #f3f4f6;
  }

  .cell-json,
  .result-json,
  .result-text,
  .nested-json {
    max-height: none;
    overflow: visible;
  }

  .result-chart {
    max-height: 300px;
  }
}
</style>
