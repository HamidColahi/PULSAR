
/*
 File: Pulsar/frontend/src/composables/useComponentData.js
 Description: Metadata-driven dynamic component data client
 Responsibilities:
   1. Transport dynamic component CRUD requests
   2. Build runtime DataWindow URLs
   3. Pass record identity as an opaque value
   4. Manage loading, error, and list-record state
   5. Support multipart FormData payloads
   6. Transport binary file download requests
   7. Keep primary_key and where_clause semantics outside
      the data transport layer
 Author: MHKolahi@gmail.com
 In collaboration with GPT4 Chat Assistant: Bahram
 Last Modified: 2026-11-16 11:36 (Asia/Baku)
*/

import { ref } from 'vue'
import axios from '@/utils/axiosInstance'

export function useComponentData(
  componentName,
  schemaName = 'pulsar',
  fieldMode = 'list'
) {
  const records = ref([])
  const loading = ref(false)
  const error = ref(null)

  // ---------------------------
  // Identity Transport
  // ---------------------------
  function normalizeRecordKey(id) {
    if (
      id === null ||
      id === undefined ||
      id === ''
    ) {
      throw new Error(
        'Record identity cannot be empty'
      )
    }

    return String(id)
  }

  // ---------------------------
  // URL Builder
  // ---------------------------
  function buildUrl({
    id = null,
    mode = fieldMode
  } = {}) {
    const base =
      `/dw/${String(componentName)}`

    switch (mode) {
      case 'view':
      case 'update':
      case 'delete':
        if (
          id === null ||
          id === undefined ||
          id === ''
        ) {
          throw new Error(
            `Mode "${mode}" requires a record identity`
          )
        }

        return (
          `${base}/${mode}/data/` +
          `${normalizeRecordKey(id)}`
        )

      case 'insert':
        return `${base}/insert/data`

      case 'list':
      case 'report':
        return `${base}/${mode}/data`

      default:
        throw new Error(
          `Unsupported mode: ${mode}`
        )
    }
  }

  // ---------------------------
  // File Download URL Builder
  // ---------------------------
  function buildFileUrl({
    id,
    fieldName
  } = {}) {
    if (
      fieldName === null ||
      fieldName === undefined ||
      String(fieldName).trim() === ''
    ) {
      throw new Error(
        'File field name cannot be empty'
      )
    }

    const identity = normalizeRecordKey(id)

    return (
      `/dw/${encodeURIComponent(String(componentName))}` +
      `/file/${encodeURIComponent(identity)}` +
      `/${encodeURIComponent(String(fieldName))}`
    )
  }

  // ---------------------------
  // Download Filename Resolver
  // ---------------------------
  function resolveDownloadFilename(
    contentDisposition,
    fallbackName
  ) {
    if (!contentDisposition) {
      return fallbackName
    }

    const encodedMatch =
      contentDisposition.match(
        /filename\*\s*=\s*(?:UTF-8'')?([^;]+)/i
      )

    if (encodedMatch?.[1]) {
      const encodedName = encodedMatch[1]
        .trim()
        .replace(/^["']|["']$/g, '')

      try {
        return decodeURIComponent(encodedName)
      } catch {
        return encodedName
      }
    }

    const regularMatch =
      contentDisposition.match(
        /filename\s*=\s*(?:"([^"]+)"|([^;]+))/i
      )

    if (regularMatch) {
      return (
        regularMatch[1] ||
        regularMatch[2]?.trim() ||
        fallbackName
      )
    }

    return fallbackName
  }

  // ---------------------------
  // Unified Request Handler
  // ---------------------------
  async function request(
    method,
    url,
    payload = null,
    params = {}
  ) {
    loading.value = true
    error.value = null

    const finalParams =
      schemaName
        ? {
            schema: schemaName,
            ...params
          }
        : params

    try {
      let response

      if (
        (
          method === 'get' ||
          method === 'delete'
        ) &&
        Object.keys(finalParams).length > 0
      ) {
        response = await axios({
          method,
          url,
          params: finalParams
        })
      } else if (
        method === 'post' ||
        method === 'put'
      ) {
        response = await axios({
          method,
          url,
          data: payload,
          params: finalParams
        })
      } else {
        response = await axios({
          method,
          url,
          params: finalParams
        })
      }

      return response.data
    } catch (err) {
      error.value =
        err?.response?.data?.detail ||
        err?.message ||
        'Component data request failed'

      throw err
    } finally {
      loading.value = false
    }
  }

  // ---------------------------
  // Universal CRUD Loader
  // ---------------------------
  async function loadData({
    mode = 'list',
    id = null,
    payload = null,
    params = {},
    autoAssign = true
  } = {}) {
    const url =
      buildUrl({
        id,
        mode
      })

    let method = 'get'

    switch (mode) {
      case 'insert':
        method = 'post'
        break

      case 'update':
        method = 'put'
        break

      case 'delete':
        method = 'delete'
        break

      default:
        method = 'get'
    }

    const data =
      await request(
        method,
        url,
        payload,
        params
      )

    if (
      mode === 'list' &&
      autoAssign
    ) {
      records.value =
        Array.isArray(data)
          ? data
          : []
    }

    return data
  }

  // ---------------------------
  // Binary File Download
  // ---------------------------
  async function downloadFile({
    id,
    fieldName,
    params = {}
  } = {}) {
    const url = buildFileUrl({
      id,
      fieldName
    })

    const finalParams =
      schemaName
        ? {
            schema: schemaName,
            ...params
          }
        : params

    loading.value = true
    error.value = null

    try {
      const response = await axios({
        method: 'get',
        url,
        params: finalParams,
        responseType: 'blob'
      })

      const contentDisposition =
        response.headers?.['content-disposition'] || ''

      const contentType =
        response.headers?.['content-type'] ||
        'application/octet-stream'

      const filename = resolveDownloadFilename(
        contentDisposition,
        String(fieldName)
      )

      return {
        blob: response.data,
        filename,
        contentType
      }
    } catch (err) {
      error.value =
        err?.response?.data?.detail ||
        err?.message ||
        'File download failed'

      throw err
    } finally {
      loading.value = false
    }
  }

  // ---------------------------
  // CRUD Helper Methods
  // ---------------------------
  async function viewData(id) {
    return await loadData({
      mode: 'view',
      id,
      autoAssign: false
    })
  }

  async function insertData(payload) {
    return await loadData({
      mode: 'insert',
      payload,
      autoAssign: false
    })
  }

  async function updateData(
    id,
    payload
  ) {
    return await loadData({
      mode: 'update',
      id,
      payload,
      autoAssign: false
    })
  }

  async function deleteData(id) {
    return await loadData({
      mode: 'delete',
      id,
      autoAssign: false
    })
  }

  return {
    records,
    loading,
    error,
    buildUrl,
    buildFileUrl,
    loadData,
    downloadFile,
    viewData,
    insertData,
    updateData,
    deleteData
  }
}

// Important Learning Points:
// 1. useComponentData is a transport/execution layer only.
// 2. Record identity is treated as an opaque runtime value.
// 3. Composite primary-key parsing does not belong here.
// 4. Primary-key semantics belong to component_key.py.
// 5. where_clause semantics belong to component_where.py.
// 6. Query filters are passed through params without semantic interpretation.
// 7. Database type conversion remains a backend responsibility.
// 8. FormData payloads are passed directly to Axios.
// 9. Multipart Content-Type and boundary are delegated to Axios and the browser.
// 10. Binary downloads are returned as Blob data with filename metadata.
// 11. File field names are transport parameters, not business-field assumptions.
// 12. Record identity remains opaque during file download.
// 13. File authorization and record scope validation remain backend responsibilities.
// 14. No table-specific field or primary-key logic is hard-coded.
