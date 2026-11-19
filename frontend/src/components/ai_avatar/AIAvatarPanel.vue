
<!-- ===============================================
File: frontend/src/components/ai_avatar/AIAvatarPanel.vue
Description: Persistent AI Avatar chat panel with metadata-driven digital human presentation
Change Date: 2026-10-23 15:10; Timezone: Asia/Baku
Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
=============================================== -->
<template>
  <Teleport to="body">
    <section
      ref="panelElement"
      v-show="open"
      class="ai-avatar-window fixed z-[100] flex flex-col overflow-hidden rounded-2xl border border-border shadow-2xl"
      :class="{ 'ai-avatar-dragging': isDragging }"
      :style="windowStyle"
      :dir="isRtl ? 'rtl' : 'ltr'"
      role="dialog"
      aria-modal="false"
      :aria-label="text.title"
      :aria-hidden="!open"
      :inert="!open"
    >
      <header
        class="ai-avatar-window-header flex shrink-0 cursor-move items-center justify-between border-b border-border px-4 py-3 select-none"
        @pointerdown="startDragging"
      >
        <div class="flex min-w-0 items-center gap-3">
          <div
            v-if="showDigitalAvatar"
            class="ai-avatar-header-face shrink-0"
            :class="faceStateClass"
            :style="faceStyle"
            aria-hidden="true"
          >
            <svg viewBox="0 0 64 64" class="ai-avatar-face-svg">
              <defs>
                <linearGradient id="ai-avatar-header-skin" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stop-color="var(--avatar-skin, #f8d8c4)" />
                  <stop offset="100%" stop-color="var(--avatar-skin-shadow, #c98e79)" />
                </linearGradient>
                <linearGradient id="ai-avatar-header-hair" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stop-color="var(--avatar-hair-highlight, #53617a)" />
                  <stop offset="100%" stop-color="var(--avatar-hair, #172033)" />
                </linearGradient>
              </defs>

              <path
                d="M10 64V54C10 43 19 38 32 38S54 43 54 54V64Z"
                fill="var(--avatar-clothing, #344e70)"
              />
              <path d="M25 36H39V47L32 53L25 47Z" fill="url(#ai-avatar-header-skin)" />
              <path
                d="M17 24C17 11 23 5 32 5S47 11 47 24V31C47 42 40 48 32 48S17 42 17 31Z"
                fill="url(#ai-avatar-header-skin)"
              />
              <path
                d="M16 27C12 15 18 4 30 3C41 1 50 9 49 21L46 28L43 17C34 19 27 17 22 13L19 28Z"
                fill="url(#ai-avatar-header-hair)"
              />
              <path d="M21 27Q25 24 29 27" fill="none" stroke="#5b3b36" stroke-width="1.8" stroke-linecap="round" />
              <path d="M35 27Q39 24 43 27" fill="none" stroke="#5b3b36" stroke-width="1.8" stroke-linecap="round" />

              <g class="ai-avatar-eyes">
                <ellipse cx="25" cy="31" rx="2" ry="2.4" fill="#27344a" />
                <ellipse cx="39" cy="31" rx="2" ry="2.4" fill="#27344a" />
              </g>

              <path d="M32 30L30 36L33 37" fill="none" stroke="#b77b68" stroke-width="1.4" stroke-linecap="round" />
              <path d="M27 41Q32 44 37 41" fill="none" stroke="#934f50" stroke-width="1.5" stroke-linecap="round" />
              <path d="M19 34Q20 39 24 40" fill="none" stroke="#e8a998" stroke-width="2" stroke-linecap="round" opacity=".7" />
              <path d="M45 34Q44 39 40 40" fill="none" stroke="#e8a998" stroke-width="2" stroke-linecap="round" opacity=".7" />
            </svg>

            <span class="ai-avatar-face-status"></span>
          </div>

          <div class="min-w-0">
            <h2 class="truncate text-sm font-bold tracking-wide text-label">
              {{ text.title }}
            </h2>

            <p class="mt-1 flex items-center gap-1.5 truncate text-xs text-muted">
              <span
                class="ai-avatar-status-dot h-1.5 w-1.5 shrink-0 rounded-full"
                :class="{ 'ai-avatar-status-thinking': isLoading }"
                aria-hidden="true"
              ></span>
              {{ isLoading ? text.thinking : (avatar?.title || text.subtitle) }}
            </p>
          </div>
        </div>

        <button
          type="button"
          class="ai-avatar-icon-button flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-xl text-muted transition focus:outline-none focus:ring-2 focus:ring-focus"
          :aria-label="text.close"
          :title="text.close"
          @pointerdown.stop
          @click="emit('close')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="h-5 w-5">
            <path d="m18 6-12 12M6 6l12 12" />
          </svg>
        </button>
      </header>

      <div
        ref="messagesContainer"
        class="ai-avatar-messages min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain px-4 py-5"
        aria-live="polite"
        aria-relevant="additions text"
      >
        <div
          v-if="messages.length === 0"
          class="flex min-h-full flex-col items-center justify-center px-4 py-8 text-center"
        >
          <div
            v-if="showDigitalAvatar"
            class="ai-avatar-welcome-stage mb-5"
            :class="faceStateClass"
          >
            <div class="ai-avatar-welcome-halo"></div>

            <div class="ai-avatar-welcome-face" :style="faceStyle">
              <svg viewBox="0 0 160 180" class="ai-avatar-portrait">
                <defs>
                  <linearGradient id="ai-avatar-welcome-skin" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="var(--avatar-skin-highlight, #ffe3d1)" />
                    <stop offset="55%" stop-color="var(--avatar-skin, #e8b49b)" />
                    <stop offset="100%" stop-color="var(--avatar-skin-shadow, #c68d79)" />
                  </linearGradient>

                  <linearGradient id="ai-avatar-welcome-hair" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="var(--avatar-hair-highlight, #53617a)" />
                    <stop offset="100%" stop-color="var(--avatar-hair, #1b263b)" />
                  </linearGradient>

                  <linearGradient id="ai-avatar-welcome-clothing" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="var(--avatar-clothing, #557ba6)" />
                    <stop offset="100%" stop-color="var(--avatar-clothing-shadow, #202e47)" />
                  </linearGradient>
                </defs>

                <ellipse cx="80" cy="174" rx="52" ry="7" fill="#0f172a" opacity=".12" />

                <path
                  d="M17 176V151C17 126 38 114 62 110L80 132L98 110C122 114 143 126 143 151V176Z"
                  fill="url(#ai-avatar-welcome-clothing)"
                />

                <path d="M63 104H97V132L80 145L63 132Z" fill="url(#ai-avatar-welcome-skin)" />

                <path
                  d="M48 53C48 29 61 17 80 17S112 29 112 53V79C112 103 98 120 80 120S48 103 48 79Z"
                  fill="url(#ai-avatar-welcome-skin)"
                />

                <path
                  d="M46 70C35 43 42 16 65 8C88 -1 115 12 119 39L113 67L106 43C89 47 70 40 58 29L51 63Z"
                  fill="url(#ai-avatar-welcome-hair)"
                />

                <path d="M54 61Q64 54 73 61" fill="none" stroke="#6c493f" stroke-width="3" stroke-linecap="round" />
                <path d="M87 61Q96 54 106 61" fill="none" stroke="#6c493f" stroke-width="3" stroke-linecap="round" />

                <g class="ai-avatar-eyes">
                  <ellipse cx="64" cy="69" rx="4.2" ry="5" fill="#25344a" />
                  <ellipse cx="96" cy="69" rx="4.2" ry="5" fill="#25344a" />
                  <circle cx="65" cy="67" r="1.3" fill="#fff" />
                  <circle cx="97" cy="67" r="1.3" fill="#fff" />
                </g>

                <path d="M80 68L75 84Q80 88 85 84" fill="none" stroke="#b47b68" stroke-width="2" stroke-linecap="round" />
                <path d="M68 96Q80 104 92 96" fill="none" stroke="#9d5558" stroke-width="2.5" stroke-linecap="round" />
                <path d="M51 78Q54 91 64 96" fill="none" stroke="#f6c2b0" stroke-width="4" stroke-linecap="round" opacity=".75" />
                <path d="M109 78Q106 91 96 96" fill="none" stroke="#f6c2b0" stroke-width="4" stroke-linecap="round" opacity=".75" />
                <path d="M62 117L80 139L98 117" fill="none" stroke="#d6e3f1" stroke-width="2" opacity=".8" />
              </svg>

              <span class="ai-avatar-portrait-glow"></span>
            </div>

            <span class="ai-avatar-orbit-dot ai-avatar-orbit-dot-one"></span>
            <span class="ai-avatar-orbit-dot ai-avatar-orbit-dot-two"></span>
          </div>

          <p class="max-w-xs text-sm font-semibold leading-6 text-label">
            {{ text.welcome }}
          </p>

          <p v-if="avatar?.description" class="mt-2 max-w-xs text-xs leading-5 text-muted">
            {{ avatar.description }}
          </p>
        </div>

        <article
          v-for="(message, index) in messages"
          :key="message.id || index"
          class="ai-avatar-message-row flex"
          :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <div
            class="ai-avatar-message max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-6"
            :class="message.role === 'user'
              ? 'ai-avatar-message-user rounded-br-md text-white'
              : 'ai-avatar-message-assistant rounded-bl-md border border-border text-label'"
          >
            <p class="whitespace-pre-wrap break-words">{{ message.content }}</p>
          </div>
        </article>

        <div v-if="isLoading" class="flex justify-start" :aria-label="text.thinking">
          <div class="ai-avatar-typing flex items-center gap-2 rounded-2xl border border-border px-4 py-3">
            <span class="ai-avatar-typing-dot h-1.5 w-1.5 rounded-full"></span>
            <span class="ai-avatar-typing-dot h-1.5 w-1.5 rounded-full"></span>
            <span class="ai-avatar-typing-dot h-1.5 w-1.5 rounded-full"></span>
          </div>
        </div>
      </div>

      <p
        v-if="errorMessage"
        class="ai-avatar-error mx-4 mb-2 rounded-xl border px-3 py-2 text-xs leading-5"
        role="alert"
      >
        {{ errorMessage }}
      </p>

      <form class="ai-avatar-composer shrink-0 border-t border-border p-3" @submit.prevent="sendMessage">
        <div class="ai-avatar-composer-inner flex items-end gap-2 rounded-2xl border p-2 transition">
          <textarea
            v-model="draft"
            class="ai-avatar-textarea max-h-32 min-h-10 min-w-0 flex-1 resize-none bg-transparent px-2 py-2 text-sm leading-5 text-label outline-none placeholder:text-muted disabled:cursor-not-allowed"
            :placeholder="text.placeholder"
            :aria-label="text.placeholder"
            :disabled="isLoading || isResolvingAvatar || !definitionCode"
            rows="1"
            maxlength="100000"
            @keydown.enter.exact.prevent="sendMessage"
          ></textarea>

          <button
            type="submit"
            class="ai-avatar-send-button flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-white transition disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="isLoading || isResolvingAvatar || !definitionCode || !draft.trim()"
            :aria-label="text.send"
            :title="text.send"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              class="h-5 w-5"
              :class="isRtl ? '-scale-x-100' : ''"
            >
              <path d="M22 2 11 13" />
              <path d="m22 2-7 20-4-9-9-4Z" />
            </svg>
          </button>
        </div>

        <p class="mt-2 px-1 text-center text-[10px] leading-4 text-muted">
          {{ text.disclaimer }}
        </p>
      </form>

      <button
        type="button"
        class="ai-avatar-resize-handle absolute bottom-0 right-0 h-6 w-6 cursor-nwse-resize"
        :aria-label="text.resize"
        :title="text.resize"
        @pointerdown.stop.prevent="startResizing"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="absolute bottom-1 right-1 h-3.5 w-3.5 text-muted">
          <path d="M21 15v6h-6M21 9v12M15 21h6" />
        </svg>
      </button>
    </section>
  </Teleport>
