/*
File: Pulsar/frontend/src/composables/usePaliAnalystAnalysis.js
Description: API composable for persistent Pali Analyst Function output sessions
Change Date: 2026-11-21 04:00; Timezone: Asia/Baku
Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
*/

import axios from '@/utils/axiosInstance'

const API_ENDPOINTS = Object.freeze({
  CREATE: Object.freeze({
    method: 'post',
    path: '/ai-avatar/function-output-analysis-sessions'
  }),
  GET: Object.freeze({
    method: 'get',
    path: '/ai-avatar/function-output-analysis-sessions'
  }),
  CHECKPOINT: Object.freeze({
    method: 'patch',
    path: '/ai-avatar/function-output-analysis-sessions'
  })
})

export function usePaliAnalystAnalysis() {
  async function createSession(report, definitionCode, outputConfigId) {
    if (!report || typeof report !== 'object' || Array.isArray(report)) {
      throw new Error('A valid Function output report is required.')
    }

    if (typeof definitionCode !== 'string' || !definitionCode.trim()) {
      throw new Error('The Pali Analyst definition code is required.')
    }

    const normalizedConfigId = Number(outputConfigId)
    if (!Number.isInteger(normalizedConfigId) || normalizedConfigId < 1) {
      throw new Error('A valid Function output configuration ID is required.')
    }

    const response = await axios.request({
      method: API_ENDPOINTS.CREATE.method,
      url: API_ENDPOINTS.CREATE.path,
      data: {
        output_config_id: normalizedConfigId,
        definition_code: definitionCode.trim(),
        report
      },
      timeout: 120000
    })

    return response.data
  }

  async function getSession(sessionId) {
    const normalizedId = normalizeSessionId(sessionId)
    const response = await axios.request({
      method: API_ENDPOINTS.GET.method,
      url: `${API_ENDPOINTS.GET.path}/${encodeURIComponent(normalizedId)}`,
      timeout: 60000
    })

    return response.data
  }

  async function saveCheckpoint(sessionId, payload) {
    const normalizedId = normalizeSessionId(sessionId)

    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      throw new Error('A valid Pali Analyst checkpoint is required.')
    }

    const response = await axios.request({
      method: API_ENDPOINTS.CHECKPOINT.method,
      url: `${API_ENDPOINTS.CHECKPOINT.path}/${encodeURIComponent(normalizedId)}/checkpoint`,
      data: payload,
      timeout: 60000
    })

    return response.data
  }

  function normalizeSessionId(value) {
    if (typeof value !== 'string' || !/^[0-9a-f-]{36}$/i.test(value)) {
      throw new Error('A valid Pali Analyst analysis session ID is required.')
    }

    return value
  }

  return {
    createSession,
    getSession,
    saveCheckpoint
  }
}
