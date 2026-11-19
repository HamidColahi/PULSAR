// ===============================================
// File:
// frontend/src/composables/useUserAccess.js
//
// Description:
// Load user access through the generic context-based access API
//
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// ===============================================
import {
  ref,
  watch,
  computed
} from 'vue'
import axios from '@/utils/axiosInstance'
import {
  userIdentity
} from '@/stores/uiStore'

const STORAGE_KEY =
  'pulsar_user_access_map'

const userAccessMap =
  ref(loadAccessFromStorage())

const userId = computed(() => {
  return userIdentity.value?.id || null
})

function loadAccessFromStorage() {
  try {
    const stored =
      localStorage.getItem(
        STORAGE_KEY
      )

    if (!stored) {
      return {}
    }

    const parsed =
      JSON.parse(stored)

    return (
      parsed &&
      typeof parsed === 'object' &&
      !Array.isArray(parsed)
    )
      ? parsed
      : {}
  } catch (err) {
    console.warn(
      'useUserAccess: failed to load access map from localStorage',
      err
    )

    return {}
  }
}

function saveAccessToStorage(
  accessMap
) {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(accessMap)
    )
  } catch (err) {
    console.warn(
      'useUserAccess: failed to save access map to localStorage',
      err
    )
  }
}

function clearAccessStorage() {
  try {
    localStorage.removeItem(
      STORAGE_KEY
    )
  } catch (err) {
    console.warn(
      'useUserAccess: failed to clear access map from localStorage',
      err
    )
  }
}

async function fetchUserAccess() {
  if (!userId.value) {
    userAccessMap.value = {}
    clearAccessStorage()
    return {}
  }

  try {
    const response =
      await axios.get(
        '/access/user_access',
        {
          params: {
            context_id:
              userId.value
          }
        }
      )

    const rows =
      Array.isArray(
        response.data
      )
        ? response.data
        : []

    const accessMap =
      Object.fromEntries(
        rows
          .filter(
            entry =>
              entry?.page_key &&
              entry?.page_level
          )
          .map(
            entry => [
              entry.page_key,
              {
                page_level:
                  entry.page_level,
                c_page_view:
                  entry.c_page_view === true,
                c_page_insert:
                  entry.c_page_insert === true,
                c_page_update:
                  entry.c_page_update === true,
                c_page_delete:
                  entry.c_page_delete === true,
                c_page_renderer:
                  entry.c_page_renderer === true
              }
            ]
          )
      )

    userAccessMap.value =
      accessMap

    saveAccessToStorage(
      accessMap
    )

    return accessMap
  } catch (err) {
    console.warn(
      'useUserAccess: failed to load access map',
      err
    )

    userAccessMap.value = {}

    return {}
  }
}

watch(
  userId,
  fetchUserAccess,
  {
    immediate: true
  }
)

export function useUserAccess() {
  return {
    userAccessMap,
    userId,
    fetchUserAccess
  }
}

// Important Learning Points:
// 1. User access is loaded through the generic backend access API.
// 2. context_id is the authenticated user identity id.
// 3. Access data is keyed by metadata page key.
// 4. CRUD permissions remain explicit runtime properties.
// 5. Local storage is only a client-side cache.
// 6. Backend access control remains authoritative.
// 7. This composable does not interpret primary_key.
// 8. This composable does not interpret where_clause.
// 9. This composable does not create parm[n].
// 10. No physical database field alias is introduced here.