</template>

<script setup>
import {
  ref,
  computed,
  watch,
  onMounted,
  onBeforeUnmount,
  nextTick
} from 'vue'

import {
  language,
  languageMeta
} from '@/stores/uiStore'

import {
  useTranslation
} from '@/composables/useTranslation'
 
import {
  useAIAvatar
} from '@/composables/useAIAvatar'

import {
  useAIAvatarDefinition
} from '@/composables/useAIAvatarDefinition'

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  },
  definitionCode: {
    type: String,
    default: ''
  },
  contextVariables: {
    type: Object,
    default: () => ({})
  },
  transparency: {
    type: Number,
    default: 92
  }
}) 

const emit = defineEmits(['close'])
const { translate } = useTranslation()

const {
  getIntroduction,
  sendChatMessage
} = useAIAvatar()

const avatarDefinition = useAIAvatarDefinition()
const avatar = avatarDefinition.avatar
const isResolvingAvatar = avatarDefinition.isLoading

const messages = ref([])
const draft = ref('')
const isLoading = ref(false)

const errorMessage = ref('')
const messagesContainer = ref(null)
const panelElement = ref(null)
const text = ref({})


const position = ref({ right: 20, bottom: 20 })
const dimensions = ref({ width: 420, height: 680 })
const isDragging = ref(false)
const isResizing = ref(false)

