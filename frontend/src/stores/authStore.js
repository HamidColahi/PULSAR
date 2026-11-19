// ================================================
// File: frontend/src/stores/authStore.js
// Description: Global store to manage authentication state
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// ================================================

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { setUserIdentity } from '@/stores/uiStore'
import axios from '@/utils/axiosInstance'

import {
  setAuthToken,
  clearAuthToken
} from '@/utils/authToken'


export const useAuthStore = defineStore(
  'auth',
  () => {

    const token = ref(null)

    const user = ref(null)

    const isAuthenticated =
      ref(!!token.value)


    // =================================================
    // Login
    // =================================================

    function login(newToken) {

      token.value =
        newToken || null

      setAuthToken(
        token.value
      )

      isAuthenticated.value =
        !!token.value
    }


    // =================================================
    // Fetch Current User
    // =================================================

    async function fetchUser() {

      if (!token.value) {
        return
      }

      try {

        const { data } =
          await axios.get(
            '/auth/me'
          )

        user.value =
          data

        setUserIdentity({
          id: user.value.id,
          email: user.value.email,
          profile_id:
            user.value.profile_id
        })

        isAuthenticated.value =
          true

      } catch (err) {

        logout()

      }
    }


    // =================================================
    // Logout
    // =================================================

    function logout() {

      token.value =
        null

      user.value =
        null

      isAuthenticated.value =
        false

      clearAuthToken()

      localStorage.removeItem(
        'access_token'
      )
    }


    return {
      token,
      user,
      isAuthenticated,
      login,
      fetchUser,
      logout
    }
  }
)


// Important Learning Points:
// 1. JWT authentication is centralized through authToken.js.
// 2. login() registers the JWT for the application HTTP layer.
// 3. fetchUser() uses axiosInstance so Authorization is added centrally.
// 4. logout() clears both the Pinia token and the shared authentication token.
// 5. No API component needs to manually construct an Authorization header.