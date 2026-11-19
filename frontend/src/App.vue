<!-- ===============================================
File: frontend/src/App.vue
Description: Application shell, global UI initialization, and persistent AI Avatar host
Change Date: 2026-11-19 11:56; Timezone: Asia/Baku
Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
=============================================== -->

<template>
  <div
    :class="[
      $colorMode,
      'pulsar-shell min-h-screen font-sans transition-colors duration-200'
    ]"
  >
    <router-view />
  </div>

  <AIAvatarPanel
    :open="aiAvatarWindow.isOpen.value"
    :definition-code="aiAvatarWindow.definitionCode.value"
    :context-variables="aiAvatarWindow.contextVariables.value"
    @close="aiAvatarWindow.close()"
  />
</template>

<script setup>
import {
  computed,
  provide,
  reactive,
  watchEffect
} from 'vue'

import {
  darkMode,
  languageMeta,
  toggleDarkMode
} from '@/stores/uiStore.js'

import {
  useLanguages
} from '@/composables/useLanguages.js'

import axiosInstance from '@/utils/axiosInstance'

import AIAvatarPanel from '@/components/ai_avatar/AIAvatarPanel.vue'


// --------------------------------------------------
// Global AI Avatar Window State
// --------------------------------------------------

const aiAvatarWindow = reactive({
  isOpen: { value: false },
  definitionCode: { value: 'PULSAR_AVATAR' },
  contextVariables: { value: {} },

  open() {
    this.isOpen.value = true
  },

  close() {
    this.isOpen.value = false
  },

  toggle() {
    this.isOpen.value = !this.isOpen.value
  },

  setContext(contextVariables) {
    this.contextVariables.value =
      contextVariables && typeof contextVariables === 'object'
        ? contextVariables
        : {}
  },

  setDefinitionCode(definitionCode) {
    if (
      typeof definitionCode === 'string' &&
      definitionCode.trim()
    ) {
      this.definitionCode.value = definitionCode.trim()
    }
  }
})

provide('aiAvatarWindow', aiAvatarWindow)


// --------------------------------------------------
// Source Trace Runtime
// --------------------------------------------------

async function sourceTraceRunner(options = {}) {
  const payload = {
    topic: options.topic,
    max_nodes: options.max_nodes ?? 160,

    scope: options.scope ?? [
      'frontend',
      'backend',
      'database'
    ],

    relations: options.relations ?? [
      'calls',
      'imports',
      'api',
      'references',
      'sql'
    ],

    depth: options.depth ?? 3
  }

  return axiosInstance.post(
    '/source-trace/topic',
    payload
  )
}

provide('sourceTraceRunner', sourceTraceRunner)


// --------------------------------------------------
// Language Runtime
// --------------------------------------------------

const {
  fetchLanguages
} = useLanguages()

fetchLanguages()


// --------------------------------------------------
// Global Language Direction
// --------------------------------------------------

watchEffect(() => {
  document.documentElement.dir =
    languageMeta.value?.is_rtl
      ? 'rtl'
      : 'ltr'
})


// --------------------------------------------------
// Global Dark Mode
// --------------------------------------------------

watchEffect(() => {
  if (darkMode.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
})


// --------------------------------------------------
// Color Mode
// --------------------------------------------------

const $colorMode = computed(() =>
  darkMode.value
    ? 'dark bg-gray-900 text-white'
    : 'light bg-white text-black'
)


// --------------------------------------------------
// State Modification
// --------------------------------------------------

function handleToggleDarkMode() {
  toggleDarkMode()
}
</script>