<!-- ===============================================

File: frontend/src/components/panels/context_panel.vue

Description: Metadata-driven operational panel with hover collapse, pinning, and isolated scrolling

Author: MHKolahi@gmail.com

In collaboration with GPT4 Chat Assistant: Bahram

Last Modified: 2026-11-27 22:08 (Asia/Baku)

=============================================== -->



<template>
  <aside
    v-if="hasPanelContent"
    class="relative h-full min-h-0 flex-shrink-0 overflow-hidden bg-panel transition-[width] duration-200 ease-in-out"
    :class="[
      isRtl ? 'border-l' : 'border-r',
      isOpen ? 'border-border' : 'border-transparent'
    ]"
    :style="{ width: `${isOpen ? panelWidth : collapsedWidth}px` }"
    :dir="isRtl ? 'rtl' : 'ltr'"
    @mouseenter="handlePanelMouseEnter"
    @mouseleave="handlePanelMouseLeave"
    @focusout="handlePanelFocusOut"
  >
    <div
      v-if="isOpen"
      class="flex h-full min-h-0 w-full flex-col overflow-hidden"
    >
      <div class="flex shrink-0 items-center justify-between gap-2 border-b border-border px-3 py-3">
        <div class="pulsar-section-label">
          PANEL
        </div>

        <div class="flex items-center gap-2">
          <span class="pulsar-status">
            {{ accessList.length }}
          </span>

          <button
            ref="pinButton"
            type="button"
            class="inline-flex h-7 w-7 items-center justify-center rounded-md border transition hover:bg-hover hover:text-primary"
            :class="isPinned
              ? 'border-primary bg-primary/10 text-primary'
              : 'border-border text-muted'"
            :aria-label="isPinned ? panelLabels.unpin : panelLabels.pin"
            :title="isPinned ? panelLabels.unpin : panelLabels.pin"
            :aria-pressed="isPinned"
            @click="togglePin"
          >
            <svg
              v-if="isPinned"
              viewBox="0 0 24 24"
              class="h-4 w-4"
              fill="currentColor"
              stroke="currentColor"
              stroke-width="1.2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M16 3 21 8 17 9 13 13 16 16 14 18 10 14 5 19 4 18 9 13 5 9 7 7 10 10 14 6 16 3Z" />
            </svg>
            <svg
              v-else
              viewBox="0 0 24 24"
              class="h-4 w-4"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M16 3 21 8 17 9 13 13 16 16 14 18 10 14 5 19 4 18 9 13 5 9 7 7 10 10 14 6 16 3Z" />
              <path d="m3 21 18-18" />
            </svg>
          </button>
        </div>
      </div>

      <div class="min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-contain p-2.5">
        <div class="space-y-1.5">
          <button
            v-for="item in accessList"
            :key="`${item.panelType}:${item.panelKey}`"
            type="button"
            :disabled="!hasSelectedRecord"
            :data-pulsar-action-code="item.panelType === 'FUNCTION' ? 'function_execution' : 'page_navigation'"
            :data-pulsar-target-key="item.panelKey"
            :data-pulsar-target-type="item.panelType"
            :data-pulsar-description="item.panelDescription || ''"
            :data-pulsar-description-source="item.descriptionSource || ''"
            :data-pulsar-description-status="item.panelDescription && item.descriptionSource ? 'documented' : 'missing'"
            class="group w-full rounded-xl border border-transparent px-3 py-2.5 text-start transition hover:border-border hover:bg-hover disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-transparent disabled:hover:bg-transparent"
            @click="openPanel(item)"
          >
            <div class="flex items-center gap-2">
              <span class="truncate text-sm font-medium text-label group-hover:text-primary">
                {{ translations[item.panelKey] || item.panelKey }}
              </span>
              <span
                v-if="item.panelType === 'PAGE' && recordCounts[item.panelKey] !== undefined"
                class="ml-auto min-w-7 shrink-0 rounded-full bg-primary/10 px-2 py-0.5 text-center text-[10px] font-bold tabular-nums text-primary"
                :aria-label="`Record count: ${recordCounts[item.panelKey]}`"
              >
                {{ recordCounts[item.panelKey] }}
              </span>
            </div>
          </button>
        </div>
      </div>
    </div>

    <button
      v-else
      type="button"
      class="flex h-full w-full flex-col items-center justify-center gap-2 bg-panel px-1 text-muted transition hover:bg-hover hover:text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
      :aria-label="panelLabels.open"
      :aria-expanded="isOpen"
      :title="panelLabels.open"
      @click="openPanelManually"
    >
      <svg
        viewBox="0 0 24 24"
        class="h-4 w-4"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path :d="isRtl ? 'm9 18 6-6-6-6' : 'm15 18-6-6 6-6'" />
      </svg>
      <span class="text-[10px] font-semibold tracking-wide [writing-mode:vertical-rl]">
        PANEL
      </span>
    </button>

    <div
      v-if="isOpen"
      class="absolute bottom-0 top-0 w-1 cursor-col-resize transition hover:bg-primary/20"
      :class="isRtl ? 'left-0' : 'right-0'"
      @mousedown="startResize"
    />
  </aside>
