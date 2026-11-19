/*
File: frontend/src/composables/useAIAvatarDefinition.js
Description: Owns AI Avatar definition state and its loading lifecycle
Change Date: 2026-10-18 21:21; Timezone: Asia/Baku
Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
*/

import { readonly, ref } from 'vue'
import { useAIAvatar } from '@/composables/useAIAvatar'

export function useAIAvatarDefinition() {
  const avatarState = ref(null)
  const isLoadingState = ref(false)

  const {
    getDefaultAvatar,
    getAvatarDefinition
  } = useAIAvatar()

  let requestId = 0

  async function loadDefinition(loader, operationName) {
    const currentRequestId = ++requestId

    isLoadingState.value = true

    try {
      const definition = await loader()

      if (currentRequestId !== requestId) {
        return null
      }

      if (!definition || typeof definition !== 'object' || Array.isArray(definition)) {
        throw new Error(`The AI Avatar definition returned by ${operationName} is invalid.`)
      }

      avatarState.value = definition

      return definition
    } catch (error) {
      if (currentRequestId === requestId) {
        console.error(`[Avatar Trace] ${operationName}: ERROR`, error)
        avatarState.value = null
      }

      if (currentRequestId !== requestId) {
        return null
      }

      throw error
    } finally {
      if (currentRequestId === requestId) {
        isLoadingState.value = false
      }
    }
  }

  function loadDefaultAvatar() {
    console.info('[Avatar Trace] loadDefaultAvatar: START')
    return loadDefinition(
      () => getDefaultAvatar(),
      'getDefaultAvatar'
    )
  }

  function loadAvatarDefinition(definitionCode) {
    const normalizedCode = typeof definitionCode === 'string'
      ? definitionCode.trim()
      : ''

    if (!normalizedCode) {
      return Promise.reject(
        new Error('An AI Avatar definition code is required.')
      )
    }

    if (typeof getAvatarDefinition !== 'function') {
      return Promise.reject(
        new Error('Loading an AI Avatar by definition code is not implemented in useAIAvatar.')
      )
    }

    return loadDefinition(
      () => getAvatarDefinition(normalizedCode),
      'getAvatarDefinition'
    )
  }

  function clearAvatarDefinition() {
    requestId += 1
    avatarState.value = null
    isLoadingState.value = false
  }

  return {
    avatar: readonly(avatarState),
    isLoading: readonly(isLoadingState),
    loadDefaultAvatar,
    loadAvatarDefinition,
    clearAvatarDefinition
  }
}
