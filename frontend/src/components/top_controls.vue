
<!-- ===============================================
File: frontend/src/components/top_controls.vue
Description: Fixed global PULSAR identity bar with system monitoring and metadata-driven controls
Change Date: 2026-11-27 02:29
Timezone: Asia/Baku
Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
=============================================== -->
<template>
  <header
    v-bind="attrs"
    class="pulsar-header fixed inset-x-0 top-0 z-50 h-16"
    dir="ltr"
  >
    <div
      class="pointer-events-none absolute inset-x-0 bottom-0 h-px opacity-50"
      style="background:var(--pulsar-level-accent)"
    ></div>

    <div
      class="pointer-events-none absolute inset-x-0 bottom-0 h-8 blur-xl"
      style="background:var(--pulsar-level-accent);opacity:0.045"
    ></div>

    <div
      class="relative mx-auto flex h-full w-full max-w-[1800px] items-center px-3 sm:px-5"
    >
      <!-- LEFT ZONE -->
      <div class="flex min-w-0 shrink-0 items-center gap-2.5">
        <img
          src="@/assets/logo/Pulsar.png"
          alt="Pulsar"
          class="h-12 w-auto select-none object-contain drop-shadow-[0_0_14px_rgba(99,102,241,0.22)] sm:h-14"
          draggable="false"
        />

        <div class="hidden h-6 w-px bg-border sm:block"></div>

        <button
          v-if="canGoBack"
          type="button"
          class="pulsar-icon-button"
          aria-label="Back"
          title="Back"
          @click="goBack"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            class="h-4 w-4"
          >
            <path d="M19 12H5" />
            <path d="m12 19-7-7 7-7" />
          </svg>
        </button>

        <div
          v-if="currentLevel > 0"
          class="pulsar-level-indicator"
          :title="`Level ${currentLevel}`"
          :aria-label="`Page Level ${currentLevel}`"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.7"
            class="h-4 w-4"
          >
            <path d="M5 7h14" />
            <path d="M5 12h14" />
            <path d="M5 17h14" />
            <circle
              cx="5"
              cy="7"
              r="1.5"
              fill="currentColor"
              stroke="none"
            />
          </svg>

          <span class="pulsar-level-number">
            {{ currentLevel }}
          </span>
        </div>
      </div>

      <!-- CENTER ZONE -->
      <div
        class="flex min-w-0 flex-1 justify-center px-3"
      >
        <div class="flex min-w-0 max-w-full items-center gap-3">
          <span
            class="hidden h-px w-8 shrink-0 opacity-50 sm:block"
            style="background:linear-gradient(to right,transparent,var(--pulsar-level-accent),transparent)"
          ></span>

          <h1
            class="truncate text-center text-sm font-semibold tracking-wide text-label sm:text-base"
          >
            {{ translatedPageTitle }}
          </h1>

          <span
            class="hidden h-px w-8 shrink-0 opacity-50 sm:block"
            style="background:linear-gradient(to right,transparent,var(--pulsar-level-accent),transparent)"
          ></span>
        </div>
      </div>  

      <!-- RIGHT ZONE -->
      <div class="ml-auto flex shrink-0 items-center gap-1.5 sm:gap-2">
        <!-- Language -->
        <select
          v-if="activeLanguages.length"
          :value="language"
          @change="changeLanguage($event.target.value)"
          class="pulsar-language-select h-9 cursor-pointer rounded-xl border border-border bg-panel px-2 text-xs font-semibold text-label shadow-sm transition hover:border-focus focus:outline-none"
          :style="{ colorScheme: darkMode ? 'dark' : 'light' }"
          aria-label="Language"
        >
          <option
            v-for="item in activeLanguages"
            :key="item.language_code"
            :value="item.language_code"
          >
            {{ item.native_name || item.language_name }}
          </option>
        </select>

        <!-- System Monitor -->
        <div
          v-if="isAuthenticated"
          class="system-monitor"
          :class="{ 'system-monitor-offline': !systemMetricsOnline }"
          :title="systemMonitorTooltip"
          aria-label="System Resource Monitor"
          role="status"
        >
          <div class="system-monitor-item">
            <span class="system-monitor-label">CPU</span>

            <div class="system-monitor-track">
              <div
                class="system-monitor-fill"
                :class="getMetricClass(systemMetrics.cpu)"
                :style="{ width: `${systemMetrics.cpu}%` }"
              ></div>
            </div>

            <span class="system-monitor-value">
              {{ formatMetric(systemMetrics.cpu) }}
            </span>
          </div>

          <div class="system-monitor-divider"></div>

          <div class="system-monitor-item">
            <span class="system-monitor-label">RAM</span>

            <div class="system-monitor-track">
              <div
                class="system-monitor-fill"
                :class="getMetricClass(systemMetrics.memory)"
                :style="{ width: `${systemMetrics.memory}%` }"
              ></div>
            </div>

            <span class="system-monitor-value">
              {{ formatMetric(systemMetrics.memory) }}
            </span>
          </div>

          <span
            class="system-monitor-status"
            :class="{
              'system-monitor-status-online': systemMetricsOnline
            }"
          ></span>
        </div>

        <!-- Permission Management -->
        <button
          v-if="canManagePermissions"
          type="button"
          class="pulsar-icon-button"
          :aria-label="permissionManagerTitle"
          :title="permissionManagerTitle"
          :aria-expanded="permissionManagerOpen"
          @click="permissionManagerOpen = !permissionManagerOpen"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            class="h-5 w-5"
          >
            <path d="M12 3 4.5 6v5.2c0 4.7 3.2 8 7.5 9.8 4.3-1.8 7.5-5.1 7.5-9.8V6L12 3Z" />
            <path d="m8.5 12 2.2 2.2 4.8-5" />
          </svg>
        </button>

        <!-- Source Trace -->
        <button
          v-if="canViewSourceTrace"
          type="button"
          class="pulsar-icon-button source-trace-trigger"
          :class="{ 'source-trace-trigger-active': sourceTraceOpen }"
          aria-label="Source Trace"
          title="Source Trace"
          :aria-expanded="sourceTraceOpen"
          @click="sourceTraceOpen = !sourceTraceOpen"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            class="h-5 w-5"
          >
            <circle cx="6" cy="6" r="2.5" />
            <circle cx="18" cy="6" r="2.5" />
            <circle cx="12" cy="18" r="2.5" />
            <path d="M8.5 6h7M7.5 8l3.2 7.7M16.5 8l-3.2 7.7" />
          </svg>
        </button>

        <!-- AI Avatar -->
        <button
          v-if="isAuthenticated"
          type="button"
          class="pulsar-icon-button ai-avatar-trigger"
          :class="{
            'ai-avatar-trigger-active': aiAvatarWindow.isOpen.value
          }"
          :aria-label="aiAvatarTitle"
          :title="aiAvatarTitle"
          :aria-expanded="aiAvatarWindow.isOpen.value"
          @click="toggleAIAvatar"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.7"
            class="h-5 w-5"
          >
            <path d="M12 2.5v3" />
            <path d="M12 18.5v3" />
            <path d="M2.5 12h3" />
            <path d="M18.5 12h3" />
            <circle cx="12" cy="12" r="6" />
            <path d="M9.5 10h.01M14.5 10h.01" />
            <path d="M9.5 14c1.5 1.2 3.5 1.2 5 0" />
          </svg>
        </button>

        <!-- Dark / Light Mode -->
        <button
          type="button"
          class="pulsar-icon-button"
          :title="darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
          @click="toggleDarkMode"
        >
          <svg
            v-if="darkMode"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            class="h-4 w-4"
          >
            <circle cx="12" cy="12" r="3" />
            <path
              d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l-1.41-1.41M17.66 6.34l1.41-1.41"
            />
          </svg>

          <svg
            v-else
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            class="h-4 w-4"
          >
            <path
              d="M21 12.8A8.5 8.5 0 1 1 11.2 3 6.6 6.6 0 0 0 21 12.8Z"
            />
          </svg>
        </button>

        <!-- UI Theme Intensity -->
        <div
          class="hidden h-9 items-center gap-2 rounded-xl border border-border bg-panel px-2.5 shadow-sm backdrop-blur lg:flex"
        >
          <span
            class="text-[10px] font-semibold uppercase tracking-wider text-muted"
          >
            UI
          </span>

          <input
            v-model.number="colorIntensity"
            type="range"
            min="1"
            max="10"
            step="1"
            class="w-20 cursor-pointer accent-[var(--pulsar-level-accent)]"
            aria-label="Color Intensity"
          />
        </div>

        <!-- User -->
        <button
          type="button"
          class="flex h-9 items-center gap-2 rounded-xl border border-border bg-panel px-2.5 text-label shadow-sm transition hover:border-focus"
          :title="userEmail"
        >
          <span
            class="flex h-6 w-6 items-center justify-center rounded-lg text-[11px] font-bold text-white"
            style="background:var(--pulsar-level-accent)"
          >
            {{ userInitial }}
          </span>

          <span class="hidden max-w-32 truncate text-xs font-medium xl:block">
            {{ userEmail }}
          </span>
        </button>
      </div>
    </div>
  </header>

  <SourceTracePanel v-model="sourceTraceOpen" />
  <PermissionManager v-model="permissionManagerOpen" />
