// ===============================================
// File:
// frontend/src/composables/usePageNavigation.js
//
// Description:
// Central runtime navigation state for PULSAR dynamic pages
//
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// ===============================================

import {
  ref,
  computed
} from 'vue'
import {
  useRouter
} from 'vue-router'

const pageStack = ref([])

function registerPage(pageKey) {
  if (!pageKey) {
    return
  }

  const lastPage =
    pageStack.value[
      pageStack.value.length - 1
    ]

  if (
    lastPage === pageKey
  ) {
    return
  }

  pageStack.value.push(
    pageKey
  )
}

const currentPageKey = computed(() => {
  if (
    pageStack.value.length === 0
  ) {
    return null
  }

  return (
    pageStack.value[
      pageStack.value.length - 1
    ]
  )
})

/*
 * Navigation level:
 *
 * Dashboard  = Level 0
 * First page = Level 1
 * Child page = Level 2
 * Next page  = Level 3
 *
 * currentLevel represents navigation depth only.
 * It is independent from page_type, panel_type,
 * where_clause, parm[n], record identity, and CRUD state.
 *
 * currentLevel is the single runtime source for
 * the Visual Level Theme.
 *
 * This composable does not define or modify
 * visual theme behavior.
 */
const currentLevel = computed(() => {
  return pageStack.value.length
})

// Dashboard is outside the Dynamic Page stack.
// Any registered Dynamic Page can therefore navigate back.
const canGoBack = computed(() => {
  return pageStack.value.length > 0
})

export function usePageNavigation() {
  const router = useRouter()

  function goBack() {
    if (!canGoBack.value) {
      return
    }

    if (
      pageStack.value.length === 1
    ) {
      pageStack.value = []

      router.back()

      return
    }

    pageStack.value.pop()

    router.back()
  }

  function resetNavigation() {
    pageStack.value = []
  }

  return {
    pageStack,
    currentPageKey,
    currentLevel,
    canGoBack,
    registerPage,
    goBack,
    resetNavigation
  }
}

// Important Learning Points:
// 1. Navigation state contains page identity only.
// 2. Selected records are not stored in pageStack.
// 3. primary_key semantics do not belong to navigation.
// 4. where_clause semantics do not belong to navigation.
// 5. parm[n] is never created or resolved here.
// 6. Record data is transported separately through route context.
// 7. Dashboard remains outside the Dynamic Page stack.
// 8. Dashboard is Level 0.
// 9. The first Dynamic Page is Level 1.
// 10. Child Dynamic Pages increment the navigation level.
// 11. currentLevel represents navigation depth, not page_type.
// 12. currentLevel is the single source for Visual Level Theme.
// 13. Visual Level Theme does not alter navigation behavior.
// 14. Navigation remains independent from record identity and CRUD state.
// 15. pageStack is shared by all consumers of usePageNavigation.
// 16. generic_page and top_controls therefore use the same navigation level.
// 17. Navigation does not interpret runtime metadata or database fields.