const isRtl = computed(() => languageMeta.value?.is_rtl === true)

const definitionCode = computed(
  () => props.definitionCode.trim() || avatar.value?.definition_code || ''
)

const presentationDefinition = computed(() => {
  const definition = avatar.value?.presentation_definition

  if (definition && typeof definition === 'object' && !Array.isArray(definition)) {
    return definition
  }

  if (typeof definition === 'string') {
    try {
      const parsed = JSON.parse(definition)

      return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
        ? parsed
        : {}
    } catch {
      return {}
    }
  }

  return {}
})

const visualDefinition = computed(() => {
  const visual = presentationDefinition.value.visual

  return visual && typeof visual === 'object' && !Array.isArray(visual)
    ? visual
    : {}
})

const showDigitalAvatar = computed(() => {
  const visual = visualDefinition.value
  const presentationType = String(
    avatar.value?.presentation_type || ''
  ).trim().toUpperCase()
  const visualType = String(visual.type || '').trim().toUpperCase()

  if (visual.enabled !== true) return false

  if (
    presentationType &&
    !['AVATAR', 'DIGITAL_AVATAR'].includes(presentationType)
  ) {
    return false
  }

  return !visualType || ['AVATAR', 'DIGITAL_AVATAR'].includes(visualType)
})

const motionEnabled = computed(() => {
  const visual = visualDefinition.value

  return (
    showDigitalAvatar.value
    && visual.animation !== false
    && visual.idle_animation !== false
  )
})

