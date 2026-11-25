<!-- ===============================================
File: frontend/src/components/reporting/ReportFilterNode.vue
Description: Recursive metadata-driven Report Generator filter node editor
Modified: 2026-11-26 (Asia/Baku)
In collaboration with GPT4 Chat Assistant: Bahram
=============================================== -->

<template>
  <div class="space-y-2 rounded-lg border border-border p-2">
    <template v-if="node.node_type === 'GROUP'">
      <div class="flex flex-wrap items-center gap-2">
        <span class="min-w-0 flex-1 text-[10px] font-semibold text-muted">
          {{ labels.group }} · {{ level }}
        </span>
        <label class="flex items-center gap-1 text-[10px] text-muted">
          <input v-model="node.is_negated" type="checkbox" :disabled="readOnly" />
          NOT
        </label>
        <select
          v-model="node.logical_operator"
          class="rounded border border-border bg-panel px-2 py-1 text-xs"
          :disabled="readOnly || !canAdvanced"
        >
          <option value="AND">AND</option>
          <option value="OR">OR</option>
        </select>
        <button class="text-xs text-red-500" :disabled="readOnly" @click="$emit('remove')">×</button>
      </div>

      <div class="space-y-2 border-l-2 border-border pl-2">
        <ReportFilterNode
          v-for="(child, index) in node.children"
          :key="child.local_id"
          :node="child"
          :level="level + 1"
          :searchable-fields="searchableFields"
          :operators="operators"
          :parameters="parameters"
          :labels="labels"
          :field-label="fieldLabel"
          :can-advanced="canAdvanced"
          :can-sql="canSql"
          :read-only="readOnly"
          @remove="node.children.splice(index, 1)"
        />
      </div>

      <div class="flex flex-wrap gap-1.5">
        <button class="report-action" :disabled="readOnly" @click="addCondition">
          {{ labels.addCondition }}
        </button>
        <button
          v-if="canAdvanced"
          class="report-action"
          :disabled="readOnly"
          @click="addGroup"
        >
          {{ labels.addNestedGroup }}
        </button>
        <button
          v-if="canSql"
          class="report-action"
          :disabled="readOnly"
          @click="addSqlFilter"
        >
          {{ labels.addSqlFilter }}
        </button>
      </div>
    </template>

    <template v-else-if="node.node_type === 'SQL'">
      <div class="flex items-center gap-2">
        <span class="min-w-0 flex-1 text-[10px] font-semibold text-muted">
          {{ labels.sqlFilter }}
        </span>
        <label class="flex items-center gap-1 text-[10px] text-muted">
          <input v-model="node.is_negated" type="checkbox" :disabled="readOnly" />
          NOT
        </label>
        <button class="text-xs text-red-500" :disabled="readOnly" @click="$emit('remove')">×</button>
      </div>
      <textarea
        v-model="node.sql_expression"
        rows="4"
        maxlength="4000"
        class="w-full rounded border border-border bg-panel px-2 py-1.5 font-mono text-[11px]"
        :placeholder="labels.sqlFilterHelp"
        :disabled="readOnly || !canSql"
      />
      <p class="text-[10px] leading-4 text-muted">{{ labels.sqlFilterHelp }}</p>
    </template>

    <template v-else>
      <div class="flex items-center gap-2">
        <span class="min-w-0 flex-1 text-[10px] font-semibold text-muted">
          {{ labels.condition }}
        </span>
        <label class="flex items-center gap-1 text-[10px] text-muted">
          <input v-model="node.is_negated" type="checkbox" :disabled="readOnly" />
          NOT
        </label>
        <button class="text-xs text-red-500" :disabled="readOnly" @click="$emit('remove')">×</button>
      </div>

      <select
        v-model="node.field_name"
        class="w-full rounded border border-border bg-panel px-2 py-1.5 text-xs"
        :disabled="readOnly"
      >
        <option value="">{{ labels.selectField }}</option>
        <option v-for="field in searchableFields" :key="field" :value="field">
          {{ fieldLabel(field) }}
        </option>
      </select>

      <select
        v-model="node.operator_code"
        class="w-full rounded border border-border bg-panel px-2 py-1.5 text-xs"
        :disabled="readOnly"
      >
        <option v-for="operator in operators" :key="operator" :value="operator">
          {{ labels['operator_' + operator] || operator }}
        </option>
      </select>

      <select
        v-model="node.parameter_code"
        class="w-full rounded border border-border bg-panel px-2 py-1.5 text-xs"
        :disabled="readOnly"
      >
        <option value="">{{ labels.fixedValue }}</option>
        <option v-for="parameter in parameters" :key="parameter" :value="parameter">
          {{ labels['parameter_' + parameter] || parameter }}
        </option>
      </select>

      <input
        v-if="!node.parameter_code && !['IS_NULL', 'IS_NOT_NULL'].includes(node.operator_code)"
        v-model="conditionValue"
        class="w-full rounded border border-border bg-panel px-2 py-1.5 text-xs"
        :placeholder="labels.value"
        :disabled="readOnly"
      />
    </template>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'

defineOptions({ name: 'ReportFilterNode' })

const props = defineProps({
  node: { type: Object, required: true },
  level: { type: Number, default: 1 },
  searchableFields: { type: Array, default: () => [] },
  operators: { type: Array, default: () => [] },
  parameters: { type: Array, default: () => [] },
  labels: { type: Object, default: () => ({}) },
  fieldLabel: { type: Function, required: true },
  canAdvanced: { type: Boolean, default: false },
  canSql: { type: Boolean, default: false },
  readOnly: { type: Boolean, default: false }
})

defineEmits(['remove'])

watch(
  () => props.node.operator_code,
  operator => {
    const listOperators = ['IN', 'NOT_IN', 'BETWEEN', 'NOT_BETWEEN']
    if (listOperators.includes(operator) && !Array.isArray(props.node.value)) {
      props.node.value = props.node.value == null || props.node.value === ''
        ? []
        : String(props.node.value).split(',').map(item => item.trim()).filter(Boolean)
    } else if (!listOperators.includes(operator) && Array.isArray(props.node.value)) {
      props.node.value = props.node.value.join(', ')
    }
  }
)

const conditionValue = computed({
  get() {
    return Array.isArray(props.node.value)
      ? props.node.value.join(', ')
      : (props.node.value ?? '')
  },
  set(value) {
    if (['IN', 'NOT_IN', 'BETWEEN', 'NOT_BETWEEN'].includes(props.node.operator_code)) {
      props.node.value = String(value)
        .split(',')
        .map(item => item.trim())
        .filter(Boolean)
    } else {
      props.node.value = value
    }
  }
})

function createId() {
  return String(Date.now()) + '-' + Math.random().toString(36).slice(2)
}

function createCondition() {
  return {
    local_id: createId(),
    node_type: 'CONDITION',
    is_negated: false,
    field_name: props.searchableFields[0] || '',
    operator_code: 'EQ',
    value: '',
    parameter_code: '',
    display_order: (props.node.children || []).length + 1,
    children: []
  }
}

function addCondition() {
  props.node.children.push(createCondition())
}

function addGroup() {
  props.node.children.push({
    local_id: createId(),
    node_type: 'GROUP',
    is_negated: false,
    logical_operator: 'AND',
    display_order: props.node.children.length + 1,
    children: [createCondition()]
  })
}

function addSqlFilter() {
  props.node.children.push({
    local_id: createId(),
    node_type: 'SQL',
    is_negated: false,
    sql_expression: '',
    display_order: props.node.children.length + 1,
    children: []
  })
}
</script>
