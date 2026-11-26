<!--
 File: src/pages/dashboard_page.vue
 Description: PulsarGen Dashboard with dynamic menu, translations, and metadata-driven RTL support
-->

<script setup>
import { ref, watch, computed } from 'vue'
import {
  darkMode,
  language,
  languageMeta
} from '@/stores/uiStore'
import { useRouter } from 'vue-router'
import TopControls from '@/components/top_controls.vue'
import { useTranslation } from '@/composables/useTranslation'
import { useUserAccess } from '@/composables/useUserAccess'\nimport { fetchPageRecordCount } from '@/composables/usePageRecordCount'\nimport { userIdentity } from '@/stores/uiStore'

const router = useRouter()

const {
  userAccessMap,
  fetchUserAccess
} = useUserAccess()

const itemKeys = computed(() =>
  Object.keys(userAccessMap.value)
)

const {
  translate
} = useTranslation()

const translations = ref({})\nconst recordCounts = ref({})

const isRtl = computed(() => {
  return languageMeta.value?.is_rtl === true
})

async function loadTranslations() {
  const lang = language.value
  const result = {}

  for (const key of itemKeys.value) {
    result[key] = await translate(
      key,
      lang,
      'dashboard_page'
    )
  }

  translations.value = result
}

watch(
  () => [
    language.value,
    userAccessMap.value
  ],
  loadTranslations,
  { immediate: true }
)

const accessList = computed(() =>
  Object.entries(userAccessMap.value).map(
    ([pageKey, access]) => ({
      pageKey,
      level: access?.page_level || ''
    })
  )
)

let countRequestVersion = 0

async function loadRecordCounts() {
  const version = ++countRequestVersion
  const entries = accessList.value
  const nextCounts = {}

  await Promise.all(entries.map(async item => {
    try {
      const count = await fetchPageRecordCount(
        item.pageKey,
        { runtimeContext: userIdentity.value || {} }
      )
      if (count !== null && version === countRequestVersion) {
        nextCounts[item.pageKey] = count
      }
    } catch (err) {
      console.warn(
        'dashboard_page: record count unavailable',
        item.pageKey,
        err
      )
    }
  }))

  if (version === countRequestVersion) {
    recordCounts.value = nextCounts
  }
}

watch(
  accessList,
  loadRecordCounts,
  { immediate: true }
)

function getLevelColor(level) {
  const colors = [
    'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
    'bg-amber-500/10 text-amber-600 dark:text-amber-400',
    'bg-blue-500/10 text-blue-600 dark:text-blue-400',
    'bg-purple-500/10 text-purple-600 dark:text-purple-400',
    'bg-rose-500/10 text-rose-600 dark:text-rose-400',
    'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400',
    'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400'
  ]

  if (!level) {
    return colors[0]
  }

  const index =
    [...String(level)].reduce(
      (sum, char) => sum + char.charCodeAt(0),
      0
    ) % colors.length

  return colors[index]
}

function goToPage(pageKey) {
  router.push(`/pages/${pageKey}`)
}

fetchUserAccess()
</script>

<template>
  <div
    :class="{ dark: darkMode }"
    class="pulsar-shell min-h-screen"
  >
    <TopControls pageTitleKey="dashboard_page" />

<div
  :dir="isRtl ? 'rtl' : 'ltr'"
  class="mx-auto w-full max-w-7xl px-4 pb-8 pt-[92px] sm:px-6"
>
  <div
    class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
  >
    <button
      v-for="item in accessList"
      :key="item.pageKey"
      type="button"
      @click="goToPage(item.pageKey)"
      class="group pulsar-surface flex min-h-24 items-center justify-between p-4 text-start transition-all hover:-translate-y-0.5 hover:border-focus"
    >
      <div class="min-w-0">
        <div
          class="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-primary-soft text-primary"
          style="background:var(--color-primary-soft)"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            class="h-4 w-4"
          >
            <rect
              x="4"
              y="4"
              width="16"
              height="16"
              rx="2"
            />
            <path d="M8 8h8M8 12h8M8 16h5" />
          </svg>
        </div>

        <div
          class="truncate text-sm font-semibold text-label group-hover:text-primary"
        >
          {{ translations[item.pageKey] || item.pageKey }}
        </div>
      </div>

      <div class="ml-3 flex shrink-0 items-center gap-2">
        <span
          v-if="recordCounts[item.pageKey] !== undefined"
          class="min-w-7 rounded-full bg-primary/10 px-2 py-1 text-center text-[10px] font-bold tabular-nums text-primary"
          :aria-label="`Record count: ${recordCounts[item.pageKey]}`"
        >
          {{ recordCounts[item.pageKey] }}
        </span>
        <span
          class="rounded-md px-2 py-1 text-[10px] font-bold"
          :class="getLevelColor(item.level)"
        >
          {{ item.level }}
        </span>
      </div>
    </button>
  </div>

  <div
    v-if="accessList.length === 0"
    class="pulsar-surface mt-3 p-10 text-center text-sm text-empty"
  >
    {{ translations.no_access_entries || 'No access entries found.' }}
  </div>
</div>

  </div>
</template>