const faceStateClass = computed(() => ({
  'ai-avatar-state-thinking': isLoading.value,
  'ai-avatar-motion-none': !motionEnabled.value,
  'ai-avatar-motion-subtle': motionEnabled.value
}))

const faceStyle = computed(() => {
  const visual = visualDefinition.value

  const allowedColor = value => (
    typeof value === 'string'
    && value.length <= 80
    && !/[;{}<>]/.test(value)
  ) ? value : null

  const skin = allowedColor(visual.skin_color)
  const skinHighlight = allowedColor(visual.skin_highlight_color)
  const skinShadow = allowedColor(visual.skin_shadow_color)
  const hair = allowedColor(visual.hair_color)
  const hairHighlight = allowedColor(visual.hair_highlight_color)
  const clothing = allowedColor(visual.clothing_color)
  const clothingShadow = allowedColor(visual.clothing_shadow_color)
  const accent = allowedColor(visual.accent_color)

  return {
    ...(skin ? { '--avatar-skin': skin } : {}),
    ...(skinHighlight ? { '--avatar-skin-highlight': skinHighlight } : {}),
    ...(skinShadow ? { '--avatar-skin-shadow': skinShadow } : {}),
    ...(hair ? { '--avatar-hair': hair } : {}),
    ...(hairHighlight ? { '--avatar-hair-highlight': hairHighlight } : {}),
    ...(clothing ? { '--avatar-clothing': clothing } : {}),
    ...(clothingShadow ? { '--avatar-clothing-shadow': clothingShadow } : {}),
    ...(accent ? { '--avatar-accent': accent } : {})
  }
})

const windowStyle = computed(() => ({
  right: `${position.value.right}px`,
  bottom: `${position.value.bottom}px`,
  width: `${dimensions.value.width}px`,
  height: `${dimensions.value.height}px`,
  maxWidth: 'calc(100vw - 24px)',
  maxHeight: 'calc(100dvh - 24px)',
  backgroundColor: `color-mix(in srgb, var(--color-panel) ${clampTransparency(props.transparency)}%, transparent)`,
  backdropFilter: 'blur(16px)',
  WebkitBackdropFilter: 'blur(16px)',
  touchAction: isDragging.value || isResizing.value ? 'none' : 'auto'
}))

const translationKeys = {
  title: 'AI_AVATAR_TITLE',
  subtitle: 'AI_AVATAR_SUBTITLE',
  welcome: 'AI_AVATAR_WELCOME',
  placeholder: 'AI_AVATAR_MESSAGE_PLACEHOLDER',
  send: 'AI_AVATAR_SEND',
  close: 'AI_AVATAR_CLOSE',
  resize: 'AI_AVATAR_RESIZE',
  thinking: 'AI_AVATAR_THINKING',
  missingDefinition: 'AI_AVATAR_DEFINITION_REQUIRED',
  requestError: 'AI_AVATAR_REQUEST_FAILED',
  disclaimer: 'AI_AVATAR_DISCLAIMER'
}

const fallbackText = {
  title: 'AI Avatar',
  subtitle: 'Assistant',
  welcome: 'How can I help you?',
  placeholder: 'Type your message...',
  send: 'Send',
  close: 'Close',
  resize: 'Resize AI Avatar',
  thinking: 'Thinking...',
  missingDefinition: 'No active AI Avatar definition is configured.',
  requestError: 'The request could not be completed. Please try again.',
  disclaimer: 'AI-generated responses may be inaccurate.'
}

let translationRequestId = 0
let avatarRequestId = 0
let pointerState = null

const introductionInFlight = new Set()
const introductionCompleted = new Set()

