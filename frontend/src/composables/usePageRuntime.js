// =============================================
// File:
// frontend/src/composables/usePageRuntime.js
//
// Description:
// Metadata-driven page runtime client
//
// Responsibilities:
//   1. Request page runtime metadata
//   2. Transport page key only
//   3. Expose runtime state to page components
//   4. Keep HTTP transport outside Vue components
//
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// =============================================
import { ref } from 'vue'
import axiosInstance from '@/utils/axiosInstance'

export function usePageRuntime() {
  const runtime = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function loadRuntime(pageKey) {
    if (!pageKey) {
      const validationError = new Error('Page key is required')
      error.value = validationError
      throw validationError
    }

    loading.value = true
    error.value = null

    try {
      const response = await axiosInstance.get(
        `/page/runtime/${encodeURIComponent(pageKey)}`
      )

      runtime.value = response.data
      return runtime.value
    } catch (err) {
      console.error(
        'usePageRuntime: runtime load failed',
        err
      )

      error.value =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to load page runtime'

      runtime.value = null
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearRuntime() {
    runtime.value = null
    loading.value = false
    error.value = null
  }

  return {
    runtime,
    loading,
    error,
    loadRuntime,
    clearRuntime
  }
}

// Important Learning Points:
// 1. Page runtime HTTP transport belongs to this composable.
// 2. dynamic_page.vue does not perform direct fetch calls.
// 3. The backend remains the source of truth for page runtime metadata.
// 4. The authenticated backend user is the source of runtime context.
// 5. context_id is not accepted from the client.
// 6. This composable does not interpret primary_key.
// 7. This composable does not interpret where_clause.
// 8. This composable does not create parm[n].
// 9. Runtime state is cleared when the request fails.
// 10. No page-specific API URL is hard-coded.