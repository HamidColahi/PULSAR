<!--
 File: frontend/src/pages/login_page.vue
 Description: Localized login page with metadata-driven language direction
 Author: MHKolahi@gmail.com
 In collaboration with GPT4 Chat Assistant: Bahram
-->

<script setup>
// -------------------------------------------------------------
// Imports
// -------------------------------------------------------------
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore.js'
import {
  language,
  languageMeta,
  darkMode
} from '@/stores/uiStore.js'
import captcha from '@/components/captcha.vue'
import TopControls from '@/components/top_controls.vue'
import { useTranslation } from '@/composables/useTranslation.js'
import axios from '@/utils/axiosInstance'

// -------------------------------------------------------------
// State and store bindings
// -------------------------------------------------------------
const pageTitleKey = ref('login_page')
const router = useRouter()
const auth = useAuthStore()
const email = ref('')
const password = ref('')
const errorMessage = ref('')
const captchaRef = ref(null)

// -------------------------------------------------------------
// Language Direction
// -------------------------------------------------------------
const isRtl = computed(() => {
  return languageMeta.value?.is_rtl === true
})

// -------------------------------------------------------------
// Translation composable setup
// -------------------------------------------------------------
const { translate } = useTranslation()

// List of translation item_codes used in this page
const itemKeys = [
  'login.title',
  'login.email.label',
  'login.password.label',
  'login.button.submit',
  'login.error.invalid_credentials',
  'login.error.missing_fields',
  'login.error.captcha',
  'login.register.prompt'
]

// Reactive translations object to store fetched translated strings
const translations = ref({})

// -------------------------------------------------------------
// Load translations for current language and form context
// Uses fallback: if translation missing, show the item_code itself.
// -------------------------------------------------------------
async function loadTranslations() {
  const lang = language.value
  const result = {}

  for (const key of itemKeys) {
    try {
      result[key] =
        await translate(
          key,
          lang,
          'login_page'
        )
    } catch {
      result[key] = key
    }
  }

  translations.value = result
}

// -------------------------------------------------------------
// Reset form inputs and captcha widget
// -------------------------------------------------------------
function resetForm() {
  email.value = ''
  password.value = ''
  errorMessage.value = ''

  if (captchaRef.value?.reset) {
    captchaRef.value.reset()
  }
}

// -------------------------------------------------------------
// Handle login form submission with validation & error handling
// -------------------------------------------------------------
async function submitLogin() {
  errorMessage.value = ''

  // Validate captcha correctness before proceeding
  if (!captchaRef.value?.isCorrect()) {
    errorMessage.value =
      translations.value[
        'login.error.captcha'
      ] || 'Invalid captcha'

    return
  }

  // Validate required fields
  if (
    !email.value.trim() ||
    !password.value.trim()
  ) {
    errorMessage.value =
      translations.value[
        'login.error.missing_fields'
      ] ||
      'Please enter email and password.'

    return
  }

  try {
    // Call backend login API
    const res = await fetch(
      axios.defaults.baseURL +
        'auth/login',
      {
        method: 'POST',
        headers: {
          'Content-Type':
            'application/json'
        },
        body: JSON.stringify({
          email: email.value,
          password: password.value
        })
      }
    )

    // Handle failed login attempt
    if (!res.ok) {
      throw new Error(
        translations.value[
          'login.error.invalid_credentials'
        ] ||
        'Invalid credentials'
      )
    }

    // Success: store token, fetch user profile, and redirect to dashboard
    const data = await res.json()

    auth.login(data.access_token)

    await auth.fetchUser()

    router.push('/dashboard')

  } catch (error) {
    errorMessage.value =
      error.message
  }
}

// -------------------------------------------------------------
// Navigate to registration page with captcha check
// -------------------------------------------------------------
function goToRegister() {
  errorMessage.value = ''

  if (!captchaRef.value?.isCorrect()) {
    errorMessage.value =
      translations.value[
        'login.error.captcha'
      ] || 'Invalid captcha'

    return
  }

  router.push('/profile/create')
}

// -------------------------------------------------------------
// Initialize translation loading & reset form on mount
// Also reload translations when global language changes.
// -------------------------------------------------------------
onMounted(() => {
  loadTranslations()
  resetForm()
})

watch(language, () => {
  loadTranslations()
})
</script>

<template>
  <div
    :class="{ dark: darkMode }"
    class="pulsar-shell flex min-h-screen items-center justify-center px-4 py-20"
  >
    <TopControls
      :pageTitleKey="pageTitleKey"
    />

<div
  v-if="Object.keys(translations).length > 0"
  :dir="isRtl ? 'rtl' : 'ltr'"
  class="w-full max-w-[420px]"
>
  <div class="pulsar-surface overflow-hidden">

    <div
      class="border-b border-border bg-panel-alt px-6 py-7 text-center"
    >
      <img
        src="@/assets/logo/Pulsar.png"
        alt="Pulsar"
        class="mx-auto mb-4 h-10 w-auto object-contain"
      />

      <h1
        class="text-2xl font-bold tracking-tight text-label"
      >
        {{ translations['login.title'] }}
      </h1>

      <p class="mt-1 text-xs text-muted">
        PULSAR Enterprise Platform
      </p>
    </div>

    <form
      @submit.prevent="submitLogin"
      class="space-y-4 p-6"
    >
      <div>
        <label
          for="email"
          class="mb-1.5 block text-xs font-semibold text-label"
        >
          {{ translations['login.email.label'] }}
        </label>

        <input
          id="email"
          v-model="email"
          type="email"
          :placeholder="
            translations['login.email.label']
          "
          class="pulsar-field"
          autocomplete="on"
          required
        />
      </div>

      <div>
        <label
          for="password"
          class="mb-1.5 block text-xs font-semibold text-label"
        >
          {{ translations['login.password.label'] }}
        </label>

        <input
          id="password"
          v-model="password"
          type="password"
          placeholder="••••••••"
          class="pulsar-field"
          autocomplete="new-password"
          required
        />
      </div>

      <captcha ref="captchaRef" />

      <button
        type="submit"
        class="w-full rounded-xl bg-button py-2.5 text-sm font-semibold text-button shadow-sm transition hover:brightness-105"
      >
        {{ translations['login.button.submit'] }}
      </button>

      <p
        v-if="errorMessage"
        class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-center text-xs font-medium text-red-600 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-400"
      >
        {{ errorMessage }}
      </p>

      <div
        class="border-t border-border pt-4 text-center"
      >
        <button
          @click="goToRegister"
          type="button"
          class="text-xs font-semibold text-link hover:text-link-hover"
        >
          {{ translations['login.register.prompt'] }}
        </button>
      </div>

    </form>
  </div>
</div>

<div
  v-else
  class="text-sm text-muted"
>
  Loading translations...
</div>

  </div>
</template>
