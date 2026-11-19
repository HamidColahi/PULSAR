// ===============================================
// File: frontend/src/composables/useLanguages.js
// Description: Load active language metadata for the application runtime
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// ===============================================

import {
  ref,
  computed
} from 'vue'

import axios from '@/utils/axiosInstance'

import {
  languages,
  language,
  languageMeta,
  setLanguages,
  setLanguage
} from '@/stores/uiStore'

// --------------------------------------------------
// State
// --------------------------------------------------

const loading = ref(false)
const error = ref(null)

// --------------------------------------------------
// Active Languages
// --------------------------------------------------

const activeLanguages = computed(() => {
  return languages.value.filter(
    item =>
      item.is_active === true
  )
})

// --------------------------------------------------
// Load Languages
// --------------------------------------------------

async function fetchLanguages() {
  loading.value = true
  error.value = null

  try {
    const { data } =
      await axios.get('/languages')

    setLanguages(data || [])

    const current =
      activeLanguages.value.find(
        item =>
          item.language_code ===
          language.value
      )

    if (current) {
      setLanguage(
        current.language_code
      )
    } else if (
      activeLanguages.value.length
    ) {
      setLanguage(
        activeLanguages.value[0]
          .language_code
      )
    }

  } catch (err) {
    error.value = err

    console.warn(
      'useLanguages - Failed to load languages:',
      err
    )

  } finally {
    loading.value = false
  }
}

// --------------------------------------------------
// Language Selection
// --------------------------------------------------

function changeLanguage(code) {
  setLanguage(code)
}

// --------------------------------------------------
// Composable
// --------------------------------------------------

export function useLanguages() {
  return {
    languages,
    activeLanguages,
    language,
    languageMeta,
    loading,
    error,
    fetchLanguages,
    changeLanguage
  }
}
