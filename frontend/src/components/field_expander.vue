<!-- ===============================================
File: frontend/src/components/field_expander.vue
Description: Universal large-field viewer/editor for PULSAR runtime
Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
============================================== -->

<script setup>
import {
  ref,
  computed,
  watch,
  onMounted,
  onBeforeUnmount
} from 'vue'

import {
  darkMode,
  language,
  languageMeta
} from '@/stores/uiStore'

// --------------------------------------------------
// Props
// --------------------------------------------------

const props = defineProps({
  modelValue: {
    type: [String, Number, Boolean, Object, Array],
    default: ''
  },

  label: {
    type: String,
    default: ''
  },

  mode: {
    type: String,
    default: 'view'
  },

  open: {
    type: Boolean,
    default: false
  }
})

// --------------------------------------------------
// Emits
// --------------------------------------------------

const emit = defineEmits([
  'update:modelValue',
  'update:open',
  'save',
  'close'
])

// --------------------------------------------------
// State
// --------------------------------------------------

const localValue = ref(
  normalizeValue(props.modelValue)
)

// --------------------------------------------------
// Computed
// --------------------------------------------------

const isRtl = computed(() => {
  return (
    languageMeta.value?.is_rtl === true
  )
})

const normalizedMode = computed(() => {
  return String(
    props.mode || 'view'
  ).toLowerCase()
})

const isEditable = computed(() => {
  return [
    'insert',
    'update',
    'edit'
  ].includes(
    normalizedMode.value
  )
})

const displayValue = computed(() => {
  return normalizeValue(
    props.modelValue
  )
})

// --------------------------------------------------
// Value normalization
// --------------------------------------------------

function normalizeValue(value) {
  if (
    value === null ||
    value === undefined
  ) {
    return ''
  }

  if (
    typeof value === 'object'
  ) {
    try {
      return JSON.stringify(
        value,
        null,
        2
      )
    } catch {
      return String(value)
    }
  }

  return String(value)
}

// --------------------------------------------------
// Synchronize value
// --------------------------------------------------

watch(
  () => props.modelValue,
  value => {
    localValue.value =
      normalizeValue(value)
  }
)

// --------------------------------------------------
// Open / Close
// --------------------------------------------------

function close() {
  emit(
    'update:open',
    false
  )

  emit('close')
}

function save() {
  emit(
    'update:modelValue',
    localValue.value
  )

  emit(
    'save',
    localValue.value
  )

  close()
}

// --------------------------------------------------
// Keyboard
// --------------------------------------------------

function onKeydown(event) {
  if (!props.open) {
    return
  }

  if (
    event.key === 'Escape'
  ) {
    event.preventDefault()
    close()
    return
  }

  if (
    event.ctrlKey &&
    event.key === 'Enter' &&
    isEditable.value
  ) {
    event.preventDefault()
    save()
  }
}

// --------------------------------------------------
// Lifecycle
// --------------------------------------------------

onMounted(() => {
  window.addEventListener(
    'keydown',
    onKeydown
  )
})

onBeforeUnmount(() => {
  window.removeEventListener(
    'keydown',
    onKeydown
  )
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      :class="{ dark: darkMode }"
      :dir="isRtl ? 'rtl' : 'ltr'"
      class="fixed inset-0 z-[200] flex items-center justify-center bg-slate-950/45 p-3 backdrop-blur-[2px]"
      @mousedown.self="close"
    >
      <div
        class="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-border bg-panel shadow-2xl"
        role="dialog"
        aria-modal="true"
      >
        <!-- Header -->
        <div
          class="flex shrink-0 items-center justify-between border-b border-border px-4 py-3"
        >
          <div
            class="min-w-0 text-sm font-semibold text-label"
          >
            {{ label || 'Field' }}
          </div>

          <button
            type="button"
            class="flex h-8 w-8 items-center justify-center rounded-lg text-muted transition-colors hover:bg-hover hover:text-input"
            title="Close"
            aria-label="Close"
            @click="close"
          >
            ×
          </button>
        </div>

        <!-- Content -->
        <div
          class="min-h-0 flex-1 overflow-y-auto p-4"
        >
          <textarea
            v-if="isEditable"
            v-model="localValue"
            class="min-h-[55vh] w-full resize-y rounded-xl border border-border bg-input p-3 text-sm leading-6 text-input outline-none focus:border-primary"
            spellcheck="false"
            autofocus
          />

          <div
            v-else
            class="min-h-[55vh] w-full whitespace-pre-wrap break-words rounded-xl border border-border bg-input p-3 text-sm leading-6 text-input"
          >
            {{ displayValue }}
          </div>
        </div>

        <!-- Footer -->
        <div
          class="flex shrink-0 items-center justify-end gap-2 border-t border-border px-4 py-3"
        >
          <button
            type="button"
            class="rounded-lg border border-border px-4 py-2 text-sm text-label transition-colors hover:bg-hover"
            @click="close"
          >
            {{ language === 'fa'
              ? 'بستن'
              : 'Close'
            }}
          </button>

          <button
            v-if="isEditable"
            type="button"
            class="rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors"
            style="background:var(--color-primary)"
            @click="save"
          >
            {{ language === 'fa'
              ? 'ذخیره'
              : 'Save'
            }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<!--
Important Learning Points:
1. The component is completely metadata-independent.
2. No field-specific option is required.
3. Editability is determined only by the existing field mode.
4. Mode matching is case-insensitive.
5. View/list/delete modes are rendered as read-only content.
6. Insert/update/edit modes use a large textarea editor.
7. Long content has independent vertical scrolling.
8. The component supports RTL/LTR through the existing UI language metadata.
9. Escape closes the viewer/editor.
10. Ctrl+Enter saves editable content.
11. The component is reusable by both Dynamic Grid and Dynamic Form.
-->