function clampTransparency(value) {
  const numericValue = Number(value)

  if (!Number.isFinite(numericValue)) {
    return 92
  }

  return Math.min(100, Math.max(15, numericValue))
}

function clampPosition() {
  const maxRight = Math.max(
    0,
    window.innerWidth
      - Math.min(dimensions.value.width, window.innerWidth - 24)
      - 12
  )

  const maxBottom = Math.max(
    0,
    window.innerHeight
      - Math.min(dimensions.value.height, window.innerHeight - 24)
      - 12
  )

  position.value.right = Math.min(maxRight, Math.max(0, position.value.right))
  position.value.bottom = Math.min(maxBottom, Math.max(0, position.value.bottom))
}

function startDragging(event) {
  if (event.button !== 0 || isResizing.value) return

  pointerState = {
    type: 'drag',
    pointerX: event.clientX,
    pointerY: event.clientY,
    right: position.value.right,
    bottom: position.value.bottom
  }

  isDragging.value = true

  window.addEventListener('pointermove', handlePointerMove)
  window.addEventListener('pointerup', stopPointerAction)
  window.addEventListener('pointercancel', stopPointerAction)
}

function startResizing(event) {
  if (event.button !== 0 || isDragging.value) return

  pointerState = {
    type: 'resize',
    pointerX: event.clientX,
    pointerY: event.clientY,
    width: dimensions.value.width,
    height: dimensions.value.height
  }

  isResizing.value = true

  window.addEventListener('pointermove', handlePointerMove)
  window.addEventListener('pointerup', stopPointerAction)
  window.addEventListener('pointercancel', stopPointerAction)
}

function handlePointerMove(event) {
  if (!pointerState) return

  const deltaX = event.clientX - pointerState.pointerX
  const deltaY = event.clientY - pointerState.pointerY

  if (pointerState.type === 'drag') {
    position.value.right = pointerState.right - deltaX
    position.value.bottom = pointerState.bottom - deltaY
    clampPosition()
    return
  }

  const direction = isRtl.value ? -1 : 1

  dimensions.value.width = Math.min(
    Math.max(300, pointerState.width + deltaX * direction),
    Math.max(300, window.innerWidth - 24)
  )

  dimensions.value.height = Math.min(
    Math.max(320, pointerState.height - deltaY),
    Math.max(320, window.innerHeight - 24)
  )

  clampPosition()
}

function stopPointerAction() {
  pointerState = null
  isDragging.value = false
  isResizing.value = false

  window.removeEventListener('pointermove', handlePointerMove)
  window.removeEventListener('pointerup', stopPointerAction)
  window.removeEventListener('pointercancel', stopPointerAction)
}

async function loadTranslations() {
  const requestId = ++translationRequestId
  const result = {}

  for (const [name, key] of Object.entries(translationKeys)) {
    try {
      const translated = await translate(key, language.value, 'GlobalUI')

      result[name] = typeof translated === 'string' && translated.trim()
        ? translated
        : fallbackText[name]
    } catch {
      result[name] = fallbackText[name]
    }
  }

  if (requestId === translationRequestId) {
    text.value = result
  }
}


async function loadDefaultAvatar() {
  const requestId = ++avatarRequestId
  const requestedCode = props.definitionCode.trim()

  errorMessage.value = ''

  try {
    const result = requestedCode
      ? await avatarDefinition.loadAvatarDefinition(requestedCode)
      : await avatarDefinition.loadDefaultAvatar()

    if (requestId !== avatarRequestId) return

    if (!result?.definition_code) {
      errorMessage.value =
        text.value.missingDefinition || fallbackText.missingDefinition
    }
  } catch (error) {
    if (requestId !== avatarRequestId) return

    errorMessage.value =
      error?.response?.data?.detail
      || error?.message
      || text.value.missingDefinition
      || fallbackText.missingDefinition
  }
}


async function loadFirstIntroduction(requestedDefinitionCode) {
  const code = requestedDefinitionCode?.trim()

  if (
    !props.open
    || !code
    || isResolvingAvatar.value
    || introductionCompleted.has(code)
    || introductionInFlight.has(code)
  ) {
    return
  }

  introductionInFlight.add(code)

  try {
    const result = await getIntroduction({
      definition_code: code,
      language_code: language.value
    })

    introductionCompleted.add(code)

    if (
      result?.show_introduction === true
      && typeof result.message === 'string'
      && result.message.trim()
      && definitionCode.value === code
    ) {
      messages.value.push({
        id: `introduction-${code}`,
        role: 'assistant',
        content: result.message
      })

      await scrollToLatest()
    }
  } catch (error) {
    console.error('AI Avatar introduction request failed:', {
      status: error?.response?.status ?? null,
      detail: error?.response?.data?.detail ?? null,
      message: error?.message ?? 'Unknown request error'
    })
  } finally {
    introductionInFlight.delete(code)
  }
}

