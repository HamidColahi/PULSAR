// =============================================
// File:
// frontend/src/composables/useComponentWhere.js
//
// Description:
// Metadata driven where_clause resolver client
//
// Responsibilities:
//   1. Send target component metadata identifiers
//   2. Send selected record without interpreting where_clause
//   3. Send runtime context separately
//   4. Receive resolved parm[n] and filters
//
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// =============================================
import axiosInstance from '@/utils/axiosInstance'
export function useComponentWhere() {
  async function resolveWhere(payload = {}) {
    const request = {
      component_name: payload.component_name,
      field_mode: payload.field_mode || 'list',
      selected_record: payload.selected_record || {},
      runtime_context: payload.runtime_context || {}
    }
    /* console.log(
      'useComponentWhere: INPUT',
      request
    ) */
    const response =
      await axiosInstance.post(
        '/runtime/resolve_where_clause',
        request
      )
    /* console.log(
      'useComponentWhere: OUTPUT',
      response.data
    ) */
    return response.data
  }
  return {
    resolveWhere
  }
}