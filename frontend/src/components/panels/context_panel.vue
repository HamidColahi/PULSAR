<!-- ===============================================

File: frontend/src/components/panels/context_panel.vue

Description: Resizable metadata-driven context panel with isolated scrolling

Author: MHKolahi@gmail.com

In collaboration with GPT4 Chat Assistant: Bahram

Last Modified: 2026-10-08 13:11:00 (Asia/Baku)

=============================================== -->



<template>

  <aside

    class="relative flex h-full min-h-0 flex-shrink-0 overflow-hidden border-r border-border bg-panel"

    :style="{ width: `${panelWidth}px` }"

    :dir="isRtl ? 'rtl' : 'ltr'"

  >

    <div class="flex h-full min-h-0 w-full flex-col overflow-hidden">

      <div

        class="flex shrink-0 items-center justify-between border-b border-border px-3 py-3"

      >

        <div class="pulsar-section-label">

          PANEL

        </div>

        <span class="pulsar-status">

          {{ accessList.length }}

        </span>

      </div>



      <div

        class="min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-contain p-2.5"

      >

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

              <span

                class="truncate text-sm font-medium text-label group-hover:text-primary"

              >

                {{ translations[item.panelKey] || item.panelKey }}

              </span>

            </div>

          </button>



          <p

            v-if="loading"

            class="py-8 text-center text-xs text-muted"

          >

            Loading...

          </p>



          <p

            v-else-if="accessList.length === 0"

            class="py-8 text-center text-xs text-empty"

          >

            No entries found.

          </p>

        </div>

      </div>

    </div>



    <div

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

  watch

} from 'vue'

import { useRouter } from 'vue-router'

import {

  language,

  languageMeta

} from '@/stores/uiStore'

import { useTranslation } from '@/composables/useTranslation'

import { useContextAccess } from '@/composables/useContextAccess.js'



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



// =================================================

// Panel State

// =================================================

const panelWidth = ref(props.initialWidth)

const resizing = ref(false)

const resizeStartX = ref(0)

const resizeStartWidth = ref(0)



// =================================================

// Direction

// =================================================

const isRtl = computed(() => {

  return languageMeta.value?.is_rtl === true

})



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

    translations.value = {}



    await fetchContextAccess(

      props.cartableKey,

      props.contextId

    )



    await loadTranslations()

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

</script>