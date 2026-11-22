// ===============================================
// File: frontend/src/composables/useSystemMetrics.js
// Description: Shared system resource metrics state and polling lifecycle
// Change Date: 2026-11-23
// Timezone: Asia/Baku
// In collaboration with GPT4 Chat Assistant: Bahram
// ===============================================

import { ref } from 'vue'
import axiosInstance from '@/utils/axiosInstance'

const systemMetrics = ref({
  cpu: 0,
  memory: 0,
  memoryUsed: 0,
  memoryTotal: 0,
  logicalCores: 0
})

const systemMetricsOnline = ref(false)

let pollingTimer = null
let requestPending = false

async function fetchSystemMetrics() {
  if (requestPending) return

  requestPending = true

  try {
    const response = await axiosInstance.get('/admin/system/metrics')
    const data = response.data

    systemMetrics.value = {
      cpu: Math.min(100, Math.max(0, Number(data.cpu?.percent) || 0)),
      memory: Math.min(100, Math.max(0, Number(data.memory?.percent) || 0)),
      memoryUsed: Number(data.memory?.used_bytes) || 0,
      memoryTotal: Number(data.memory?.total_bytes) || 0,
      logicalCores: Number(data.cpu?.logical_cores) || 0
    }

    systemMetricsOnline.value = true
  } catch (error) {
    systemMetricsOnline.value = false
    console.warn('[PULSAR SYSTEM MONITOR] Metrics unavailable.', error)
  } finally {
    requestPending = false
  }
}

function startSystemMetrics() {
  if (pollingTimer !== null) return

  fetchSystemMetrics()
  pollingTimer = setInterval(fetchSystemMetrics, 3000)
}

function stopSystemMetrics() {
  if (pollingTimer !== null) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

export function useSystemMetrics() {
  return {
    systemMetrics,
    systemMetricsOnline,
    startSystemMetrics,
    stopSystemMetrics
  }
}
