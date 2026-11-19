// ===============================================
// File:
// frontend/src/composables/useTranslation.js
//
// Description:
// Composable for dynamic text translations via backend API.
//
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// Modified: 2026-10-09 01:00 (Asia/Baku)
// ===============================================
import axios from '@/utils/axiosInstance'
import { language } from '@/stores/uiStore.js'

export function useTranslation() {
  const currentLanguage = language

  async function translate(itemCode, lang = currentLanguage.value) {
    if (!itemCode) {
      return ''
    }

    try {
      const response = await axios.get('/utils/translate', {
        params: {
          item_code: itemCode,
          language_code: lang
        }
      })

      return response.data?.translated_text || itemCode
    } catch (err) {
      console.warn(
        `Translation fetch failed for "${itemCode}":`,
        err
      )

      return itemCode
    }
  }

  return {
    translate,
    currentLanguage
  }
}

// Important Learning Points:
// 1. Translation requests are transported through the shared API client.
// 2. The active language comes from uiStore.
// 3. Translation failures safely fall back to itemCode.
// 4. This composable does not contain language-specific translations.
// 5. This composable does not interpret primary_key.
// 6. This composable does not interpret where_clause.
// 7. This composable does not create or resolve parm[n].