</template>

<script setup>
import {
  ref,
  computed,
  watch,
  onMounted,
  onUnmounted,
  useAttrs,
  inject,
  nextTick
} from 'vue'

import { useRoute } from 'vue-router'

import SourceTracePanel from '@/components/tools/source_trace_panel.vue'
import PermissionManager from '@/components/security/PermissionManager.vue'
import axios from '@/utils/axiosInstance'
import { useSystemMetrics } from '@/composables/useSystemMetrics'

import {
  darkMode,
  language,
  userIdentity
} from '@/stores/uiStore'

import {
  useTranslation
} from '@/composables/useTranslation'

import {
  useLanguages
} from '@/composables/useLanguages'

import {
  usePageNavigation
} from '@/composables/usePageNavigation'

import {
  usePageContext
} from '@/composables/usePageContext'


// =================================================
// Composables
// =================================================

const {
  activeLanguages,
  changeLanguage
} = useLanguages()

const {
  currentLevel,
  canGoBack,
  goBack
} = usePageNavigation()

const {
  collectPageContext,
  clearPageContext
} = usePageContext({
  rootSelector: '.pulsar-shell'
})

const { translate } = useTranslation()

const {
  systemMetrics,
  systemMetricsOnline,
  startSystemMetrics,
  stopSystemMetrics
} = useSystemMetrics()