</template>



<script setup>

import {

  ref,

  computed,

  onMounted,

  onBeforeUnmount,

  watch,
  nextTick

} from 'vue'

import { useRouter } from 'vue-router'

import {

  language,

  languageMeta

} from '@/stores/uiStore'

import { useTranslation } from '@/composables/useTranslation'

import { useContextAccess } from '@/composables/useContextAccess.js'
import { fetchPageRecordCount } from '@/composables/usePageRecordCount'



// =================================================

// Props

// =================================================

const props = defineProps({

  contextId: {

    type: String,

    required: true

  },

  cartableKey: {

    type: String,

    required: true

  },

  sourceComponent: {

    type: String,

    default: null

  },

  selectedRecord: {

    type: Object,

    default: null

  },

  parentRecordContext: {

    type: Array,

    default: () => []

  },

  runtimeContext: {

    type: Object,

    default: () => ({})

  },

  initialWidth: {

    type: Number,

    default: 280

  },

  minWidth: {

    type: Number,

    default: 180

  },

  maxWidth: {

    type: Number,

    default: 600

  }

})



const emit = defineEmits([
  'open-function'
])



// =================================================

// Router

// =================================================

const router = useRouter()



// =================================================

// Context Access

// =================================================

const {

  accessList,

  loading,

  fetchContextAccess

} = useContextAccess()



// =================================================

// Translation

// =================================================

const { translate } = useTranslation()

const translations = ref({})
const recordCounts = ref({})



// =================================================

// Panel State

// =================================================

const panelWidth = ref(props.initialWidth)

const pinButton = ref(null)

const collapsedWidth = 32

const isOpen = ref(false)

const isPinned = ref(false)

const panelLabels = ref({
  pin: 'Pin panel',
  unpin: 'Unpin panel',
  open: 'Open panel'
})

const resizing = ref(false)

const resizeStartX = ref(0)

const resizeStartWidth = ref(0)



// =================================================

// Direction

// =================================================

const isRtl = computed(() => {

  return languageMeta.value?.is_rtl === true

})

const hasPanelContent = computed(() => {
  return !loading.value && accessList.value.length > 0
})

function handlePanelMouseEnter() {
  isOpen.value = true
}

function handlePanelMouseLeave() {
  if (!isPinned.value && !resizing.value) {
    isOpen.value = false
  }
}

function handlePanelFocusOut(event) {
  const panel = event.currentTarget

  nextTick(() => {
    if (
      !isPinned.value &&
      !panel.contains(document.activeElement) &&
      !panel.matches(':hover')
    ) {
      isOpen.value = false
    }
  })
}

async function openPanelManually() {
  isOpen.value = true
  await nextTick()
  pinButton.value?.focus()
}

function togglePin() {
  isPinned.value = !isPinned.value

  if (isPinned.value) {
    isOpen.value = true
  }
}



// =================================================

// Selection State

// =================================================

const hasSelectedRecord = computed(() => {

  return (

    props.selectedRecord &&

    typeof props.selectedRecord === 'object' &&

    Object.keys(props.selectedRecord).length > 0

  )

})



// =================================================

// Translations

// =================================================

let countRequestVersion = 0

async function loadPageRecordCounts() {
  const version = ++countRequestVersion
  const selectedRecord =
    props.selectedRecord &&
    typeof props.selectedRecord === 'object' &&
    !Array.isArray(props.selectedRecord)
      ? props.selectedRecord
      : null

  if (!selectedRecord || Object.keys(selectedRecord).length === 0) {
    recordCounts.value = {}
    return
  }

  const pages = accessList.value.filter(
    item => item?.panelType === 'PAGE' && item?.panelKey
  )
  const nextCounts = {}

  await Promise.all(pages.map(async item => {
    try {
      const count = await fetchPageRecordCount(
        item.panelKey,
        {
          selectedRecord: props.selectedRecord,
          runtimeContext: props.runtimeContext || {}
        }
      )
      if (count !== null && version === countRequestVersion) {
        nextCounts[item.panelKey] = count
      }
    } catch (err) {
      console.warn('ContextPanel: record count unavailable', item.panelKey, err)
    }
  }))

  if (version === countRequestVersion) {
    recordCounts.value = nextCounts
  }
}

async function loadTranslations() {

  const result = {}



  for (const item of accessList.value) {

    if (!item?.panelKey) {

      continue

    }



    result[item.panelKey] = await translate(

      item.panelKey,

      language.value,

      'dashboard_page'

    )

  }



  translations.value = result

  const [pin, unpin, open] = await Promise.all([
    translate('pulsar.context_panel.pin', language.value, 'Default'),
    translate('pulsar.context_panel.unpin', language.value, 'Default'),
    translate('pulsar.context_panel.open', language.value, 'Default')
  ])

  panelLabels.value = {
    pin: pin && pin !== 'pulsar.context_panel.pin' ? pin : 'Pin panel',
    unpin: unpin && unpin !== 'pulsar.context_panel.unpin' ? unpin : 'Unpin panel',
    open: open && open !== 'pulsar.context_panel.open' ? open : 'Open panel'
  }

}



