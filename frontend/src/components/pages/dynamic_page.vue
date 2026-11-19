<!--
 File: Pulsar/frontend/src/components/pages/dynamic_page.vue
 Description: Dynamic page runtime resolver
 Author: MHKolahi@gmail.com
 In collaboration with GPT4 Chat Assistant: Bahram
-->
<template>
  <div v-if="loading" class="p-4">
    Loading...
  </div>

  <div v-else-if="error" class="p-4 text-red-500">
    {{ error }}
  </div>

  <div v-else-if="!gridName" class="p-4 text-red-500">
    No grid component configured for page: {{ pageKey }}
  </div>

  <generic_page
    v-else
    :gridComponent="dynamicGrid"
    :formComponent="dynamicForm"
    :gridName="gridName"
    :formName="formName"
    :pageTitleKey="pageKey"
    :runtimeContext="runtimeContext"
    :c_page_view="pageAccess.c_page_view"
    :c_page_insert="pageAccess.c_page_insert"
    :c_page_update="pageAccess.c_page_update"
    :c_page_delete="pageAccess.c_page_delete"
  />
</template>

<script setup>
import {
  computed,
  watch
} from 'vue'
import {
  useRoute
} from 'vue-router'
import generic_page from '@/components/pages/generic_page.vue'
import dynamicGrid from '@/components/grids/dynamic_dw_grid.vue'
import dynamicForm from '@/components/forms/dynamic_dw_form.vue'
import {
  userIdentity
} from '@/stores/uiStore'
import {
  useUserAccess
} from '@/composables/useUserAccess'
import {
  usePageNavigation
} from '@/composables/usePageNavigation'
import {
  usePageRuntime
} from '@/composables/usePageRuntime.js'

// =================================================
// Props
// =================================================
const props = defineProps({
  pageKey: {
    type: String,
    required: true
  }
})

// =================================================
// Router
// =================================================
const route = useRoute()

// =================================================
// User Access
// =================================================
const {
  userAccessMap
} = useUserAccess()

const pageAccess = computed(() => {
  return (
    userAccessMap.value?.[props.pageKey] ||
    {}
  )
})

// =================================================
// Page Navigation
// =================================================
// Navigation owns page depth.
//
// dynamic_page only registers the page.
// It does not calculate visual level.
// usePageNavigation is the single source of
// navigation-depth information for the runtime.
const {
  registerPage
} = usePageNavigation()

// =================================================
// Page Runtime
// =================================================
const {
  runtime,
  loading,
  error,
  loadRuntime
} = usePageRuntime()

// =================================================
// Navigation Context
// =================================================
// Navigation provides raw context only.
//
// parm[n] is never created or resolved here.
// Selected record transport is handled by the
// target generic_page from the route.
const navigationContext = computed(() => {
  const context =
    route.query?.context

  if (!context) {
    return {}
  }

  try {
    const parsed =
      JSON.parse(
        String(context)
      )

    if (
      parsed &&
      typeof parsed === 'object' &&
      !Array.isArray(parsed)
    ) {
      return parsed
    }

    return {}
  } catch (err) {
    console.warn(
      'dynamic_page: invalid navigation context',
      err
    )

    return {}
  }
})

// =================================================
// Runtime Components
// =================================================
const components = computed(() => {
  return runtime.value?.components || []
})

// =================================================
// Runtime Context
// =================================================
// Runtime context contains:
// - frontend user identity
// - raw navigation context
//
// Authentication and page runtime context authority
// remain on the backend.
//
// parm[n] does not belong to this layer.
const runtimeContext = computed(() => {
  const identity =
    userIdentity.value || {}

  const context = {}

  Object.entries(identity).forEach(
    ([key, value]) => {
      if (
        value === null ||
        value === undefined ||
        value === ''
      ) {
        return
      }

      context[key] = value
    }
  )

  Object.entries(
    navigationContext.value
  ).forEach(
    ([key, value]) => {
      if (
        value === null ||
        value === undefined ||
        value === ''
      ) {
        return
      }

      context[key] = value
    }
  )

  return context
})

// =================================================
// Grid Component
// =================================================
const gridName = computed(() => {
  const component =
    components.value.find(
      item =>
        item.component_name?.includes('grid')
    )

  return (
    component?.component_name ||
    null
  )
})

// =================================================
// Form Component
// =================================================
const formName = computed(() => {
  const component =
    components.value.find(
      item =>
        item.component_name?.includes('form')
    )

  if (component?.component_name) {
    return component.component_name
  }

  if (gridName.value) {
    return gridName.value.replace(
      'grid',
      'form'
    )
  }

  return null
})

// =================================================
// Load Page Runtime
// =================================================
async function refreshPageRuntime() {
  if (!props.pageKey) {
    return
  }

  try {
    await loadRuntime(
      props.pageKey
    )
  } catch (err) {
    console.error(
      'dynamic_page: runtime load failed',
      err
    )
  }
}

// =================================================
// Page Navigation
// =================================================
watch(
  () => props.pageKey,
  async (
    newPageKey,
    oldPageKey
  ) => {
    if (!newPageKey) {
      return
    }

    registerPage(
      newPageKey
    )

    if (
      newPageKey !== oldPageKey
    ) {
      await refreshPageRuntime()
    }
  },
  {
    immediate: true
  }
)

// =================================================
// Runtime Context Changes
// =================================================
watch(
  () => route.query?.context,
  async () => {
    await refreshPageRuntime()
  }
)

// Important Learning Points:
// 1. Dynamic pages remain fully metadata-driven.
// 2. Page runtime loading belongs to usePageRuntime.
// 3. Components do not perform direct runtime fetch calls.
// 4. Navigation provides only raw runtime context.
// 5. Selected record transport remains separate from runtime context.
// 6. dynamic_page never creates or interprets parm[n].
// 7. parm[n] resolution belongs exclusively to component_where.py.
// 8. Runtime context remains independent from record identity.
// 9. User identity remains available as frontend runtime context.
// 10. Metadata determines the runtime Grid and Form components.
// 11. No physical database field name is mapped here.
// 12. generic_page receives runtimeContext without interpreting
//     where_clause or primary_key metadata.
// 13. Page runtime authentication context is determined by the backend.
// 14. context_id is no longer supplied by the client runtime request.
// 15. dynamic_page registers page navigation depth but does not calculate it.
// 16. Visual Level Theme is resolved from the shared usePageNavigation stack.
// 17. dynamic_page does not own page_type, panel_type, visual level,
//     where_clause, parm[n], or record identity.
</script>
