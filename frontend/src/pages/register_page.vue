<!--
====================================================================
File: frontend/src/pages/register_page.vue
Description:
User registration page using new translation model (item_code + language_code)
Dynamic i18n, light/dark mode, and metadata-driven RTL support.
====================================================================
-->

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  language,
  languageMeta,
  darkMode
} from "@/stores/uiStore.js";
import TopControls from "@/components/top_controls.vue";
import { useTranslation } from "@/composables/useTranslation.js";
import axios from "@/utils/axiosInstance";

// Route & State
const route = useRoute();
const router = useRouter();

const profileId = ref("");
const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const message = ref("");
const success = ref(false);
const loading = ref(false);

// RTL
const isRtl = computed(() => {
  return languageMeta.value?.is_rtl === true;
});

// Translations
const { translate } = useTranslation();

const itemKeys = [
  "register.title",
  "register.email.label",
  "register.password.label",
  "register.confirm_password.label",
  "register.button.submit",
  "register.button.loading",
  "register.error.incomplete",
  "register.error.generic",
  "register.success.message"
];

const translations = ref({});

// Load translations
async function loadTranslations() {
  const lang = language.value;

  for (const key of itemKeys) {
    translations.value[key] = await translate(key, lang);
  }
}

// Validation
const isFormValid = computed(() =>
  email.value.trim() !== "" &&
  password.value.length >= 6 &&
  password.value === confirmPassword.value
);

// Init
onMounted(() => {
  profileId.value = route.query.profile_id || "";
  loadTranslations();
});

watch(language, loadTranslations);

// Submit Registration
async function submitUser() {
  message.value = "";
  success.value = false;

  if (!isFormValid.value) {
    message.value =
      translations.value["register.error.incomplete"];
    return;
  }

  try {
    loading.value = true;

    const res = await axios.post(
      "/auth/register",
      {
        email: email.value,
        password: password.value,
        profile_id: profileId.value
      }
    );

    message.value =
      translations.value["register.success.message"];

    success.value = true;

    email.value = "";
    password.value = "";
    confirmPassword.value = "";

    setTimeout(() => {
      router.push("/login");
    }, 2000);

  } catch (err) {
    const detail =
      err.response?.data?.detail ||
      err.message ||
      translations.value["register.error.generic"];

    message.value =
      `${translations.value["register.error.generic"]} ${detail}`;

  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div
    :class="{ dark: darkMode }"
    class="pulsar-shell flex min-h-screen items-center justify-center px-4 py-20"
  >
    <TopControls
      pageTitleKey="register_page"
      userEmail="auth.user?.email"
    />

<div
  :dir="isRtl ? 'rtl' : 'ltr'"
  class="w-full max-w-[420px]"
>
  <div class="pulsar-surface overflow-hidden">
    <div
      class="border-b border-border bg-panel-alt px-6 py-6 text-center"
    >
      <h1 class="text-2xl font-bold text-label">
        {{ translations["register.title"] }}
      </h1>
    </div>

    <form
      @submit.prevent="submitUser"
      class="space-y-4 p-6"
    >
      <div>
        <label
          class="mb-1.5 block text-xs font-semibold text-label"
        >
          {{ translations["register.email.label"] }}
        </label>

        <input
          v-model="email"
          type="email"
          class="pulsar-field"
          autocomplete="on"
          required
        />
      </div>

      <div>
        <label
          class="mb-1.5 block text-xs font-semibold text-label"
        >
          {{ translations["register.password.label"] }}
        </label>

        <input
          v-model="password"
          type="password"
          class="pulsar-field"
          autocomplete="new-password"
          required
        />
      </div>

      <div>
        <label
          class="mb-1.5 block text-xs font-semibold text-label"
        >
          {{ translations["register.confirm_password.label"] }}
        </label>

        <input
          v-model="confirmPassword"
          type="password"
          class="pulsar-field"
          required
        />
      </div>

      <button
        type="submit"
        class="w-full rounded-xl bg-button py-2.5 text-sm font-semibold text-button shadow-sm transition hover:brightness-105 disabled:opacity-50"
        :disabled="loading"
      >
        {{
          loading
            ? translations["register.button.loading"]
            : translations["register.button.submit"]
        }}
      </button>

      <p
        v-if="message"
        class="rounded-lg px-3 py-2 text-center text-xs font-medium"
        :class="
          success
            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
            : 'bg-red-500/10 text-red-600 dark:text-red-400'
        "
      >
        {{ message }}
      </p>
    </form>
  </div>
</div>


  </div>
</template>