// =================================================

// Load Panel

// =================================================

async function loadPanel() {

  if (!props.cartableKey || !props.contextId) {

    translations.value = {}

    return

  }



  try {

    isPinned.value = false
    isOpen.value = false
    translations.value = {}



    await fetchContextAccess(

      props.cartableKey,

      props.contextId

    )



    await loadTranslations()
    await loadPageRecordCounts()

  } catch (err) {

    console.error(

      'ContextPanel: failed to load Cartable panels',

      err

    )

    translations.value = {}

  }

}



// =================================================

// Open Panel
// =================================================
//
// ContextPanel provides:
// - target panel metadata
// - source context
// - source component
// - selected record data
// - existing parent-record navigation chain
//
// It does not interpret:
// - primary_key
// - where_clause
// - parm[n]
//
// Primary-key resolution belongs to useComponentKey.
//
// parm[n] resolution belongs exclusively to
// component_where.py / useComponentWhere.

// =================================================
function openPanel(item) {
  if (!item?.panelKey || !hasSelectedRecord.value) {
    return
  }

  const context = {
    context_id: String(props.contextId),
    source_component:
      props.sourceComponent || null,
    parent_record_context:
      Array.isArray(props.parentRecordContext)
        ? props.parentRecordContext
        : []
  }

  const selectedRecord =
    props.selectedRecord &&
    typeof props.selectedRecord === 'object'
      ? props.selectedRecord
      : null

  if (item.panelType === 'FUNCTION') {
    emit('open-function', {
      functionName: item.panelKey,
      cartableKey: props.cartableKey,
      context,
      selectedRecord
    })
    return
  }

  router.push({
    path: `/pages/${item.panelKey}`,
    query: {
      context: JSON.stringify(context),
      selected_record:
        selectedRecord
          ? JSON.stringify(selectedRecord)
          : ''
    }
  })
}



// =================================================

// Resize

// =================================================

function startResize(event) {

  resizing.value = true

  resizeStartX.value = event.clientX

  resizeStartWidth.value = panelWidth.value



  document.addEventListener(

    'mousemove',

    handleResize

  )



  document.addEventListener(

    'mouseup',

    stopResize

  )

}



function handleResize(event) {

  if (!resizing.value) {

    return

  }



  const direction = isRtl.value ? -1 : 1



  const delta =

    (event.clientX - resizeStartX.value) *

    direction



  const width =

    resizeStartWidth.value + delta



  panelWidth.value = Math.min(

    props.maxWidth,

    Math.max(

      props.minWidth,

      width

    )

  )

}



function stopResize() {

  resizing.value = false



  document.removeEventListener(

    'mousemove',

    handleResize

  )



  document.removeEventListener(

    'mouseup',

    stopResize

  )

}



// =================================================

// Watchers

// =================================================

watch(

  [

    () => props.contextId,

    () => props.cartableKey

  ],

  loadPanel

)



watch(

  language,

  () => {

    if (accessList.value.length > 0) {

      loadTranslations()

    }

  }

)



// =================================================

// Lifecycle

// =================================================

watch(
  [
    () => props.selectedRecord,
    () => props.runtimeContext
  ],
  loadPageRecordCounts,
  { deep: true }
)

onMounted(loadPanel)



onBeforeUnmount(stopResize)



// Important Learning Points:

// 1. cartableKey identifies the Cartable component.

// 2. contextId identifies the runtime context.

// 3. sourceComponent identifies the source Grid component.

// 4. selectedRecord contains the complete source record.

// 5. parentRecordContext contains the existing navigation chain.

// 6. parentRecordContext is passed forward unchanged.

// 7. Panel definitions come from Cartable metadata.

// 8. panelType distinguishes PAGE from FUNCTION.

// 9. PAGE panels navigate to a target page.

// 10. FUNCTION panels are delegated through open-function.

// 11. Panel authorization is resolved by the backend.

// 12. JWT identifies the current user.

// 13. contextId is not used for panel authorization.

// 14. Panel access level is not used by the frontend.

// 15. ContextPanel does not interpret primary_key metadata.

// 16. ContextPanel does not interpret where_clause metadata.

// 17. ContextPanel does not create or resolve parm[n].

// 18. Primary-key resolution belongs to useComponentKey.

// 19. Selected record is passed as data to the target page or function.

// 20. Source component is passed as navigation metadata.

// 21. Existing parent-record context is passed as navigation metadata.

// 22. Navigation remains metadata-driven.

// 23. Resize behavior remains unchanged.

// 24. Panel buttons are disabled when no grid record is selected.

// 25. Panel navigation is guarded by the selected-record state.

// 26. sourceComponent is not interpreted by ContextPanel.

// 27. Function execution is delegated to the parent through open-function.

// 28. Empty ContextPanels are not rendered.
// 29. Unpinned panels collapse when the pointer leaves the panel.
// 30. The collapsed tab opens the panel on hover and supports keyboard activation.
// 31. Pinned panels remain expanded until they are unpinned and the pointer leaves.
// 32. Panel visibility and pin state do not mutate Grid selection or navigation context.

</script>