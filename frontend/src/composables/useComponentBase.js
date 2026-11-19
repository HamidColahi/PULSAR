// =============================================
// File:
// frontend/src/composables/useComponentBase.js
//
// Description:
// Metadata-driven component base configuration client
//
// Responsibilities:
//   1. Request component base metadata
//   2. Transport component_name and field_mode
//   3. Expose loading and error state
//   4. Keep primary_key semantics outside the client
//   5. Keep where_clause semantics outside the client
//
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// =============================================
import {
  ref
} from 'vue'
import axios from '@/utils/axiosInstance'

export function useComponentBase(
  componentName,
  fieldMode = 'list'
) {
  const baseConfig = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchBase() {
    if (!componentName) {
      baseConfig.value = null
      error.value = new Error(
        'Component name is required'
      )
      return null
    }

    loading.value = true
    error.value = null

    try {
      const response =
        await axios.get(
          '/config/component_base',
          {
            params: {
              component_name:
                componentName,
              field_mode:
                fieldMode
            }
          }
        )

      baseConfig.value =
        response.data

      return baseConfig.value
    } catch (err) {
      console.error(
        'useComponentBase: failed to fetch component base',
        err
      )

      error.value =
        err?.response?.data?.detail ||
        err?.message ||
        err

      baseConfig.value = null

      throw err
    } finally {
      loading.value = false
    }
  }

  function clearBase() {
    baseConfig.value = null
    error.value = null
  }

  return {
    baseConfig,
    loading,
    error,
    fetchBase,
    clearBase
  }
}

// Important Learning Points:
// 1. useComponentBase is a metadata transport layer.
// 2. component_name and field_mode define the requested metadata.
// 3. primary_key is received as metadata only and is not interpreted here.
// 4. where_clause is received as metadata only and is not interpreted here.
// 5. parm[n] is not created or resolved here.
// 6. Record identity is not created here.
// 7. Backend metadata remains the source of truth.
// 8. No component-specific fields are hard-coded.