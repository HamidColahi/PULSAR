<!-- Pulsar/frontend/src/components/common/form_field.vue -->
<!-- Last Modified: 2026-10-08 01:55:12 (+04:00) -->

<template>
  <div class="form-field">
    <label
      v-if="label"
      class="block mb-1 text-sm text-label"
    >
      {{ label }}
    </label>

    <textarea
      v-if="resolvedType === 'textarea'"
      :value="modelValue"
      :readonly="isReadonly"
      :disabled="disabled"
      class="w-full min-h-[90px] px-3 py-2 rounded border border-border bg-panel text-label resize-y"
      @input="onInput"
      @dblclick.stop="openExpanded"
    ></textarea>

    <input
      v-else
      :type="resolvedType"
      :value="modelValue"
      :readonly="isReadonly"
      :disabled="disabled"
      class="w-full px-3 py-2 rounded border border-border bg-panel text-label"
      @input="onInput"
      @dblclick.stop="openExpanded"
    />

    <field_expander
      :open="expandedOpen"
      :model-value="expandedValue"
      :label="label"
      :mode="expandedMode"
      @update:open="expandedOpen = $event"
      @update:model-value="onExpandedInput"
      @save="onExpandedSave"
      @close="closeExpanded"
    />
  </div>
</template>

<script>
import field_expander from '@/components/field_expander.vue'

export default {
  name: 'form_field',
  components: {
    field_expander
  },
  props: {
    label: {
      type: String,
      default: ''
    },
    modelValue: {
      type: [String, Number, Boolean],
      default: ''
    },
    readonly: {
      type: Boolean,
      default: false
    },
    disabled: {
      type: Boolean,
      default: false
    },
    mod: {
      type: String,
      default: 'view'
    },
    type: {
      type: String,
      default: 'text'
    }
  },
  emits: ['update:modelValue'],
  data() {
    return {
      expandedOpen: false,
      expandedValue: ''
    }
  },
  computed: {
    isReadonly() {
      if (this.readonly || this.disabled) {
        return true
      }

      return !['insert', 'update', 'edit'].includes(
        String(this.mod).toLowerCase()
      )
    },
    expandedMode() {
      return this.isReadonly ? 'view' : 'edit'
    },
    resolvedType() {
      return this.type === 'textarea' ? 'textarea' : this.type
    }
  },
  methods: {
    onInput(event) {
      let value = event.target.value

      if (typeof this.modelValue === 'number' && value !== '') {
        const numericValue = Number(value)

        if (!Number.isNaN(numericValue)) {
          value = numericValue
        }
      }

      this.$emit('update:modelValue', value)
    },
    openExpanded() {
      this.expandedValue = this.modelValue == null
        ? ''
        : String(this.modelValue)

      this.expandedOpen = true
    },
    onExpandedInput(value) {
      this.expandedValue = value

      if (!this.isReadonly) {
        this.emitExpandedValue(value)
      }
    },
    onExpandedSave(value) {
      this.expandedValue = value
      this.emitExpandedValue(value)
      this.closeExpanded()
    },
    emitExpandedValue(value) {
      let result = value

      if (typeof this.modelValue === 'number' && value !== '') {
        const numericValue = Number(value)

        if (!Number.isNaN(numericValue)) {
          result = numericValue
        }
      }

      this.$emit('update:modelValue', result)
    },
    closeExpanded() {
      this.expandedOpen = false
    }
  }
}
</script>

<style scoped>
.form-field {
  width: 100%;
}

.form-field input:focus,
.form-field textarea:focus {
  outline: none;
}
</style>