
// =============================================
// File:
// frontend/src/composables/useComponentConfig.js
//
// Description:
// Metadata-driven component configuration client
//
// Responsibilities:
//   1. Request component configuration metadata
//   2. Normalize API field configuration
//   3. Preserve metadata-defined field ordering
//   4. Preserve physical component schema and table identity
//   5. Expose loading and error state
//   6. Keep primary_key and where_clause semantics outside this client
//
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// =============================================

import {
  ref
} from 'vue'

import axios from '@/utils/axiosInstance'

export function useComponentConfig(
  componentName,
  fieldMode = 'list'
) {
  const config = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // ----------------------------------------
  // Normalize API Response
  // ----------------------------------------
  function normalizeConfig(data) {
    if (Array.isArray(data)) {
      const fields = {}
      const rows = [...data].sort(
        (a, b) =>
          (a?.ordering_index ?? 0) -
          (b?.ordering_index ?? 0)
      )

      const fieldOrder = []

      for (const row of rows) {
        if (!row?.field_name) {
          continue
        }

        fields[row.field_name] = {
          ...row,
          required: row.null_able === false
        }

        fieldOrder.push(row.field_name)
      }

      const firstRow = rows[0] || {}

      return {
        schema_name:
          firstRow.schema_name ??
          firstRow.schm_name ??
          null,

        table_name:
          firstRow.table_name ??
          firstRow.tbl_name ??
          null,

        fields,
        field_order: fieldOrder
      }
    }

    if (
      data &&
      typeof data === 'object' &&
      !Array.isArray(data)
    ) {
      const fields =
        data.fields &&
        typeof data.fields === 'object'
          ? data.fields
          : {}

      const fieldOrder =
        Array.isArray(data.field_order)
          ? data.field_order
          : Object.keys(fields)

      return {
        ...data,

        schema_name:
          data.schema_name ??
          data.schm_name ??
          null,

        table_name:
          data.table_name ??
          data.tbl_name ??
          null,

        fields,
        field_order: fieldOrder
      }
    }

    return {
      schema_name: null,
      table_name: null,
      fields: {},
      field_order: []
    }
  }

  // ----------------------------------------
  // API Call
  // ----------------------------------------
  async function fetchConfig() {
    if (!componentName) {
      config.value = null
      error.value = new Error(
        'Component name is required'
      )
      return null
    }

    if (!fieldMode) {
      config.value = null
      error.value = new Error(
        'Field mode is required'
      )
      return null
    }

    loading.value = true
    error.value = null

    try {
      const response = await axios.get(
        '/config/component_config',
        {
          params: {
            component_name: componentName,
            field_mode: fieldMode
          }
        }
      )

      config.value = normalizeConfig(
        response.data
      )

      return config.value

    } catch (err) {
      console.error(
        'useComponentConfig: failed to fetch component configuration',
        err
      )

      error.value =
        err?.response?.data?.detail ||
        err?.message ||
        err

      config.value = null

      throw err

    } finally {
      loading.value = false
    }
  }

  // ----------------------------------------
  // Clear Configuration
  // ----------------------------------------
  function clearConfig() {
    config.value = null
    error.value = null
  }

  return {
    config,
    loading,
    error,
    fetchConfig,
    clearConfig
  }
}

// Important Learning Points:
// 1. useComponentConfig is a metadata transport and normalization layer.
// 2. Component identity is defined by component_name + field_mode.
// 3. Field ordering comes from metadata.
// 4. Physical component identity includes schema_name and table_name.
// 5. primary_key is not interpreted here.
// 6. where_clause is not interpreted here.
// 7. parm[n] is not created or resolved here.
// 8. Record identity is not created here.
// 9. No table-specific field assumptions are hard-coded.
