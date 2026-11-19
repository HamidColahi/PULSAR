<!-- File: Pulsar/frontend/src/components/dw_toolbar.vue -->
<!-- Description: Metadata-driven CRUD and Renderer toolbar -->
<!-- Author: MHKolahi@gmail.com -->
<!-- In collaboration with GPT4 Chat Assistant: Bahram -->

<template>
  <div
    class="pulsar-surface flex min-h-14 items-center gap-1.5 px-2.5 py-2 select-none"
  >
    <div class="pulsar-section-label mr-1 hidden px-2 md:block">
      Actions
    </div>

    <!-- INSERT -->
    <button
      v-if="props.c_page_insert"
      type="button"
      @click="handleAction('insert')"
      class="pulsar-action"
      :title="translations.insert"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        class="h-4 w-4"
      >
        <path d="M12 5v14M5 12h14"/>
      </svg>
      <span class="hidden text-xs font-semibold sm:inline">
        {{ translations.insert }}
      </span>
    </button>

    <!-- UPDATE -->
    <button
      v-if="props.c_page_update"
      type="button"
      @click="handleAction('update')"
      :disabled="!props.hasSelection"
      class="pulsar-action disabled:cursor-not-allowed disabled:opacity-40 disabled:saturate-0"
      :title="translations.update"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        class="h-4 w-4"
      >
        <path d="m16 3 5 5L8 21H3v-5L16 3Z"/>
        <path d="m14 5 5 5"/>
      </svg>
      <span class="hidden text-xs font-semibold sm:inline">
        {{ translations.update }}
      </span>
    </button>

    <!-- VIEW -->
    <button
      v-if="props.c_page_view"
      type="button"
      @click="handleAction('view')"
      :disabled="!props.hasSelection"
      class="pulsar-action disabled:cursor-not-allowed disabled:opacity-40 disabled:saturate-0"
      :title="translations.view"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        class="h-4 w-4"
      >
        <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"/>
        <circle cx="12" cy="12" r="2.5"/>
      </svg>
      <span class="hidden text-xs font-semibold sm:inline">
        {{ translations.view }}
      </span>
    </button>

    <!-- DELETE -->
    <button
      v-if="props.c_page_delete"
      type="button"
      @click="handleAction('delete')"
      :disabled="!props.hasSelection"
      class="pulsar-action disabled:cursor-not-allowed disabled:opacity-40 disabled:saturate-0"
      :title="translations.delete"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        class="h-4 w-4"
      >
        <path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13M10 11v5M14 11v5"/>
      </svg>
      <span class="hidden text-xs font-semibold sm:inline">
        {{ translations.delete }}
      </span>
    </button>

    <!-- RENDERER -->
    <button
      v-if="props.c_page_renderer"
      type="button"
      @click="handleAction('renderer')"
      class="pulsar-action"
      :title="translations.renderer"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        class="h-4 w-4"
      >
        <rect x="3" y="4" width="18" height="16" rx="2"/>
        <path d="M7 8h10M7 12h6M7 16h4"/>
        <path d="M17 15l3 3"/>
      </svg>
      <span class="hidden text-xs font-semibold sm:inline">
        {{ translations.renderer }}
      </span>
    </button>

    <div class="flex-1"></div>

    <!-- REFRESH -->
    <button
      type="button"
      @click="handleAction('refresh')"
      class="pulsar-action"
      :title="translations.refresh"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        class="h-4 w-4"
      >
        <path d="M20 11a8 8 0 0 0-14.9-4M4 5v4h4M4 13a8 8 0 0 0 14.9 4M20 19v-4h-4"/>
      </svg>
      <span class="hidden text-xs font-semibold sm:inline">
        {{ translations.refresh }}
      </span>
    </button>
  </div>
</template>

<script setup>
import {
  ref,
  onMounted,
  watch
} from 'vue'
import {
  language
} from '@/stores/uiStore'
import {
  useTranslation
} from '@/composables/useTranslation'

const props = defineProps({
  hasSelection: {
    type: Boolean,
    default: false
  },
  c_page_view: {
    type: Boolean,
    default: true
  },
  c_page_insert: {
    type: Boolean,
    default: true
  },
  c_page_update: {
    type: Boolean,
    default: true
  },
  c_page_delete: {
    type: Boolean,
    default: true
  },
  c_page_renderer: {
    type: Boolean,
    default: true
  }
})

const emitAction = defineEmits([
  'insert',
  'update',
  'view',
  'delete',
  'renderer',
  'refresh'
])

const translations = ref({
  insert: 'insert',
  update: 'update',
  view: 'view',
  delete: 'delete',
  renderer: 'renderer',
  refresh: 'refresh'
})

const {
  translate
} = useTranslation()

async function loadTranslations() {
  const lang =
    language.value

  const result = {}

  for (
    const key of Object.keys(
      translations.value
    )
  ) {
    try {
      result[key] =
        await translate(
          key,
          lang
        )
    } catch {
      result[key] =
        translations.value[key]
    }
  }

  translations.value =
    result
}

onMounted(
  loadTranslations
)

watch(
  language,
  loadTranslations
)

function handleAction(action) {
  const validActions = [
    'insert',
    'update',
    'view',
    'delete',
    'renderer',
    'refresh'
  ]

  if (
    !validActions.includes(
      action
    )
  ) {
    console.warn(
      'dw_toolbar: Invalid action:',
      action
    )
    return
  }

  if (
    (
      action === 'update' ||
      action === 'view' ||
      action === 'delete'
    ) &&
    !props.hasSelection
  ) {
    return
  }

  emitAction(action)
}
</script>

<style scoped>
@keyframes spin-slow {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

.animate-spin-slow {
  animation: spin-slow 3s linear infinite;
}
</style>