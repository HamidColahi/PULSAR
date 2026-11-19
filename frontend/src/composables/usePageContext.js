// =============================================
// File: frontend/src/composables/usePageContext.js
// Description: Dynamic, metadata-aware page context collector for PULSAR
// Change Date: 2026-10-23 15:25; Timezone: Asia/Baku
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// =============================================
import {
  ref,
  unref
} from 'vue'

const MAX_TEXT_LENGTH = 500
const MAX_ITEMS_PER_GROUP = 200
const SENSITIVE_KEY_PATTERN =
  /(password|passwd|secret|token|credential|authorization|cookie|api[_-]?key|private[_-]?key|ssn|credit[_-]?card)/i

function asObject(value) {
  const resolved = unref(value)

  return resolved &&
    typeof resolved === 'object' &&
    !Array.isArray(resolved)
    ? resolved
    : {}
}

function cleanText(value, maxLength = MAX_TEXT_LENGTH) {
  if (typeof value !== 'string') return ''

  return value
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, maxLength)
}

function uniqueStrings(values) {
  return [...new Set(
    values
      .map(value => cleanText(value, 200))
      .filter(Boolean)
  )]
}

function scalarValue(value) {
  return value === null ||
    ['string', 'number', 'boolean'].includes(typeof value)
}

function redactRecord(record) {
  if (!record || typeof record !== 'object' || Array.isArray(record)) {
    return null
  }

  const safeRecord = {}

  for (const [key, value] of Object.entries(record)) {
    if (SENSITIVE_KEY_PATTERN.test(key)) continue
    if (!scalarValue(value)) continue

    safeRecord[key] = value
  }

  return safeRecord
}

function isElementVisible(element) {
  if (!element || element.hidden) return false
  if (element.getAttribute?.('aria-hidden') === 'true') return false

  if (typeof window !== 'undefined' && typeof window.getComputedStyle === 'function') {
    const style = window.getComputedStyle(element)

    if (
      style.display === 'none' ||
      style.visibility === 'hidden' ||
      style.visibility === 'collapse'
    ) {
      return false
    }
  }

  if (typeof element.getClientRects === 'function') {
    return element.getClientRects().length > 0
  }

  return true
}

function elementText(element) {
  return cleanText(
    element?.innerText ||
    element?.textContent ||
    ''
  )
}

function getAccessibleLabel(element) {
  if (!element) return ''

  const ariaLabel = cleanText(element.getAttribute?.('aria-label'))
  if (ariaLabel) return ariaLabel

  const labelledBy = cleanText(element.getAttribute?.('aria-labelledby'))

  if (labelledBy && typeof document !== 'undefined') {
    const text = labelledBy
      .split(/\s+/)
      .map(id => document.getElementById(id))
      .filter(Boolean)
      .map(elementText)
      .filter(Boolean)
      .join(' ')

    if (text) return cleanText(text)
  }

  if (element.labels?.length) {
    const labels = [...element.labels]
      .map(elementText)
      .filter(Boolean)
      .join(' ')

    if (labels) return labels
  }

  const wrappingLabel = element.closest?.('label')
  if (wrappingLabel) {
    const labelText = elementText(wrappingLabel)
    if (labelText) return labelText
  }

  return cleanText(
    element.getAttribute?.('title') ||
    element.getAttribute?.('placeholder') ||
    elementText(element)
  )
}

function collectVisibleActions(root) {
  const selectors = [
    'button',
    'input[type="button"]',
    'input[type="submit"]',
    'input[type="reset"]',
    '[role="button"]',
    '[role="menuitem"]',
    '[role="tab"]'
  ].join(',')

  return [...root.querySelectorAll(selectors)]
    .filter(isElementVisible)
    .slice(0, MAX_ITEMS_PER_GROUP)
    .map((element, index) => ({
      index,
      label: getAccessibleLabel(element) || `Action ${index + 1}`,
      element_type: element.tagName?.toLowerCase() || null,
      role: element.getAttribute?.('role') || null,
      action_type: element.getAttribute?.('type') || null,
      component_key:
        element.getAttribute?.('data-component-key') ||
        element.getAttribute?.('data-component-name') ||
        null,
      disabled: Boolean(
        element.disabled ||
        element.getAttribute?.('aria-disabled') === 'true'
      ),
      title: cleanText(element.getAttribute?.('title')) || null,
      action_code: cleanText(element.getAttribute?.('data-pulsar-action-code'), 100) || null,
      target_key: cleanText(element.getAttribute?.('data-pulsar-target-key'), 256) || null,
      target_type: (() => {
        const targetType = cleanText(element.getAttribute?.('data-pulsar-target-type'), 20).toUpperCase()
        return targetType || null
      })(),
      description: cleanText(element.getAttribute?.('data-pulsar-description'), 1000) || null,
      description_source: cleanText(element.getAttribute?.('data-pulsar-description-source'), 160) || null,
      description_status: cleanText(element.getAttribute?.('data-pulsar-description-status'), 40) || 'missing'
    }))
}

