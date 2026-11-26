// =============================================
// File:
// frontend/src/composables/usePageRecordCount.js
//
// Description:
// Resolve metadata-driven Grid record counts for navigation badges
//
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// Last Modified: 2026-11-26 (Asia/Baku)
// =============================================
import axios from '@/utils/axiosInstance'
import { useComponentWhere } from '@/composables/useComponentWhere'

const { resolveWhere } = useComponentWhere()

function buildWhereParams(filters = {}) {
  return Object.fromEntries(
    Object.entries(filters).map(([field, value]) => [
      `where_clause[${field}]`,
      value
    ])
  )
}

export async function fetchPageRecordCount(
  pageKey,
  {
    selectedRecord = null,
    runtimeContext = {},
    fieldMode = 'list'
  } = {}
) {
  if (!pageKey) return null

  const runtimeResponse = await axios.get(
    `/runtime/${encodeURIComponent(pageKey)}`
  )
  const components = runtimeResponse.data?.components || []
  const grid = components.find(item =>
    item?.component_name &&
    String(item.component_name).toLowerCase().includes('grid')
  )

  if (!grid?.component_name) return null

  const scope = await resolveWhere({
    component_name: grid.component_name,
    field_mode: fieldMode,
    selected_record: selectedRecord || {},
    runtime_context: runtimeContext || {}
  })

  const response = await axios.get(
    `/dw/${encodeURIComponent(grid.component_name)}/count/data`,
    {
      params: buildWhereParams(scope?.filters || {})
    }
  )

  return Number.isFinite(Number(response.data?.count))
    ? Number(response.data.count)
    : null
}

// Important Learning Points:
// 1. Page-to-Grid resolution comes from authenticated page runtime metadata.
// 2. Grid scope is resolved by the centralized where_clause service.
// 3. Record counts are computed by the backend without transferring Grid rows.
// 4. Selected-record and runtime contexts remain separate.
// 5. No physical table or field names are hard-coded.
