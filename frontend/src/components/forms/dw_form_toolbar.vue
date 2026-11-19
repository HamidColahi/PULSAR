<!-- ===============================================
File: frontend/src/components/forms/dw_form_toolbar.vue
Description: Dynamic form action toolbar with metadata-driven translations
Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
=============================================== -->

<template>
  <div
    class="mb-4 flex items-center justify-end gap-1.5 border-b border-border pb-3"
  >
    <button
      v-if="
        mode === 'insert' ||
        mode === 'update'
      "
      type="button"
      @click="$emit('save')"
      :disabled="isSaving"
      class="pulsar-action pulsar-action-primary"
      :title="translations.save"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        class="h-4 w-4"
      >
        <path d="m5 12 4 4L19 6" />
      </svg>

      <span class="text-xs font-semibold">
        {{ translations.save }}
      </span>
    </button>

    <button
      v-if="mode === 'delete'"
      type="button"
      @click="$emit('delete')"
      :disabled="isSaving"
      class="pulsar-action text-red-600 dark:text-red-400"
      :title="translations.delete"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        class="h-4 w-4"
      >
        <path
          d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13"
        />
      </svg>

      <span class="text-xs font-semibold">
        {{ translations.delete }}
      </span>
    </button>

    <button
      type="button"
      @click="$emit('cancel')"
      :disabled="isSaving"
      class="pulsar-action"
      :title="translations.cancel"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        class="h-4 w-4"
      >
        <path d="M6 6l12 12M18 6 6 18" />
      </svg>

      <span class="text-xs font-semibold">
        {{ translations.cancel }}
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

defineProps({
  isSaving: {
    type: Boolean,
    default: false
  },
  mode: {
    type: String,
    default: 'view',
    validator: value =>
      [
        'insert',
        'update',
        'view',
        'delete'
      ].includes(value)
  }
})

const translations = ref({
  save: 'Save',
  cancel: 'Cancel',
  delete: 'Delete'
})

const {
  translate
} = useTranslation()

const translationKeys = Object.keys(
  translations.value
)

async function loadTranslations() {
  const currentLanguage =
    language.value

  const result = {
    ...translations.value
  }

  for (
    const key of translationKeys
  ) {
    try {
      const translated =
        await translate(
          key,
          currentLanguage
        )

      if (
        translated !== null &&
        translated !== undefined &&
        translated !== ''
      ) {
        result[key] = translated
      }
    } catch {
      // Keep the existing fallback text.
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

// Important Learning Points:
// 1. Form toolbar emits commands only.
// 2. The toolbar does not resolve primary_key.
// 3. The toolbar does not interpret where_clause.
// 4. The toolbar does not create parm[n].
// 5. Record identity remains owned by generic_page/useComponentKey.
// 6. Save, delete, and cancel remain command events.
</script>