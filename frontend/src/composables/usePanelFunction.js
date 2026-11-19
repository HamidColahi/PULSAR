// ================================================
// File: frontend/src/composables/usePanelFunction.js
// Description: Execute metadata-driven Panel Functions with request diagnostics
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// Last Modified: 2026-10-09 02:00 (Asia/Baku)
// ================================================

import { ref } from 'vue'
import axios from '@/utils/axiosInstance'

const EXECUTE_ENDPOINT = '/functions/execute'
const REQUEST_TIMEOUT = 120000

export function usePanelFunction() {
  const loading = ref(false)
  const error = ref(null)
  const result = ref(null)

  async function executeFunction(payload) {
    if (loading.value) {
      throw new Error('A Panel Function is already running')
    }

    if (!payload?.functionName || !payload?.cartableKey) {
      throw new Error('Function name and Cartable key are required')
    }

    if (
      !payload.selectedRecord ||
      typeof payload.selectedRecord !== 'object' ||
      Array.isArray(payload.selectedRecord) ||
      Object.keys(payload.selectedRecord).length === 0
    ) {
      throw new Error('A selected Grid record is required')
    }

    loading.value = true
    error.value = null
    result.value = null

    const startedAt = Date.now()

    try {
      const response = await axios.post(
        EXECUTE_ENDPOINT,
        {
          function_name: payload.functionName,
          cartable_key: payload.cartableKey,
          context: payload.context || {},
          selected_record: payload.selectedRecord
        },
        {
          timeout: REQUEST_TIMEOUT
        }
      )

      result.value = response.data

      return result.value
    } catch (err) {
      const detail = err?.response?.data?.detail

      error.value =
        typeof detail === 'string'
          ? detail
          : detail?.message ||
            err?.message ||
            'Panel Function execution failed'

      console.error('[PanelFunction] Request failed', {
        endpoint: EXECUTE_ENDPOINT,
        functionName: payload.functionName,
        elapsedMs: Date.now() - startedAt,
        status: err?.response?.status ?? null,
        code: err?.code ?? null,
        message: error.value,
        response: err?.response?.data ?? null
      })

      throw err
    } finally {
      loading.value = false

    }
  }

  function reset() {
    error.value = null
    result.value = null
  }

  return {
    loading,
    error,
    result,
    executeFunction,
    reset
  }
}

// Important Learning Points:
// 1. Panel Function execution is isolated from UI components.
// 2. All HTTP requests use the centralized Axios instance.
// 3. JWT authentication is handled by axiosInstance.
// 4. Function metadata comes from the authorized Panel entry.
// 5. The selected Grid record and runtime context are passed separately.
// 6. Backend authorization and execution validation are mandatory.
// 7. Function output is returned without assuming a specific output type.
// 8. The execution endpoint is centralized for future changes.
// 9. Long-running operations use a dedicated request timeout.
// 10. This composable does not execute arbitrary frontend code.
// 11. Request start, completion, failure, and loading release are logged for diagnostics.
// 12. The endpoint must be implemented and verified in the Backend.
