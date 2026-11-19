// ===============================================
// File: frontend/src/composables/useDateFormat.js
// Description: Composable for metadata-driven date and datetime formatting
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// ===============================================
 
import {
  computed
} from 'vue'

import {
  languageMeta
} from '@/stores/uiStore'

// --------------------------------------------------
// Language Metadata
// --------------------------------------------------

const dateFormat = computed(
  () =>
    languageMeta.value?.date_format ||
    'YYYY-MM-DD'
)

const datetimeFormat = computed(
  () =>
    languageMeta.value?.datetime_format ||
    'YYYY-MM-DD HH24:MI:SS'
)

const calendarCode = computed(
  () =>
    languageMeta.value?.calendar_code ||
    'gregorian'
)

// --------------------------------------------------
// Date Parsing
// --------------------------------------------------

function parseDate(value) {
  if (!value) return null

  if (value instanceof Date) {
    return Number.isNaN(value.getTime())
      ? null
      : value
  }

  if (
    typeof value === 'string' &&
    /^\d{4}-\d{2}-\d{2}$/.test(value)
  ) {
    const [
      year,
      month,
      day
    ] = value
      .split('-')
      .map(Number)

    const date = new Date(
      year,
      month - 1,
      day
    )

    return Number.isNaN(date.getTime())
      ? null
      : date
  }

  const date = new Date(value)

  return Number.isNaN(date.getTime())
    ? null
    : date
}

// --------------------------------------------------
// Calendar Components
// --------------------------------------------------

function getGregorianComponents(date) {
  return {
    year: date.getFullYear(),
    month: date.getMonth() + 1,
    day: date.getDate()
  }
}

function getJalaliComponents(date) {
  const formatter =
    new Intl.DateTimeFormat(
      'en-US-u-ca-persian-nu-latn',
      {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      }
    )

  const parts =
    formatter.formatToParts(date)

  const result = {}

  parts.forEach(part => {
    if (
      part.type === 'year' ||
      part.type === 'month' ||
      part.type === 'day'
    ) {
      result[part.type] =
        Number(part.value)
    }
  })

  return result
}

function getCalendarComponents(date) {
  if (
    calendarCode.value ===
    'jalali'
  ) {
    return getJalaliComponents(date)
  }

  return getGregorianComponents(date)
}

// --------------------------------------------------
// Format Tokens
// --------------------------------------------------

function pad(value) {
  return String(value).padStart(2, '0')
}

function formatDateTokens(
  format,
  components
) {
  return format
    .replace(
      'YYYY',
      String(components.year)
    )
    .replace(
      'MM',
      pad(components.month)
    )
    .replace(
      'DD',
      pad(components.day)
    )
}

function formatDateTimeTokens(
  format,
  components,
  date
) {
  return format
    .replace(
      'YYYY',
      String(components.year)
    )
    .replace(
      'MM',
      pad(components.month)
    )
    .replace(
      'DD',
      pad(components.day)
    )
    .replace(
      'HH24',
      pad(date.getHours())
    )
    .replace(
      'MI',
      pad(date.getMinutes())
    )
    .replace(
      'SS',
      pad(date.getSeconds())
    )
}

// --------------------------------------------------
// Digit System
// --------------------------------------------------

function applyDigitSystem(value) {
  const system =
    languageMeta.value?.digit_system ||
    'western'

  if (system === 'western') {
    return value
  }

  if (system === 'persian') {
    return String(value).replace(
      /\d/g,
      digit =>
        '۰۱۲۳۴۵۶۷۸۹'[digit]
    )
  }

  if (system === 'arabic') {
    return String(value).replace(
      /\d/g,
      digit =>
        '٠١٢٣٤٥٦٧٨٩'[digit]
    )
  }

  return value
}

// --------------------------------------------------
// Public API
// --------------------------------------------------

export function useDateFormat() {
  function formatDate(value) {
    const date =
      parseDate(value)

    if (!date) return ''

    const components =
      getCalendarComponents(date)

    return applyDigitSystem(
      formatDateTokens(
        dateFormat.value,
        components
      )
    )
  }

  function formatDateTime(value) {
    const date =
      parseDate(value)

    if (!date) return ''

    const components =
      getCalendarComponents(date)

    return applyDigitSystem(
      formatDateTimeTokens(
        datetimeFormat.value,
        components,
        date
      )
    )
  }

  return {
    dateFormat,
    datetimeFormat,
    calendarCode,
    formatDate,
    formatDateTime
  }
}
