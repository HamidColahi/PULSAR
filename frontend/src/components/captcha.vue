<!-- Pulsar/frontend/src/components/captcha.vue -->

<template>
  <div class="flex items-center gap-3">
    <!-- Display question in Latin digits with proper font -->
    <span dir="ltr" class="captcha-font">
      {{ latinQuestion }}
    </span>


<!-- Answer input -->
<input
  v-model="userInput"
  type="text"
  inputmode="numeric"
  placeholder="?"
  class="bg-input w-16 text-center border rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
/>

<!-- Refresh button -->
<button
  @click="generatecaptcha"
  :title="refreshTitle"
  type="button"
>
  🔄
</button>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { language } from '@/stores/uiStore'
import { useTranslation } from '@/composables/useTranslation'

const question = ref('')
const answer = ref(null)
const userInput = ref('')
const refreshTitle = ref('')

const { translate } = useTranslation()

// Load the CAPTCHA refresh title from the translation dictionary.
async function loadTranslations() {
  refreshTitle.value = await translate(
    'captcha.refresh',
    language.value,
    'captcha'
  )
}

// Generate captcha with Latin digits.
function generatecaptcha() {
  const num1 = Math.floor(Math.random() * 10)
  const num2 = Math.floor(Math.random() * 10)
  const result = num1 + num2

  question.value = `${num1} + ${num2} = ?`
  answer.value = result
  userInput.value = ''
}

// Always return the question with Latin digits.
const latinQuestion = computed(() =>
  question.value.replace(/\d/g, d => d.toLocaleString('en-US'))
)

// Check captcha correctness.
function isCorrect() {
  return parseInt(userInput.value) === answer.value
}

// Reset captcha.
function reset() {
  generatecaptcha()
  userInput.value = ''
}

// Expose methods to parent.
defineExpose({
  userInput,
  answer,
  generatecaptcha,
  isCorrect,
  reset
})

onMounted(async () => {
  await loadTranslations()
  generatecaptcha()
})

watch(language, async () => {
  await loadTranslations()
})
</script>

<style scoped>
.captcha-font {
  font-family: "Fira Code" !important;
  font-size: 3cap;
  font-weight: 800;
  font-style: italic;
  color: #2563eb;
  user-select: none;
  font-variant-numeric: tabular-nums;
  direction: ltr;
  unicode-bidi: plaintext;
}
</style>