async function scrollToLatest() {
  await nextTick()

  if (messagesContainer.value && props.open) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function normalizeResponse(response) {
  if (typeof response === 'string') return response
  if (response === null || response === undefined) return ''

  try {
    return JSON.stringify(response, null, 2)
  } catch {
    return String(response)
  }
}

async function sendMessage() {
  const message = draft.value.trim()

  if (!message || isLoading.value || isResolvingAvatar.value) return

  if (!definitionCode.value) {
    errorMessage.value =
      text.value.missingDefinition || fallbackText.missingDefinition
    return
  }

  errorMessage.value = ''
  draft.value = ''

  messages.value.push({
    id: `${Date.now()}-user`,
    role: 'user',
    content: message
  })

  isLoading.value = true
  await scrollToLatest()

  const contextVariables =
    props.contextVariables
    && typeof props.contextVariables === 'object'
    && !Array.isArray(props.contextVariables)
      ? props.contextVariables
      : {}

  try {
  
    const result = await sendChatMessage({
      definition_code: definitionCode.value,
      message,
      context_variables: contextVariables
    })

    messages.value.push({
      id: `${Date.now()}-assistant`,
      role: 'assistant',
      content: normalizeResponse(result?.response)
        || (text.value.requestError || fallbackText.requestError)
    })
  } catch (error) {
    errorMessage.value =
      error?.response?.data?.detail
      || text.value.requestError
      || fallbackText.requestError
  } finally {
    isLoading.value = false
    await scrollToLatest()
  }
}

function handleEscape(event) {
  if (event.key === 'Escape' && props.open) {
    emit('close')
  }
}

function handleWindowResize() {
  dimensions.value.width = Math.min(
    dimensions.value.width,
    Math.max(300, window.innerWidth - 24)
  )

  dimensions.value.height = Math.min(
    dimensions.value.height,
    Math.max(320, window.innerHeight - 24)
  )

  clampPosition()
}

watch(() => language.value, loadTranslations)
watch(messages, scrollToLatest, { deep: true })
watch(() => props.definitionCode, loadDefaultAvatar)

watch(
  [
    () => props.open,
    definitionCode,
    () => avatar.value?.definition_code || '',
    isResolvingAvatar
  ],
  ([isOpen, code, loadedCode, resolving]) => {
    if (isOpen && code && !resolving && loadedCode === code) {
      loadFirstIntroduction(code)
    }
  },
  { immediate: true }
)

watch(
  () => props.open,
  isOpen => {
    if (isOpen) {
      scrollToLatest()
      return
    }

    const activeElement = document.activeElement

    if (activeElement && panelElement.value?.contains(activeElement)) {
      activeElement.blur()
    }
  }
)

onMounted(() => {
  loadTranslations()
  loadDefaultAvatar()

  window.addEventListener('keydown', handleEscape)
  window.addEventListener('resize', handleWindowResize)
})

onBeforeUnmount(() => {
  translationRequestId++
  avatarRequestId++
  avatarDefinition.clearAvatarDefinition()
  stopPointerAction()

  window.removeEventListener('keydown', handleEscape)
  window.removeEventListener('resize', handleWindowResize)
})
</script>

<style scoped>
.ai-avatar-window {
  min-width: 300px;
  min-height: 320px;
  background-clip: padding-box;
  border-color: color-mix(in srgb, var(--pulsar-level-accent) 22%, var(--color-border));
  box-shadow: 0 24px 80px rgb(15 23 42 / 22%), 0 4px 16px rgb(15 23 42 / 10%);
}

.ai-avatar-window-header {
  touch-action: none;
  background:
    radial-gradient(
      circle at 0% 0%,
      color-mix(in srgb, var(--pulsar-level-accent) 17%, transparent),
      transparent 58%
    ),
    linear-gradient(
      135deg,
      var(--pulsar-level-surface),
      color-mix(in srgb, var(--pulsar-level-accent) 7%, var(--pulsar-level-surface))
    );
}

.ai-avatar-header-face {
  position: relative;
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--avatar-accent, var(--pulsar-level-accent)) 38%, transparent);
  border-radius: 15px;
  background: radial-gradient(circle at 50% 20%, #dce8f5, #879dbb 65%, #526781);
  box-shadow: 0 5px 16px color-mix(in srgb, var(--pulsar-level-accent) 22%, transparent);
}

.ai-avatar-face-svg {
  width: 100%;
  height: 100%;
}

