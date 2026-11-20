/*
File: Pulsar/frontend/src/composables/useSourceTraceAnalysis.js
Description: API composable for persistent P-ATVT interactive analysis sessions
Change Date: 2026-11-20 18:30; Timezone: Asia/Baku
Author: MHKolahi@gmail.com
In collaboration with GPT4 Chat Assistant: Bahram
*/

import axios from '@/utils/axiosInstance'

const API_ENDPOINTS = Object.freeze({
  CREATE: Object.freeze({
    method: 'post',
    path: '/source-trace/analysis-sessions'
  }),
  GET: Object.freeze({
    method: 'get',
    path: '/source-trace/analysis-sessions'
  }),
  CHECKPOINT: Object.freeze({
    method: 'patch',
    path: '/source-trace/analysis-sessions'
  })
})

export function useSourceTraceAnalysis() {
  async function createSession(report, definitionCode) {
    if (!report || typeof report !== 'object' || Array.isArray(report)) {
      throw new Error('A valid Source Trace report is required.')
    }

    const topic = typeof report.topic === 'string'
      ? report.topic.trim()
      : ''

    if (!topic) {
      throw new Error('The Source Trace topic is missing.')
    }

    if (typeof definitionCode !== 'string' || !definitionCode.trim()) {
      throw new Error('The Pali Tracer definition code is required.')
    }

    const response = await axios.request({
      method: API_ENDPOINTS.CREATE.method,
      url: API_ENDPOINTS.CREATE.path,
      data: {
        topic,
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
      throw new Error('A valid analysis checkpoint is required.')
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
      throw new Error('A valid Source Trace analysis session ID is required.')
    }

    return value
  }

  return {
    createSession,
    getSession,
    saveCheckpoint
  }
}
