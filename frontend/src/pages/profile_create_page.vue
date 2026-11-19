<!--
====================================================================
File: frontend/src/pages/profile_create_page.vue
Description:
Profile creation page with metadata-driven translation and RTL support.
====================================================================
-->

<script setup>
// Imports
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import {
  language,
  languageMeta,
  darkMode
} from "@/stores/uiStore.js";
import TopControls from "@/components/top_controls.vue";
import { useTranslation } from "@/composables/useTranslation.js";
import axios from "@/utils/axiosInstance";

// Translation setup
const { translate } = useTranslation();
const translations = ref({});

const itemKeys = [
  "profile.title",
  "profile.title.label",
  "profile.title.placeholder",
  "profile.person_type.label",
  "profile.person_type.natural",
  "profile.person_type.legal",
  "profile.sector.label",
  "profile.sector.private",
  "profile.sector.government",
  "profile.button.submit",
  "profile.button.loading",
  "profile.success.message",
  "profile.error.incomplete",
  "profile.error.generic"
];

async function loadTranslations() {
  const lang = language.value;

  for (const key of itemKeys) {
    translations.value[key] = await translate(key, lang);
  }
}

// RTL
const isRtl = computed(() => {
  return languageMeta.value?.is_rtl === true;
});

// Form state
const type = ref("");
const sector = ref("");
const title = ref("");

const loading = ref(false);
const message = ref("");
const success = ref(false);

const router = useRouter();

const isFormValid = computed(() =>
  type.value && sector.value && title.value.trim()
);

// Submit profile form
async function submitProfile() {
  message.value = "";
  success.value = false;

  if (!isFormValid.value) {
    message.value = translations.value["profile.error.incomplete"];
    return;
  }

  try {
    loading.value = true;

    const { data } = await axios.post(
      "/profile/create",
      {
        c_profile_type: type.value,
        c_profile_sector: sector.value,
        c_profile_title: title.value.trim()
      }
    );

    message.value = translations.value["profile.success.message"];
    success.value = true;

    // Clear form
    type.value = "";
    sector.value = "";
    title.value = "";

    setTimeout(() => {
      router.push({
        path: "/register",
        query: { profile_id: data.profile_id }
      });
    }, 1500);

  } catch (err) {
    const detail =
      err.response?.data?.detail ||
      err.message ||
      "";

    message.value =
      `${translations.value["profile.error.generic"]} ${detail}`;
  } finally {
    loading.value = false;
  }
}

// On mount and language change
onMounted(() => loadTranslations());
watch(language, loadTranslations);
</script>

<template>
  <div
    :class="{ dark: darkMode }"
    class="pulsar-shell flex min-h-screen items-center justify-center px-4 py-20"
  >
    <TopControls
      pageTitleKey="profile_create_page"
      userEmail="auth.user?.email"
    />

<div
  :dir="isRtl ? 'rtl' : 'ltr'"
  class="w-full max-w-[460px]"
>
  <div class="pulsar-surface overflow-hidden">
    <div
      class="border-b border-border bg-panel-alt px-6 py-6 text-center"
    >
      <h1 class="text-2xl font-bold text-label">
        {{ translations["profile.title"] }}
      </h1>
    </div>

    <form
      @submit.prevent="submitProfile"
      class="space-y-4 p-6"
    >
      <div>
        <label
          class="mb-1.5 block text-xs font-semibold text-label"
        >
          {{ translations["profile.person_type.label"] }}
        </label>

        <select
          v-model="type"
          class="pulsar-field"
        >
          <option disabled value="">
            {{ translations["profile.person_type.label"] }}
          </option>

          <option value="N">
            {{ translations["profile.person_type.natural"] }}
          </option>

          <option value="L">
            {{ translations["profile.person_type.legal"] }}
          </option>
        </select>
      </div>

      <div>
        <label
          class="mb-1.5 block text-xs font-semibold text-label"
        >
          {{ translations["profile.sector.label"] }}
        </label>

        <select
          v-model="sector"
          class="pulsar-field"
        >
          <option disabled value="">
            {{ translations["profile.sector.label"] }}
          </option>

          <option value="P">
            {{ translations["profile.sector.private"] }}
          </option>

          <option value="G">
            {{ translations["profile.sector.government"] }}
          </option>
        </select>
      </div>

      <div>
        <label
          class="mb-1.5 block text-xs font-semibold text-label"
        >
          {{ translations["profile.title.label"] }}
        </label>

        <input
          v-model="title"
          type="text"
          class="pulsar-field"
          :placeholder="translations['profile.title.placeholder']"
        />
      </div>

      <button
        type="submit"
        class="w-full rounded-xl bg-button py-2.5 text-sm font-semibold text-button shadow-sm transition hover:brightness-105 disabled:opacity-50"
        :disabled="loading"
      >
        {{
          loading
            ? translations["profile.button.loading"]
            : translations["profile.button.submit"]
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