function collectVisibleFields(root) {
  const selectors = [
    'input',
    'textarea',
    'select',
    '[contenteditable="true"]',
    '[role="textbox"]',
    '[role="combobox"]',
    '[role="checkbox"]',
    '[role="radio"]',
    '[role="switch"]'
  ].join(',')

  return [...root.querySelectorAll(selectors)]
    .filter(isElementVisible)
    .filter(element => {
      const type = cleanText(element.getAttribute?.('type')).toLowerCase()

      return type !== 'password' &&
        type !== 'hidden' &&
        element.getAttribute?.('autocomplete') !== 'current-password' &&
        element.getAttribute?.('autocomplete') !== 'new-password'
    })
    .slice(0, MAX_ITEMS_PER_GROUP)
    .map((element, index) => {
      const selectedOption = element.tagName?.toLowerCase() === 'select'
        ? cleanText(element.selectedOptions?.[0]?.textContent)
        : ''

      return {
        index,
        label: getAccessibleLabel(element) || `Field ${index + 1}`,
        name: (() => {
          const name = cleanText(element.getAttribute?.('name'), 200)
          return name && !SENSITIVE_KEY_PATTERN.test(name) ? name : null
        })(),
        id: (() => {
          const id = cleanText(element.id, 200)
          return id && !SENSITIVE_KEY_PATTERN.test(id) ? id : null
        })(),
        element_type: element.tagName?.toLowerCase() || null,
        input_type: cleanText(element.getAttribute?.('type'), 80) || null,
        role: cleanText(element.getAttribute?.('role'), 80) || null,
        placeholder: cleanText(element.getAttribute?.('placeholder')) || null,
        required: Boolean(element.required || element.getAttribute?.('aria-required') === 'true'),
        disabled: Boolean(element.disabled || element.getAttribute?.('aria-disabled') === 'true'),
        read_only: Boolean(element.readOnly),
        selected_option_label: selectedOption || null
      }
    })
}

function collectTables(root) {
  return [...root.querySelectorAll('table,[role="table"],[role="grid"]')]
    .filter(isElementVisible)
    .slice(0, MAX_ITEMS_PER_GROUP)
    .map((table, index) => {
      const headers = [
        ...table.querySelectorAll(
          'thead th,[role="columnheader"]'
        )
      ]
        .filter(isElementVisible)
        .map(elementText)
        .filter(Boolean)

      return {
        index,
        label:
          cleanText(table.getAttribute?.('aria-label')) ||
          cleanText(table.getAttribute?.('data-component-name')) ||
          cleanText(table.getAttribute?.('data-component-key')) ||
          `Data grid ${index + 1}`,
        role: table.getAttribute?.('role') || null,
        component_key:
          table.getAttribute?.('data-component-key') ||
          table.getAttribute?.('data-component-name') ||
          null,
        column_labels: uniqueStrings(headers).slice(0, MAX_ITEMS_PER_GROUP),
        visible_row_count: [
          ...table.querySelectorAll('tbody tr,[role="row"]')
        ].filter(isElementVisible).length
      }
    })
}

