
/*
File: frontend/src/composables/useAIAvatar.js
Description: API composable for the metadata-driven AI Avatar runtime
Change Date: 2026-11-20 13:00; Timezone: Asia/Baku
Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
*/

import axios from '@/utils/axiosInstance'

const API_ENDPOINTS = Object.freeze({
  AI_AVATAR_DEFAULT: Object.freeze({
    method: 'get',
    path: '/ai-avatar/default'
  }),
  AI_AVATAR_INTRODUCTION: Object.freeze({
    method: 'post',
    path: '/ai-avatar/introduction'
  }),
  AI_AVATAR_CHAT: Object.freeze({
    method: 'post',
    path: '/ai-avatar/chat'
  })
})

export function useAIAvatar() {

  async function requestAvatarDefinition(avatarManagerId = 3) {
    const normalizedManagerId = Number(avatarManagerId)

    if (
      !Number.isInteger(normalizedManagerId) ||
      normalizedManagerId < 1
    ) {
      throw new Error('A valid AI Avatar manager ID is required.')
    }

    const endpoint = API_ENDPOINTS.AI_AVATAR_DEFAULT

    try {
      const response = await axios.request({
        method: endpoint.method,
        url: endpoint.path,
        params: {
          avatar_manager_id: normalizedManagerId
        }
      })

      const data = response.data

      if (!data || typeof data !== 'object' || Array.isArray(data)) {
        throw new Error('The AI Avatar definition response is invalid.')
      }

      const definition = normalizeAvatarDefinition(data)

      if (
        definition.avatar_manager_id !== undefined &&
        Number(definition.avatar_manager_id) !== normalizedManagerId
      ) {
        throw new Error(
          `The requested manager ID ${normalizedManagerId} does not match the returned avatar definition.`
        )
      }

      return definition
    } catch (error) {
      logRequestError(
        'Avatar Trace 2: Default avatar definition request failed:',
        error
      )
      throw error
    }
  }

  async function getDefaultAvatar(avatarManagerId = 3) {
    console.info(
      `[Avatar Trace 2] getDefaultAvatar: START (Manager ${avatarManagerId})`
    )

    try {
      const definition = await requestAvatarDefinition(avatarManagerId)

      return definition
    } catch (error) {
      console.error(
        '[Avatar Trace 2] getDefaultAvatar: FAILED',
        error
      )
      throw error
    }
  }

  async function getAvatarDefinition(definitionCode, avatarManagerId = 3) {
    const normalizedCode = typeof definitionCode === 'string'
      ? definitionCode.trim()
      : ''

    if (!normalizedCode) {
      throw new Error('AI Avatar definition code is required.')
    }

    const definition = await requestAvatarDefinition(avatarManagerId)

    if (definition.definition_code !== normalizedCode) {
      throw new Error(
        `The existing default-avatar endpoint returned "${definition.definition_code || 'unknown'}" instead of "${normalizedCode}". A backend endpoint for loading a specific AI Avatar definition is required.`
      )
    }

    return definition
  }

  function normalizeAvatarDefinition(data) {
    return {
      ...data,
      presentation_code:
        typeof data.presentation_code === 'string'
          ? data.presentation_code
          : '',
      presentation_type:
        typeof data.presentation_type === 'string'
          ? data.presentation_type
          : '',
      presentation_definition: normalizePresentationDefinition(
        data.presentation_definition
      )
    }
  }

  function normalizePresentationDefinition(value) {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return value
    }

    if (typeof value === 'string' && value.trim()) {
      try {
        const parsed = JSON.parse(value)

        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
          return parsed
        }
      } catch (error) {
        console.error(
          '[Avatar Trace 2N] Failed to parse presentation metadata:',
          error
        )
      }
    }

    return {}
  }

  async function getIntroduction(payload) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      throw new Error('A valid AI Avatar introduction request is required.')
    }

    if (
      typeof payload.definition_code !== 'string' ||
      !payload.definition_code.trim()
    ) {
      throw new Error('AI Avatar definition code is required.')
    }

    const languageCode =
      typeof payload.language_code === 'string'
        ? payload.language_code.trim()
        : ''

    try {
      const response = await axios.request({
        method: API_ENDPOINTS.AI_AVATAR_INTRODUCTION.method,
        url: API_ENDPOINTS.AI_AVATAR_INTRODUCTION.path,
        data: {
          definition_code: payload.definition_code.trim(),
          language_code: languageCode || null
        }
      })

      return response.data
    } catch (error) {
      logRequestError('AI Avatar introduction request failed:', error)
      throw error
    }
  }

  async function sendChatMessage(payload) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      throw new Error('A valid AI Avatar request payload is required.')
    }

    if (
      typeof payload.definition_code !== 'string' ||
      !payload.definition_code.trim()
    ) {
      throw new Error('AI Avatar definition code is required.')
    }

    if (typeof payload.message !== 'string' || !payload.message.trim()) {
      throw new Error('A non-empty message is required.')
    }

    try {
      const response = await axios.request({
        method: API_ENDPOINTS.AI_AVATAR_CHAT.method,
        url: API_ENDPOINTS.AI_AVATAR_CHAT.path,
        data: {
          definition_code: payload.definition_code.trim(),
          message: payload.message,
          context_variables: payload.context_variables || {}
        },
        timeout: 120000
      })

      return response.data
    } catch (error) {
      logRequestError('AI Avatar request failed:', error)
      throw error
    }
  }

  function logRequestError(message, error) {
    console.error(message, {
      status: error?.response?.status ?? null,
      detail: error?.response?.data?.detail ?? null,
      response: error?.response?.data ?? null,
      message: error?.message ?? 'Unknown request error',
      code: error?.code ?? null
    })
  }

  return {
    getDefaultAvatar,
    getAvatarDefinition,
    getIntroduction,
    sendChatMessage
  }
}
