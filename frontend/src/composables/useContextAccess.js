// =============================================
// File:
// frontend/src/composables/useContextAccess.js
//
// Description:
// Load authorized panels for a Cartable component
//
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// Last Modified: 2026-10-08 12:40 (Asia/Baku)
// =============================================
import { ref } from 'vue'
import axios from '@/utils/axiosInstance'

export function useContextAccess() {
  const accessList = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchContextAccess(
    cartableKey,
    contextId = null
  ) {
    if (!cartableKey) {
      accessList.value = []
      error.value = null
      return []
    }

    loading.value = true
    error.value = null

    try {
      const response = await axios.get(
        '/access/cartable_panels',
        {
          params: {
            cartable_key: cartableKey,
            context_id: contextId
          }
        }
      )

      accessList.value = (
        response.data || []
      )
        .filter(
          entry => Boolean(
            entry?.panel_key
          )
        )
        .map(
          entry => ({
            panelKey:
              entry.panel_key,
            panelType:
              entry.panel_type || 'PAGE',
            panelDescription: entry.panel_description || null,
            descriptionSource: entry.description_source || null,
            state:
              entry.state,
            accLevel:
              entry.acc_level,
            accStart:
              entry.acc_start,
            accEnd:
              entry.acc_end
          })
        )

      return accessList.value
    } catch (err) {
      console.error(
        'useContextAccess: failed to load authorized Cartable panels',
        err
      )

      error.value =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to load Cartable panels'

      accessList.value = []

      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    accessList,
    loading,
    error,
    fetchContextAccess
  }
}

// Important Learning Points:
// 1. Cartable panels are resolved by cartable_key.
// 2. context_id is transported as runtime context only.
// 3. User identity is resolved securely by backend authentication.
// 4. Panel authorization remains controlled by backend access rules.
// 5. No panel names are hard-coded in the frontend.
// 6. panelKey identifies the PAGE or FUNCTION according to panelType.
// 7. panelType distinguishes PAGE from FUNCTION.
// 8. This composable does not interpret primary_key.
// 9. This composable does not interpret where_clause.
// 10. This composable does not create parm[n].
// 11. Selected-record data remains outside panel authorization.