// =================================================
// Component Configuration
// =================================================

const props = defineProps({
  pageTitleKey: {
    type: String,
    default: ''
  },
  pageTitleContext: {
    type: String,
    default: 'GlobalUI'
  },
  aiAvatarDefinitionCode: {
    type: String,
    default: ''
  },
  aiAvatarContextVariables: {
    type: Object,
    default: () => ({})
  }
})

defineOptions({
  inheritAttrs: false
})

const attrs = useAttrs()
const route = useRoute()

const aiAvatarWindow = inject('aiAvatarWindow')

if (!aiAvatarWindow) {
  throw new Error('The global AI Avatar window provider is unavailable.')
}


// =================================================
// Component State
// =================================================

const translatedPageTitle = ref('')
const aiAvatarTitle = ref('AI Avatar')
const sourceTraceOpen = ref(false)
const permissionManagerOpen = ref(false)
const canManagePermissions = ref(false)
const canViewSourceTrace = ref(false)
const permissionManagerTitle = ref('')

const colorIntensity = ref(
  Number(localStorage.getItem('colorIntensity')) || 3
)



// =================================================
// Computed Properties
// =================================================

const userEmail = computed(() => {
  return userIdentity.value?.email || 'userid'
})

const isLoginRoute = computed(() => {
  const routeName = String(route.name || '').toLowerCase()

  const routeSegments = String(route.path || '')
    .toLowerCase()
    .split('/')
    .filter(Boolean)

  return (
    route.meta?.requiresGuest === true
    || routeName.includes('login')
    || routeName.includes('signin')
    || routeSegments.some(segment =>
      ['login', 'sign-in', 'signin', 'auth'].includes(segment)
    )
  )
})

const isAuthenticated = computed(() => {
  const email = userIdentity.value?.email

  return (
    !isLoginRoute.value
    && typeof email === 'string'
    && email.trim().length > 0
    && email.trim().toLowerCase() !== 'userid'
  )
})

async function loadUserPermissions() {
  if (!isAuthenticated.value) {
    canManagePermissions.value = false
    canViewSourceTrace.value = false
    return
  }

  try {
    const response = await axios.get('/permissions/me')
    const effectivePermissions = new Set(
      (response.data || [])
        .filter(grant => grant.is_effective === true)
        .map(grant => grant.permission_code)
    )

    canManagePermissions.value = effectivePermissions.has(
      'SECURITY.PERMISSION.GRANT'
    )
    canViewSourceTrace.value = effectivePermissions.has(
      'SOURCE_TRACE.VIEW'
    )
  } catch {
    canManagePermissions.value = false
    canViewSourceTrace.value = false
  }
}

async function updatePermissionManagerTitle() {
  permissionManagerTitle.value = await translate(
    'security.permissionManager',
    language.value
  )
}

const userInitial = computed(() => {
  if (!userEmail.value) {
    return '?'
  }

  return userEmail.value.trim().charAt(0).toUpperCase()
})