function collectSemanticComponents(root) {
  const selectors = [
    '[data-component-key]',
    '[data-component-name]',
    '[data-component-type]',
    '[data-pulsar-component]',
    '[data-page-component]',
    'main',
    'nav',
    'aside',
    'form',
    '[role="dialog"]',
    '[role="region"]',
    '[role="tabpanel"]',
    '[role="tree"]',
    '[role="list"]'
  ].join(',')

  return [...root.querySelectorAll(selectors)]
    .filter(isElementVisible)
    .slice(0, MAX_ITEMS_PER_GROUP)
    .map((element, index) => ({
      index,
      technical_key:
        element.getAttribute?.('data-component-key') ||
        element.getAttribute?.('data-component-name') ||
        element.getAttribute?.('data-pulsar-component') ||
        null,
      technical_type:
        element.getAttribute?.('data-component-type') ||
        element.tagName?.toLowerCase() ||
        null,
      // Keep component labels semantic; avoid capturing arbitrary container text
      // that may include record values or other user-provided content.
      visible_label: (() => {
        const ariaLabel = cleanText(element.getAttribute?.('aria-label'))
        if (ariaLabel) return ariaLabel

        const labelledBy = cleanText(element.getAttribute?.('aria-labelledby'))
        if (labelledBy && typeof document !== 'undefined') {
          const label = labelledBy
            .split(/\s+/)
            .map(id => document.getElementById(id))
            .filter(Boolean)
            .map(elementText)
            .filter(Boolean)
            .join(' ')
          if (label) return cleanText(label)
        }

        return cleanText(element.getAttribute?.('title')) || null
      })(),
      role: element.getAttribute?.('role') || null,
      landmark: ['main', 'nav', 'aside', 'form'].includes(
        element.tagName?.toLowerCase()
      )
        ? element.tagName.toLowerCase()
        : null
    }))
}

function collectHeadings(root) {
  return uniqueStrings(
    [...root.querySelectorAll('h1,h2,h3,[role="heading"]')]
      .filter(isElementVisible)
      .map(elementText)
  ).slice(0, 50)
}

function findPageTitle(root, sourcePage) {
  const explicitTitle = cleanText(
    sourcePage.visible_title ||
    sourcePage.title ||
    sourcePage.page_title
  )

  if (explicitTitle) return explicitTitle

  const heading = root.querySelector('h1,[role="heading"][aria-level="1"]')
  const headingText = isElementVisible(heading) ? elementText(heading) : ''

  if (headingText) return headingText

  if (typeof document !== 'undefined') {
    return cleanText(document.title) || null
  }

  return null
}

function collectRuntimeSignals(root) {
  const visibleAlerts = [
    ...root.querySelectorAll(
      '[role="alert"],[role="status"],[aria-live="assertive"],[aria-live="polite"]'
    )
  ]
    .filter(isElementVisible)
    .map(elementText)
    .filter(Boolean)
    .slice(0, 30)

  const visibleDialogs = [
    ...root.querySelectorAll('[role="dialog"],dialog[open]')
  ]
    .filter(isElementVisible)
    .map(element => ({
      label: getAccessibleLabel(element) || elementText(element) || null,
      modal: element.getAttribute?.('aria-modal') === 'true'
    }))
    .slice(0, 20)

  return {
    headings: collectHeadings(root),
    visible_alerts: visibleAlerts,
    visible_dialogs: visibleDialogs
  }
}

