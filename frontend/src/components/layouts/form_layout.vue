<!-- ================================================
File: frontend/src/components/layouts/form_layout.vue
Description: Reusable layout for centered forms with TopControls
================================================ -->

<template>
  <div
    :class="{ dark: darkMode }"
    class="pulsar-shell flex min-h-screen flex-col items-center justify-center px-4 py-20"
  >
    <TopControls
      pageTitleKey="form_layout"
      userEmail="auth.user?.email"
    />

<div
  :dir="isRtl ? 'rtl' : 'ltr'"
  class="w-full max-w-md pulsar-surface p-5 sm:p-6"
>
  <slot />
</div>

  </div>
</template>

<script setup>
import { computed } from "vue";
import {
  languageMeta,
  darkMode
} from "@/stores/uiStore.js";
import TopControls from "@/components/top_controls.vue";

const isRtl = computed(() => {
  return languageMeta.value?.is_rtl === true;
});
</script>

<!--
Important Learning Points:
- This layout centralizes common UI patterns like TopControls and dark/light mode.
- Allows any page to inject form content via <slot>, promoting reuse and clean code.
- Text direction is driven by language metadata instead of hard-coded language codes.
-->