.ai-avatar-face-status {
  position: absolute;
  right: 2px;
  bottom: 2px;
  width: 7px;
  height: 7px;
  border: 1.5px solid var(--color-panel);
  border-radius: 50%;
  background: #22c55e;
}

.ai-avatar-status-dot {
  background: #22c55e;
  box-shadow: 0 0 0 3px rgb(34 197 94 / 12%);
}

.ai-avatar-status-thinking {
  background: #f59e0b;
  box-shadow: 0 0 0 3px rgb(245 158 11 / 12%);
}

.ai-avatar-icon-button:hover {
  color: var(--pulsar-level-accent);
  background: color-mix(in srgb, var(--pulsar-level-accent) 10%, transparent);
}

.ai-avatar-messages {
  background:
    radial-gradient(
      ellipse at 0% 0%,
      color-mix(in srgb, var(--pulsar-level-accent) 5%, transparent),
      transparent 55%
    ),
    var(--color-panel);
  scrollbar-width: thin;
  scrollbar-color: color-mix(in srgb, var(--pulsar-level-accent) 30%, transparent) transparent;
}

.ai-avatar-messages::-webkit-scrollbar {
  width: 6px;
}

.ai-avatar-messages::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: color-mix(in srgb, var(--pulsar-level-accent) 30%, transparent);
}

.ai-avatar-welcome-stage {
  position: relative;
  display: grid;
  width: 176px;
  height: 190px;
  place-items: end center;
  isolation: isolate;
}

.ai-avatar-welcome-halo {
  position: absolute;
  z-index: -1;
  top: 10px;
  width: 170px;
  height: 160px;
  border: 1px solid color-mix(in srgb, var(--avatar-accent, var(--pulsar-level-accent)) 24%, transparent);
  border-radius: 50%;
  background: radial-gradient(
    ellipse,
    color-mix(in srgb, var(--avatar-accent, var(--pulsar-level-accent)) 16%, transparent),
    transparent 70%
  );
  box-shadow: 0 0 44px color-mix(in srgb, var(--pulsar-level-accent) 10%, transparent);
}

.ai-avatar-welcome-face {
  position: relative;
  width: 154px;
  height: 174px;
  overflow: hidden;
  border-radius: 48% 48% 36% 36%;
  background: linear-gradient(150deg, #dce8f5, #849bb7 72%, #4c617c);
  box-shadow: 0 12px 32px rgb(15 23 42 / 17%), inset 0 1px 0 rgb(255 255 255 / 70%);
}

.ai-avatar-portrait {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 3px 3px rgb(15 23 42 / 9%));
}

.ai-avatar-portrait-glow {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(
    115deg,
    rgb(255 255 255 / 22%),
    transparent 38%,
    transparent 72%,
    rgb(255 255 255 / 10%)
  );
}

.ai-avatar-orbit-dot {
  position: absolute;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--avatar-accent, var(--pulsar-level-accent));
  box-shadow: 0 0 12px color-mix(in srgb, var(--avatar-accent, var(--pulsar-level-accent)) 55%, transparent);
}

.ai-avatar-orbit-dot-one {
  top: 43px;
  left: 4px;
}

.ai-avatar-orbit-dot-two {
  top: 85px;
  right: 0;
  width: 5px;
  height: 5px;
}

.ai-avatar-motion-subtle .ai-avatar-welcome-face {
  animation: ai-avatar-breathe 4.8s ease-in-out infinite;
}

.ai-avatar-motion-subtle .ai-avatar-welcome-halo {
  animation: ai-avatar-halo 6s ease-in-out infinite;
}

.ai-avatar-motion-subtle .ai-avatar-orbit-dot-one {
  animation: ai-avatar-orbit 7s ease-in-out infinite;
}

.ai-avatar-motion-subtle .ai-avatar-orbit-dot-two {
  animation: ai-avatar-orbit 5.5s ease-in-out infinite reverse;
}

.ai-avatar-motion-subtle .ai-avatar-eyes {
  transform-box: fill-box;
  transform-origin: center;
  animation: ai-avatar-blink 6.5s infinite;
}

.ai-avatar-motion-none .ai-avatar-welcome-face,
.ai-avatar-motion-none .ai-avatar-welcome-halo,
.ai-avatar-motion-none .ai-avatar-orbit-dot-one,
.ai-avatar-motion-none .ai-avatar-orbit-dot-two,
.ai-avatar-motion-none .ai-avatar-eyes {
  animation: none;
}

.ai-avatar-state-thinking.ai-avatar-motion-subtle .ai-avatar-welcome-face {
  animation-duration: 2.4s;
}

.ai-avatar-state-thinking .ai-avatar-welcome-halo {
  opacity: 1;
  box-shadow: 0 0 56px color-mix(in srgb, var(--pulsar-level-accent) 22%, transparent);
}

