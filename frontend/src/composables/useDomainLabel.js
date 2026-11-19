
// ===============================================
// File:
// frontend/src/composables/useDomainLabel.js
//
// Description:
// Reactive domain options cache and translated label resolver
//
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// ===============================================

import {
  reactive,
  computed,
  unref
} from 'vue'

import {
  language
} from '@/stores/uiStore'


// --------------------------------------------------
// Domain Cache
// --------------------------------------------------
const domainCache = reactive({})

const pendingRequests = new Map()


// --------------------------------------------------
// Domain Identity
// --------------------------------------------------
function normalizeDomainIdentity(domainConfig) {

  const source = unref(domainConfig) || {}

  function readValue(...keys) {

    for (const key of keys) {

      const value = unref(source[key])

      if (
        value !== undefined &&
        value !== null &&
        String(value).trim() !== ''
      ) {
        return String(value).trim()
      }
    }

    return null
  }

  return {
    schemaName: readValue(
      'schemaName',
      'schema_name',
      'schm_name'
    ),

    tableName: readValue(
      'tableName',
      'table_name',
      'tbl_name'
    ),

    fieldName: readValue(
      'fieldName',
      'field_name'
    )
  }
}


// --------------------------------------------------
// Cache Key
// --------------------------------------------------
function createDomainCacheKey(
  domainConfig,
  languageCode
) {

  const identity = normalizeDomainIdentity(
    domainConfig
  )

  const {
    schemaName,
    tableName,
    fieldName
  } = identity

  if (
    !schemaName ||
    !tableName ||
    !fieldName ||
    !languageCode
  ) {
    return null
  }

  return JSON.stringify([
    schemaName,
    tableName,
    fieldName,
    languageCode
  ])
}


// --------------------------------------------------
// Domain Options Normalization
// --------------------------------------------------
function normalizeOptions(data) {

  if (!Array.isArray(data)) {
    return []
  }

  return data
    .filter(
      item =>
        item &&
        item.value !== undefined &&
        item.value !== null
    )
    .map(
      item => ({
        value: item.value,
        label: item.label ?? item.value
      })
    )
}


// --------------------------------------------------
// Domain Label Resolver
// --------------------------------------------------
export function useDomainLabel(domainConfig) {

  const domainIdentity = computed(
    () => normalizeDomainIdentity(
      domainConfig
    )
  )

  const currentLanguage = computed(
    () => language.value || 'en'
  )

  return (value) => {

    if (
      value === undefined ||
      value === null
    ) {
      return value
    }

    const cacheKey = createDomainCacheKey(
      domainIdentity.value,
      currentLanguage.value
    )

    if (!cacheKey) {
      return value
    }

    const options =
      domainCache[cacheKey] || []

    const normalizedValue =
      typeof value === 'string'
        ? value.trim()
        : value

    const match = options.find(
      option =>
        String(option.value) ===
        String(normalizedValue)
    )

    return match
      ? match.label
      : value
  }
}


// --------------------------------------------------
// Preload Domain Options
// --------------------------------------------------
export async function preloadDomainOptions(
  domainConfig,
  axiosInstance,
  languageCode,
  apiUrl = '/common/domain_options'
) {

  const resolvedLanguage = String(
    unref(languageCode) || ''
  ).trim()

  if (!resolvedLanguage) {
    throw new Error(
      'languageCode parameter is required for preloadDomainOptions.'
    )
  }

  if (
    !axiosInstance ||
    typeof axiosInstance.get !== 'function'
  ) {
    throw new Error(
      'A valid axiosInstance is required for preloadDomainOptions.'
    )
  }

  const identity = normalizeDomainIdentity(
    domainConfig
  )

  const {
    schemaName,
    tableName,
    fieldName
  } = identity

  if (
    !schemaName ||
    !tableName ||
    !fieldName
  ) {
    return []
  }

  const cacheKey = createDomainCacheKey(
    identity,
    resolvedLanguage
  )

  if (
    Object.prototype.hasOwnProperty.call(
      domainCache,
      cacheKey
    )
  ) {
    return domainCache[cacheKey]
  }

  // Reuse an already running request for the same domain and language.
  if (pendingRequests.has(cacheKey)) {
    return pendingRequests.get(cacheKey)
  }

  const request = (async () => {

    try {

      const response = await axiosInstance.get(
        apiUrl,
        {
          params: {
            schema_name: schemaName,
            table_name: tableName,
            field_name: fieldName,
            language_code: resolvedLanguage
          }
        }
      )

      const options = normalizeOptions(
        response.data
      )

      domainCache[cacheKey] = options

      return options

    } catch (error) {

      console.error(
        'Failed to preload domain options',
        {
          schemaName,
          tableName,
          fieldName,
          languageCode: resolvedLanguage,
          error
        }
      )

      return []

    } finally {

      pendingRequests.delete(cacheKey)

    }

  })()

  pendingRequests.set(
    cacheKey,
    request
  )

  return request
}


// --------------------------------------------------
// Reactive Domain Options
// --------------------------------------------------
export function useDomainOptions(domainConfig) {

  const domainIdentity = computed(
    () => normalizeDomainIdentity(
      domainConfig
    )
  )

  const currentLanguage = computed(
    () => language.value || 'en'
  )

  return computed(() => {

    const cacheKey = createDomainCacheKey(
      domainIdentity.value,
      currentLanguage.value
    )

    return cacheKey
      ? domainCache[cacheKey] || []
      : []
  })
}


// --------------------------------------------------
// Domain Cache Debugging
// --------------------------------------------------
export function debugDomainCache() {

  return JSON.parse(
    JSON.stringify(domainCache)
  )
}


// ===============================================
// Important Learning Points
// ===============================================
// 1. field_domain_values is the source of DDLB options.
// 2. Domain identity consists of schema, table, and field.
// 3. Cache entries are isolated by domain identity and language.
// 4. Translation is resolved globally by the backend.
// 5. domain_value remains the actual stored field value.
// 6. Language changes select a different cache entry.
// 7. Metadata changes select a different domain cache entry.
// 8. Duplicate concurrent requests are prevented.
// 9. Missing translations fall back to the original value.
// 10. Failed requests are not permanently cached.
// 11. DDLB values are not hard-coded in the frontend.
// 12. DDDW options are not handled by this module.
