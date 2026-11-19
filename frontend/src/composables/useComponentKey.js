// =============================================
// File:
// frontend/src/composables/useComponentKey.js
//
// Description:
// Metadata driven primary-key resolver client
//
// Responsibilities:
//   1. Send component metadata identifiers
//   2. Send the selected record without interpreting primary_key
//   3. Receive centralized primary-key resolution results
//
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// =============================================
import axiosInstance from '@/utils/axiosInstance'
export function useComponentKey() {
  async function resolveKey(payload = {}) {
    const request = {
      component_name:
        payload.component_name,
      field_mode:
        payload.field_mode || 'list',
      record:
        payload.record || {}
    }
    /* console.log(
      'useComponentKey: INPUT',
      request
    ) */
    const response =
      await axiosInstance.post(
        '/runtime/resolve_component_key',
        request
      )
    /* console.log(
      'useComponentKey: OUTPUT',
      response.data
    ) */
    return response.data
  }
  return {
    resolveKey
  }
}