.ai-avatar-message {
  overflow-wrap: anywhere;
  box-shadow: 0 2px 8px rgb(15 23 42 / 4%);
  animation: ai-avatar-message-in 180ms ease-out both;
}

.ai-avatar-message-user {
  background: linear-gradient(
    135deg,
    var(--pulsar-level-accent),
    color-mix(in srgb, var(--pulsar-level-accent) 72%, #7c3aed)
  );
  box-shadow: 0 4px 12px color-mix(in srgb, var(--pulsar-level-accent) 16%, transparent);
}

.ai-avatar-message-assistant {
  background: color-mix(in srgb, var(--color-panel) 94%, var(--pulsar-level-accent));
  border-color: color-mix(in srgb, var(--pulsar-level-accent) 12%, var(--color-border));
}

.ai-avatar-typing {
  background: color-mix(in srgb, var(--color-panel) 94%, var(--pulsar-level-accent));
}

.ai-avatar-typing-dot {
  background: var(--pulsar-level-accent);
  animation: ai-avatar-typing 1s ease-in-out infinite;
}

.ai-avatar-typing-dot:nth-child(2) {
  animation-delay: 150ms;
}

.ai-avatar-typing-dot:nth-child(3) {
  animation-delay: 300ms;
}

.ai-avatar-error {
  color: #dc2626;
  border-color: rgb(239 68 68 / 25%);
  background: rgb(239 68 68 / 7%);
}

.ai-avatar-composer {
  background: color-mix(in srgb, var(--pulsar-level-surface) 88%, transparent);
}

.ai-avatar-composer-inner {
  border-color: color-mix(in srgb, var(--pulsar-level-accent) 20%, var(--color-border));
  background: var(--color-panel);
  box-shadow: 0 3px 12px rgb(15 23 42 / 4%);
}

.ai-avatar-composer-inner:focus-within {
  border-color: var(--pulsar-level-accent);
  box-shadow:
    0 0 0 3px color-mix(in srgb, var(--pulsar-level-accent) 13%, transparent),
    0 3px 12px rgb(15 23 42 / 4%);
}

.ai-avatar-send-button {
  background: linear-gradient(
    145deg,
    var(--pulsar-level-accent),
    color-mix(in srgb, var(--pulsar-level-accent) 72%, #7c3aed)
  );
  box-shadow: 0 4px 10px color-mix(in srgb, var(--pulsar-level-accent) 22%, transparent);
}

.ai-avatar-send-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 15px color-mix(in srgb, var(--pulsar-level-accent) 30%, transparent);
}

.ai-avatar-send-button:active:not(:disabled) {
  transform: translateY(0);
}

.ai-avatar-textarea::placeholder {
  opacity: 0.75;
}

.ai-avatar-dragging {
  user-select: none;
  cursor: grabbing;
}

.ai-avatar-resize-handle {
  background: transparent;
  border: 0;
  color: var(--pulsar-level-accent);
}

.ai-avatar-resize-handle:hover {
  color: var(--pulsar-level-accent);
  background: color-mix(in srgb, var(--pulsar-level-accent) 8%, transparent);
  border-top-left-radius: 10px;
}

@keyframes ai-avatar-message-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes ai-avatar-typing {
  0%, 60%, 100% {
    opacity: 0.35;
    transform: translateY(0);
  }

  30% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

@keyframes ai-avatar-blink {
  0%, 45%, 48%, 72%, 75%, 100% {
    transform: scaleY(1);
  }

  46.5%, 73.5% {
    transform: scaleY(0.12);
  }
}

@keyframes ai-avatar-breathe {
  0%, 100% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-3px);
  }
}

@keyframes ai-avatar-halo {
  0%, 100% {
    transform: scale(1);
    opacity: 0.7;
  }

  50% {
    transform: scale(1.035);
    opacity: 1;
  }
}

@keyframes ai-avatar-orbit {
  0%, 100% {
    transform: translateY(0);
    opacity: 0.7;
  }

  50% {
    transform: translateY(-7px);
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ai-avatar-message,
  .ai-avatar-typing-dot,
  .ai-avatar-motion-subtle .ai-avatar-welcome-face,
  .ai-avatar-motion-subtle .ai-avatar-welcome-halo,
  .ai-avatar-motion-subtle .ai-avatar-orbit-dot-one,
  .ai-avatar-motion-subtle .ai-avatar-orbit-dot-two,
  .ai-avatar-motion-subtle .ai-avatar-eyes {
    animation: none;
  }

  .ai-avatar-send-button {
    transition: none;
  }
}
</style>
