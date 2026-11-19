// ===============================================
// File:
// frontend/src/stores/uiStore.js
//
// Description:
// UI state for language, direction, calendar, theme,
// dark mode, and canonical user identity
//
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// ===============================================
import {
  ref,
  computed,
  watchEffect
} from 'vue'

// --------------------------------------------------
// Initial State
// --------------------------------------------------
function getInitialDarkMode() {
  const stored =
    localStorage.getItem(
      'darkMode'
    )

  if (stored !== null) {
    return stored === 'true'
  }

  return (
    window.matchMedia &&
    window.matchMedia(
      '(prefers-color-scheme: dark)'
    ).matches
  )
}

function getInitialLanguage() {
  return (
    localStorage.getItem(
      'language'
    ) || 'en'
  )
}

function getInitialThemeLevel() {
  const stored =
    localStorage.getItem(
      'themeLevel'
    )

  const level =
    stored
      ? parseInt(
          stored,
          10
        )
      : 3

  return (
    Number.isFinite(level) &&
    level >= 1 &&
    level <= 10
  )
    ? level
    : 3
}

// --------------------------------------------------
// Reactive State
// --------------------------------------------------
export const darkMode =
  ref(
    getInitialDarkMode()
  )

export const language =
  ref(
    getInitialLanguage()
  )

export const themeLevel =
  ref(
    getInitialThemeLevel()
  )

export const languages =
  ref([])

export const userIdentity =
  ref({
    id: '',
    email: '',
    profile_id: ''
  })

// --------------------------------------------------
// Language Metadata
// --------------------------------------------------
export const languageMeta =
  computed(() => {
    return (
      languages.value.find(
        item =>
          item.language_code ===
          language.value &&
          item.is_active === true
      ) || null
    )
  })

export function setLanguages(items) {
  languages.value =
    Array.isArray(items)
      ? items
      : []
}

export function setLanguage(code) {
  const selected =
    languages.value.find(
      item =>
        item.language_code === code &&
        item.is_active === true
    )

  if (!selected) {
    return
  }

  language.value =
    selected.language_code
}

export function setLanguageMeta(code) {
  setLanguage(code)
}

// --------------------------------------------------
// Persist State
// --------------------------------------------------
watchEffect(() => {
  localStorage.setItem(
    'darkMode',
    darkMode.value
      ? 'true'
      : 'false'
  )

  localStorage.setItem(
    'language',
    language.value
  )

  localStorage.setItem(
    'themeLevel',
    String(
      themeLevel.value
    )
  )
})

// --------------------------------------------------
// State Modification
// --------------------------------------------------
export function toggleDarkMode() {
  darkMode.value =
    !darkMode.value
}

export function toggleLanguage() {
  const activeLanguages =
    languages.value.filter(
      item =>
        item.is_active === true
    )

  if (
    activeLanguages.length === 0
  ) {
    return
  }

  const currentIndex =
    activeLanguages.findIndex(
      item =>
        item.language_code ===
        language.value
    )

  const nextIndex =
    currentIndex >= 0
      ? (
          currentIndex + 1
        ) %
        activeLanguages.length
      : 0

  setLanguage(
    activeLanguages[
      nextIndex
    ].language_code
  )
}

export function setThemeLevel(level) {
  const numericLevel =
    Number(level)

  if (
    Number.isFinite(
      numericLevel
    ) &&
    numericLevel >= 1 &&
    numericLevel <= 10
  ) {
    themeLevel.value =
      numericLevel
  }
}

// --------------------------------------------------
// User Identity
// --------------------------------------------------
//
// profile_id is the canonical runtime identity field.
// Physical database names such as c_profile_id
// must not enter the general runtime contract.
//
export function setUserIdentity(
  identity
) {
  const source =
    identity &&
    typeof identity === 'object'
      ? identity
      : {}

  userIdentity.value = {
    id:
      source.id || '',
    email:
      source.email || '',
    profile_id:
      source.profile_id || ''
  }
}

// --------------------------------------------------
// Important Learning Points
// --------------------------------------------------
// 1. userIdentity is the authenticated runtime identity context.
// 2. profile_id is the canonical profile identity field.
// 3. Physical names such as c_profile_id are not stored here.
// 4. profile_id is independent from parm[n].
// 5. parm[n] belongs to where_clause resolution.
// 6. Language metadata remains the source of direction/calendar data.
// 7. No component-specific metadata is stored in uiStore.