export function usePageContext(options = {}) {
  const context = ref(null)
  const lastCollectedAt = ref(null)
  const error = ref(null)

  function resolveRoot(rootElement = null) {
    if (
      rootElement &&
      typeof rootElement.querySelectorAll === 'function'
    ) {
      return rootElement
    }

    if (typeof document === 'undefined') return null

    const selector = options.rootSelector || '.pulsar-shell'
    return document.querySelector(selector) || document.body || null
  }

  function collectPageContext({
    sourceContext = {},
    rootElement = null,
    pageTitle = null,
    languageCode = null
  } = {}) {
    try {
      const source = asObject(sourceContext)
      const sourcePage = asObject(source.page)
      const sourceNavigation = asObject(source.navigation)
      const sourceUiState = asObject(source.ui_state)
      const sourceGrid = asObject(source.grid)
      const sourceDataContext = asObject(source.data_context)
      const root = resolveRoot(rootElement)

      const page = {
        ...sourcePage,
        technical_key:
          sourcePage.technical_key ||
          sourcePage.page_key ||
          sourcePage.page_title_key ||
          null,
        page_key: sourcePage.page_key || sourcePage.technical_key || null,
        page_title_key: sourcePage.page_title_key || null,
        visible_title:
          cleanText(pageTitle) ||
          (root ? findPageTitle(root, sourcePage) : findPageTitleWithoutRoot(sourcePage)),
        language: cleanText(languageCode) || null
      }

      const components = root ? collectSemanticComponents(root) : []
      const fields = root ? collectVisibleFields(root) : []
      const actions = root ? collectVisibleActions(root) : []
      const tables = root ? collectTables(root) : []
      const runtimeSignals = root
        ? collectRuntimeSignals(root)
        : {
            headings: [],
            visible_alerts: [],
            visible_dialogs: []
          }

      // Support both the legacy top-level contract and the nested data_context contract.
      // Prefer the explicit top-level value when it is present; otherwise use the nested value.
      const selectedRecordSource = source.selected_record != null
        ? source.selected_record
        : sourceDataContext.selected_record
      const selectedRecord = redactRecord(selectedRecordSource)
      const selectedRecordAvailable = Boolean(
        selectedRecord && Object.keys(selectedRecord).length > 0
      )
      const sourceRecordCount = Number.isFinite(sourceGrid.record_count)
        ? sourceGrid.record_count
        : Number.isFinite(sourceDataContext.record_count)
          ? sourceDataContext.record_count
          : null

      const result = {
        schema_version: 2,
        collected_at: new Date().toISOString(),
        page,
        components,
        fields,
        actions,
        tables,
        navigation: {
          ...sourceNavigation,
          parent_component: sourceNavigation.parent_component || null,
          parent_record_context: Array.isArray(sourceNavigation.parent_record_context)
            ? sourceNavigation.parent_record_context.map(parent => ({
                component_name: parent?.component_name || null,
                fields: Array.isArray(parent?.fields)
                  ? parent.fields.filter(
                      field => typeof field === 'string' &&
                        !SENSITIVE_KEY_PATTERN.test(field)
                    ).slice(0, MAX_ITEMS_PER_GROUP)
                  : [],
                field_labels: Object.fromEntries(
                  Object.entries(asObject(parent?.fieldLabels || parent?.field_labels))
                    .filter(([key, value]) =>
                      !SENSITIVE_KEY_PATTERN.test(key) &&
                      typeof value === 'string'
                    )
                    .slice(0, MAX_ITEMS_PER_GROUP)
                    .map(([key, value]) => [key, cleanText(value, 200)])
                )
              }))
            : []
        },
        runtime_state: {
          ...sourceUiState,
          page_loading: Boolean(sourceUiState.page_loading),
          page_error: Boolean(sourceUiState.page_error),
          grid_loading: Boolean(sourceUiState.grid_loading),
          grid_error: Boolean(sourceUiState.grid_error),
          form_visible: Boolean(sourceUiState.form_visible),
          form_mode: sourceUiState.form_mode || null,
          has_selection: Boolean(sourceUiState.has_selection || selectedRecordAvailable),
          ...runtimeSignals
        },
        grid: {
          ...sourceGrid,
          component: sourceGrid.component || sourcePage.grid_component || null,
          field_mode: sourceGrid.field_mode || null,
          configuration_available: Boolean(sourceGrid.configuration_available),
          record_count: sourceRecordCount
        },
        data_context: {
          ...sourceDataContext,
          selected_record_available: selectedRecordAvailable,
          selected_record_fields: selectedRecord ? Object.keys(selectedRecord) : [],
          selected_record: selectedRecord,
          record_count: sourceRecordCount
        },
        // Legacy keys are retained for the existing Avatar context contract.
        selected_record: selectedRecord
      }

      context.value = result
      lastCollectedAt.value = result.collected_at
      error.value = null

      return result
    } catch (err) {
      error.value = err
      throw err
    }
  }

  function findPageTitleWithoutRoot(sourcePage) {
    if (typeof document !== 'undefined' && cleanText(document.title)) {
      return cleanText(document.title)
    }

    return cleanText(
      sourcePage.visible_title ||
      sourcePage.title ||
      sourcePage.page_title
    ) || null
  }

  function serializePageContext(value = context.value) {
    if (!value) return null

    try {
      return JSON.stringify(value)
    } catch (err) {
      error.value = err
      throw err
    }
  }

  function clearPageContext() {
    context.value = null
    lastCollectedAt.value = null
    error.value = null
  }

  return {
    context,
    lastCollectedAt,
    error,
    collectPageContext,
    serializePageContext,
    clearPageContext
  }
}