const systemMonitorTooltip = computed(() => {
  if (!systemMetricsOnline.value) {
    return 'System monitoring unavailable'
  }

  return [
    `CPU Usage: ${formatMetric(systemMetrics.value.cpu)}`,
    `Logical Cores: ${systemMetrics.value.logicalCores}`,
    `Memory Usage: ${formatMetric(systemMetrics.value.memory)}`,
    `Memory Used: ${formatBytes(systemMetrics.value.memoryUsed)}`,
    `Total Memory: ${formatBytes(systemMetrics.value.memoryTotal)}`
  ].join('\n')
})


// =================================================
// System Monitoring
// =================================================

function formatMetric(value) {
  const number = Number(value)

  if (!Number.isFinite(number)) {
    return '--%'
  }

  const normalized = Math.min(100, Math.max(0, number))

  return `${normalized.toFixed(1)}%`
}

function formatBytes(bytes) {
  const value = Number(bytes) || 0

  if (value < 1024) {
    return `${value} B`
  }

  const units = ['KB', 'MB', 'GB', 'TB']

  let size = value / 1024
  let unitIndex = 0

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`
}

function getMetricClass(value) {
  const usage = Number(value) || 0

  if (usage >= 85) {
    return 'system-monitor-fill-high'
  }

  if (usage >= 65) {
    return 'system-monitor-fill-medium'
  }

  return 'system-monitor-fill-normal'
}

// =================================================
// Theme Management
// =================================================

function applyThemeLevel(value) {
  document.documentElement.style.setProperty(
    '--theme-level',
    value.toString()
  )

  localStorage.setItem('colorIntensity', value.toString())
}

function toggleDarkMode() {
  darkMode.value = !darkMode.value
}


// =================================================
// Page Title
// =================================================

async function updateTitle() {
  if (!props.pageTitleKey) {
    translatedPageTitle.value = ''
    return
  }

  try {
    translatedPageTitle.value = await translate(
      props.pageTitleKey,
      language.value,
      props.pageTitleContext
    )
  } catch {
    translatedPageTitle.value = props.pageTitleKey
  }
}


// =================================================
// AI Avatar
// =================================================

async function updateAIAvatarTitle() {
  try {
    aiAvatarTitle.value = await translate(
      'AI_AVATAR_TITLE',
      language.value,
      'GlobalUI'
    )
  } catch {
    aiAvatarTitle.value = 'AI Avatar'
  }
}

function updateAIAvatarContext(authenticated, contextVariables) {
  if (!authenticated) {
    clearPageContext()
    aiAvatarWindow.setContext({})
    return
  }

  try {
    const pageContext = collectPageContext({
      sourceContext:
        contextVariables &&
        typeof contextVariables === 'object' &&
        !Array.isArray(contextVariables)
          ? contextVariables
          : {},
      pageTitle: translatedPageTitle.value,
      languageCode: language.value
    })

    aiAvatarWindow.setContext(pageContext)

  } catch (error) {
    console.error(
      '[PALI PAGE CONTEXT] Collection failed; previous context retained.',
      error
    )
  }
}

async function toggleAIAvatar() {
  if (aiAvatarWindow.isOpen.value) {
    aiAvatarWindow.toggle()
    return
  }

  await nextTick()

  updateAIAvatarContext(
    isAuthenticated.value,
    props.aiAvatarContextVariables
  )

  if (isAuthenticated.value) {
    aiAvatarWindow.toggle()
  }
}


// =================================================
// Lifecycle
// =================================================

onMounted(async () => {
  applyThemeLevel(colorIntensity.value)
  updateAIAvatarTitle()
  await updatePermissionManagerTitle()
  await loadUserPermissions()
})

onUnmounted(() => {
  stopSystemMetrics()
})


// =================================================
// Watchers
// =================================================

watch(colorIntensity, value => {
  applyThemeLevel(value)
})

watch(
  [
    () => props.pageTitleKey,
    () => language.value
  ],
  updateTitle,
  { immediate: true }
)

watch(
  () => language.value,
  updateAIAvatarTitle
)

watch(
  () => language.value,
  updatePermissionManagerTitle
)

watch(
  isAuthenticated,
  loadUserPermissions
)

watch(
  [
    isAuthenticated,
    () => props.aiAvatarContextVariables,
    translatedPageTitle,
    () => language.value
  ],
  ([authenticated, contextVariables]) => {
    updateAIAvatarContext(authenticated, contextVariables)
  },
  {
    immediate: true,
    deep: true,
    flush: 'post'
  }
)

watch(
  () => route.fullPath,
  async () => {
    await nextTick()

    updateAIAvatarContext(
      isAuthenticated.value,
      props.aiAvatarContextVariables
    )
  },
  {
    flush: 'post'
  }
)

watch(
  [
    isAuthenticated,
    () => props.aiAvatarDefinitionCode
  ],
  ([authenticated, definitionCode]) => {
    aiAvatarWindow.setDefinitionCode(
      authenticated && typeof definitionCode === 'string'
        ? definitionCode.trim()
        : ''
    )
  },
  {
    immediate: true
  }
)

watch(
  isAuthenticated,
  authenticated => {
    if (authenticated) {
      startSystemMetrics()
    } else {
      stopSystemMetrics()
      systemMetricsOnline.value = false
    }

    if (!authenticated && aiAvatarWindow.isOpen.value) {
      aiAvatarWindow.toggle()
    }
  },
  {
    immediate: true
  }
)
</script>

<style scoped>
/* Source Trace */

.source-trace-trigger {
  color: var(--pulsar-level-accent);
  transition:
    background 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease;
}

.source-trace-trigger:hover,
.source-trace-trigger-active {
  border-color: var(--pulsar-level-accent);
  background: var(--pulsar-level-accent-soft);
}


/* General Controls */

button:focus {
  outline: none;
}


/* Page Level Indicator */

.pulsar-level-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1px;
  height: 36px;
  min-width: 36px;
  padding: 0 7px;
  border: 1px solid var(--pulsar-level-border);
  border-radius: 12px;
  background: var(--pulsar-level-surface);
  color: var(--pulsar-level-accent);
  box-shadow: 0 1px 2px var(--pulsar-level-shadow);
  transition:
    border-color 0.2s ease,
    background 0.2s ease,
    color 0.2s ease;
}

.pulsar-level-indicator:hover {
  border-color: var(--pulsar-level-accent);
  background: var(--pulsar-level-accent-soft);
}

.pulsar-level-number {
  min-width: 12px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  text-align: center;
  color: var(--pulsar-level-accent);
}


/* Language Selector */

.pulsar-language-select {
  color-scheme: light;
}

.pulsar-language-select option {
  background: var(--color-panel);
  color: var(--color-label);
}


/* AI Avatar */

.ai-avatar-trigger {
  color: var(--pulsar-level-accent);
  transition:
    background 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease;
}

.ai-avatar-trigger:hover,
.ai-avatar-trigger-active {
  border-color: var(--pulsar-level-accent);
  background: var(--pulsar-level-accent-soft);
}

:global(.dark) .pulsar-language-select {
  color-scheme: dark;
}

:global(.dark) .pulsar-language-select option {
  background: var(--color-panel);
  color: var(--color-label);
}


/* System Resource Monitor */

.system-monitor {
  display: flex;
  align-items: center;
  gap: 9px;
  height: 36px;
  padding: 0 10px;
  border: 1px solid var(--pulsar-level-border);
  border-radius: 12px;
  background: var(--pulsar-level-surface);
  box-shadow: 0 1px 2px var(--pulsar-level-shadow);
  transition:
    border-color 0.2s ease,
    background 0.2s ease,
    opacity 0.2s ease;
}

.system-monitor:hover {
  border-color: var(--pulsar-level-accent);
  background: var(--pulsar-level-accent-soft);
}

.system-monitor-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.system-monitor-label {
  color: var(--color-muted);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.system-monitor-track {
  width: 34px;
  height: 4px;
  overflow: hidden;
  border-radius: 10px;
  background: var(--pulsar-level-border);
}

.system-monitor-fill {
  height: 100%;
  border-radius: inherit;
  transition:
    width 0.5s ease,
    background 0.3s ease;
}

.system-monitor-fill-normal {
  background: #22c55e;
}

.system-monitor-fill-medium {
  background: #eab308;
}

.system-monitor-fill-high {
  background: #ef4444;
}

.system-monitor-value {
  display: inline-block;
  min-width: 38px;
  direction: ltr;
  unicode-bidi: isolate;
  white-space: nowrap;
  color: var(--color-label);
  font-family: Arial, sans-serif;
  font-size: 10px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.system-monitor-track {
  direction: ltr;
  width: 34px;
  height: 4px;
  overflow: hidden;
  border-radius: 10px;
  background: var(--pulsar-level-border);
}

.system-monitor-status {
  width: 5px;
  height: 5px;
  flex-shrink: 0;
  border-radius: 50%;
  background: #ef4444;
}

.system-monitor-status-online {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.45);
}

.system-monitor-offline {
  opacity: 0.65;
}
</style>
