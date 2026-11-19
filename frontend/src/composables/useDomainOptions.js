
// ===============================================
// File:
// frontend/src/composables/useDomainOptions.js
//
// Description:
// Composable for loading metadata-driven domain options
//
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// ===============================================

import {
  ref,
  watch,
  computed,
  unref
} from 'vue'

import axios from '@/utils/axiosInstance'

import {
  language
} from '@/stores/uiStore'

// --------------------------------------------------
// Domain Identity Resolver
// --------------------------------------------------
function normalizeDomainIdentity(domainConfig) {
  const source = unref(domainConfig)

  if (
    !source ||
    typeof source !== 'object' ||
    Array.isArray(source)
  ) {
    return {
      schemaName: undefined,
      tableName: undefined,
      fieldName: undefined
    }
  }

  function firstValue(...values) {
    for (const value of values) {
      const resolved = unref(value)

      if (
        resolved !== undefined &&
        resolved !== null &&
        resolved !== ''
      ) {
        return resolved
      }
    }

    return undefined
  }

  return {
    schemaName: firstValue(
      source.schemaName,
      source.schema_name,
      source.schm_name
    ),

    tableName: firstValue(
      source.tableName,
      source.table_name,
      source.tbl_name
    ),

    fieldName: firstValue(
      source.fieldName,
      source.field_name
    )
  }
}

// --------------------------------------------------
// Option Normalizer
// --------------------------------------------------
function normalizeDomainOptions(data) {
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
// Domain Options API
// --------------------------------------------------
async function requestDomainOptions(
  identity,
  languageCode
) {
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

  const response = await axios.get(
    '/common/domain_options',
    {
      params: {
        schema_name: schemaName,
        table_name: tableName,
        field_name: fieldName,
        language_code: languageCode
      }
    }
  )

  return normalizeDomainOptions(
    response.data
  )
}

// --------------------------------------------------
// Single Domain Options
//
// Backward-compatible API used by Grid and Search.
// --------------------------------------------------
export function useDomainOptions(domainConfig) {
  const options = ref([])

  const currentLanguage = computed(
    () => language.value || 'en'
  )

  const domainIdentity = computed(
    () => normalizeDomainIdentity(
      domainConfig
    )
  )

  let latestRequestId = 0

  async function fetchOptions() {
    const requestId = ++latestRequestId

    const identity = domainIdentity.value

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
      options.value = []
      return []
    }

    try {
      const result = await requestDomainOptions(
        identity,
        currentLanguage.value
      )

      if (requestId !== latestRequestId) {
        return options.value
      }

      options.value = result

      return options.value

    } catch (err) {
      if (requestId !== latestRequestId) {
        return options.value
      }

      console.warn(
        'useDomainOptions: failed to load options',
        {
          schemaName,
          tableName,
          fieldName,
          error: err
        }
      )

      options.value = []

      return []
    }
  }

  watch(
    [
      domainIdentity,
      currentLanguage
    ],
    fetchOptions,
    {
      immediate: true,
      deep: true
    }
  )

  return options
}

// --------------------------------------------------
// Multiple Domain Options
//
// Manages all DDLB fields of a dynamic form
// through one reactive composable instance.
// --------------------------------------------------
export function useDomainOptionsMap(domainConfigs) {
  const optionsMap = ref({})

  const currentLanguage = computed(
    () => language.value || 'en'
  )

  const normalizedDomains = computed(() => {
    const source = unref(domainConfigs)

    if (
      !source ||
      typeof source !== 'object' ||
      Array.isArray(source)
    ) {
      return {}
    }

    const result = {}

    for (const [key, config] of Object.entries(source)) {
      result[key] = normalizeDomainIdentity(
        config
      )
    }

    return result
  })

  let latestRequestId = 0

  async function fetchOptionsMap() {
    const requestId = ++latestRequestId

    const domains = normalizedDomains.value
    const languageCode = currentLanguage.value

    const entries = Object.entries(domains)

    if (entries.length === 0) {
      optionsMap.value = {}
      return {}
    }

    const results = await Promise.all(
      entries.map(
        async ([field, identity]) => {
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
            console.warn(
              'useDomainOptionsMap: incomplete domain identity',
              {
                formField: field,
                identity
              }
            )

            return [
              field,
              []
            ]
          }

          try {
            const options = await requestDomainOptions(
              identity,
              languageCode
            )

            return [
              field,
              options
            ]

          } catch (err) {
            console.warn(
              'useDomainOptionsMap: failed to load options',
              {
                formField: field,
                schemaName,
                tableName,
                fieldName,
                error: err
              }
            )

            return [
              field,
              []
            ]
          }
        }
      )
    )

    if (requestId !== latestRequestId) {
      return optionsMap.value
    }

    optionsMap.value = Object.fromEntries(
      results
    )

    return optionsMap.value
  }

  watch(
    [
      normalizedDomains,
      currentLanguage
    ],
    fetchOptionsMap,
    {
      immediate: true,
      deep: true
    }
  )

  return optionsMap
}

// --------------------------------------------------
// Important Learning Points
// --------------------------------------------------
// 1. Domain identity is defined by schema, table, and field.
// 2. field_domain_values is the source of DDLB options.
// 3. The active language is obtained from uiStore metadata.
// 4. Domain labels are resolved by the backend service.
// 5. Language changes automatically reload domain options.
// 6. Metadata changes automatically reload domain options.
// 7. Outdated asynchronous responses are ignored.
// 8. Missing or invalid domain metadata results in empty options.
// 9. No domain values are hard-coded in the frontend.
// 10. This composable does not interpret primary_key.
// 11. This composable does not interpret where_clause.
// 12. This composable does not create or resolve parm[n].
// 13. useDomainOptions supports individual Grid and Search domains.
// 14. useDomainOptionsMap manages multiple domains for dynamic forms.
