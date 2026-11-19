<!--
File: Pulsar/frontend/src/components/tools/source_trace_panel.vue
Version: 1.1
Modified: 2026-11-19 00:51 Asia/Baku
In collaboration with GPT4 Chat Assistant: Bahram
-->
<template>
  <Teleport to="body">
    <Transition name="trace-fade">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-[100] flex items-center justify-center bg-black/45 p-3 backdrop-blur-sm sm:p-6"
        @click.self="close"
      >
        <section
          class="trace-panel flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl border border-border bg-panel shadow-2xl"
          dir="ltr"
          role="dialog"
          aria-modal="true"
          aria-labelledby="source-trace-title"
        >
          <header class="flex items-center justify-between border-b border-border px-5 py-4">
            <div class="flex items-center gap-3">
              <div
                class="flex h-10 w-10 items-center justify-center rounded-xl"
                style="background:var(--pulsar-level-accent-soft);color:var(--pulsar-level-accent)"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="h-5 w-5">
                  <circle cx="6" cy="6" r="2.5" />
                  <circle cx="18" cy="6" r="2.5" />
                  <circle cx="12" cy="18" r="2.5" />
                  <path d="M8.5 6h7M7.5 8l3.2 7.7M16.5 8l-3.2 7.7" />
                </svg>
              </div>
              <div>
                <h2 id="source-trace-title" class="text-base font-semibold text-label">Source Trace</h2>
                <p class="text-xs text-muted">Static repository analysis · P-ATVT</p>
              </div>
            </div>

            <button type="button" class="trace-icon-button" title="Close" aria-label="Close" @click="close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-5 w-5">
                <path d="m18 6-12 12M6 6l12 12" />
              </svg>
            </button>
          </header>

          <div class="grid min-h-0 flex-1 gap-5 overflow-y-auto p-5 lg:grid-cols-[280px_minmax(0,1fr)]">
            <aside class="space-y-5">
              <div>
                <label for="trace-topic" class="mb-2 block text-xs font-semibold uppercase tracking-wider text-muted">
                  Trace Topic
                </label>
                <input
                  id="trace-topic"
                  v-model.trim="topic"
                  type="text"
                  maxlength="160"
                  autocomplete="off"
                  placeholder="e.g. profile_id"
                  class="trace-input"
                  @keydown.enter.prevent="runTrace"
                />
              </div>

              <fieldset>
                <legend class="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">Source Scope</legend>
                <div class="space-y-2">
                  <label v-for="item in scopeOptions" :key="item.value" class="trace-option">
                    <input v-model="scope" type="checkbox" :value="item.value" />
                    <span>{{ item.label }}</span>
                  </label>
                </div>
              </fieldset>

              <fieldset>
                <legend class="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">Relationships</legend>
                <div class="space-y-2">
                  <label v-for="item in relationOptions" :key="item.value" class="trace-option">
                    <input v-model="relations" type="checkbox" :value="item.value" />
                    <span>{{ item.label }}</span>
                  </label>
                </div>
              </fieldset>

              <div>
                <div class="mb-2 flex items-center justify-between">
                  <label for="trace-depth" class="text-xs font-semibold uppercase tracking-wider text-muted">Trace Depth</label>
                  <span class="text-xs font-semibold text-label">{{ depth }}</span>
                </div>
                <input
                  id="trace-depth"
                  v-model.number="depth"
                  type="range"
                  min="1"
                  max="8"
                  step="1"
                  class="w-full accent-[var(--pulsar-level-accent)]"
                />
              </div>

              <button type="button" class="trace-run-button" :disabled="!canRun" @click="runTrace">
                <svg v-if="loading" class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 2a10 10 0 1 0 10 10" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
                  <path d="M5 12h14M13 6l6 6-6 6" />
                </svg>
                {{ loading ? 'TRACING...' : 'TRACE' }}
              </button>

              <p v-if="error" role="alert" class="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-500">
                {{ error }}
              </p>
            </aside>

            <section class="flex min-h-[360px] min-w-0 flex-col overflow-hidden rounded-xl border border-border bg-app">
              <div class="flex items-center justify-between border-b border-border px-4 py-3">
                <div>
                  <h3 class="text-sm font-semibold text-label">Trace Output</h3>
                  <p class="text-[11px] text-muted">
                    {{ result ? `Analysis completed · ${result.version || 'Source Trace'}` : 'Results will appear here' }}
                  </p>
                </div>
                <button v-if="result" type="button" class="trace-copy-button" @click="copyResult">
                  {{ copied ? 'Copied' : 'Copy JSON' }}
                </button>
              </div>

              <div v-if="!result && !loading" class="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
                <div class="flex h-14 w-14 items-center justify-center rounded-2xl border border-border text-muted">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="h-7 w-7">
                    <circle cx="11" cy="11" r="7" />
                    <path d="m16 16 5 5" />
                  </svg>
                </div>
                <p class="text-sm font-medium text-label">Ready to trace</p>
                <p class="max-w-xs text-xs leading-5 text-muted">
                  Enter a topic, choose the source layers and relationships, then run the analysis.
                </p>
              </div>

              <div v-else-if="loading" class="flex flex-1 items-center justify-center text-sm text-muted">
                Analyzing source files...
              </div>

              <div v-else class="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">
                <div v-if="result.summary" class="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  <div v-for="item in summaryItems" :key="item.key" class="trace-stat">
                    <span>{{ item.label }}</span>
                    <strong>{{ result.summary[item.key] ?? 0 }}</strong>
                  </div>
                </div>

                <div v-if="result.summary?.graph_edges" class="flex flex-wrap gap-2 text-[11px]">
                  <span class="trace-meta">Structural: {{ result.summary.graph_edges.structural ?? 0 }}</span>
                  <span class="trace-meta">Semantic: {{ result.summary.graph_edges.semantic ?? 0 }}</span>
                  <span class="trace-meta">Seeds: {{ result.summary.selected_seeds ?? result.seeds?.length ?? 0 }}</span>
                  <span v-if="result.summary.traversal_truncated" class="trace-meta trace-warning">Traversal truncated</span>
                </div>

                <div v-if="result.seeds?.length">
                  <h4 class="trace-section-title">Selected Seeds ({{ result.seeds.length }})</h4>
                  <div class="space-y-1">
                    <div v-for="seed in result.seeds" :key="seed.node_id" class="trace-list-item">
                      <span class="font-mono">{{ seed.node_id }}</span>
                      <span class="trace-meta">Score {{ seed.score }}</span>
                    </div>
                  </div>
                </div>

                <div v-if="result.files?.length">
                  <h4 class="trace-section-title">Related Files ({{ result.files.length }})</h4>
                  <div class="max-h-40 space-y-1 overflow-y-auto rounded-lg border border-border p-3">
                    <div v-for="file in result.files" :key="file" class="break-all font-mono text-[11px] text-label">
                      {{ file }}
                    </div>
                  </div>
                </div>

                <div v-if="result.edges?.length">
                  <h4 class="trace-section-title">Relationships ({{ result.edges.length }})</h4>
                  <div class="space-y-2">
                    <div v-for="(edge, index) in result.edges" :key="`${edge.source}:${edge.relation}:${edge.target}:${index}`" class="rounded-lg border border-border p-3">
                      <div class="flex flex-wrap items-center gap-2 text-[11px]">
                        <span class="font-semibold text-label">{{ edge.relation }}</span>
                        <span class="trace-meta">{{ edge.confidence }}</span>
                        <span class="trace-meta">{{ edge.graph }}</span>
                      </div>
                      <p class="mt-2 break-all font-mono text-[10px] text-muted">{{ edge.source }} → {{ edge.target }}</p>
                      <p v-if="edge.evidence" class="mt-1 break-words text-[10px] leading-4 text-muted">{{ edge.evidence }}</p>
                    </div>
                  </div>
                </div>

                <div v-if="result.nodes?.length">
                  <h4 class="trace-section-title">Trace Nodes ({{ result.nodes.length }})</h4>
                  <div class="max-h-64 space-y-1 overflow-y-auto rounded-lg border border-border p-2">
                    <div v-for="node in result.nodes" :key="node.id" class="rounded-md px-2 py-1.5 hover:bg-panel">
                      <div class="flex flex-wrap items-center gap-2 text-[10px]">
                        <span class="font-semibold text-label">{{ node.kind }}</span>
                        <span class="trace-meta">Depth {{ node.depth }}</span>
                        <span class="text-muted">{{ node.name }}</span>
                      </div>
                      <p class="mt-1 break-all font-mono text-[10px] text-muted">{{ node.file }}:{{ node.line }}</p>
                    </div>
                  </div>
                </div>

                <div v-if="result.limitations?.length">
                  <details class="rounded-lg border border-border p-3">
                    <summary class="cursor-pointer text-xs font-semibold text-muted">Analysis limitations ({{ result.limitations.length }})</summary>
                    <ul class="mt-2 list-disc space-y-1 pl-4 text-[10px] leading-4 text-muted">
                      <li v-for="(item, index) in result.limitations" :key="index">{{ item }}</li>
                    </ul>
                  </details>
                </div>

                <pre v-if="!hasStructuredResult" class="overflow-x-auto whitespace-pre-wrap text-xs text-label">{{ JSON.stringify(result, null, 2) }}</pre>
              </div>
            </section>
          </div>

          <footer class="flex items-center justify-between border-t border-border px-5 py-3">
            <span class="text-[10px] text-muted">Static source analysis · Not runtime proof</span>
            <button type="button" class="trace-secondary-button" @click="close">Close</button>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, inject, ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'trace-completed'])
const sourceTraceRunner = inject('sourceTraceRunner', null)

const topic = ref('')
const scope = ref(['frontend', 'backend', 'database'])
const relations = ref(['calls', 'imports', 'api', 'references', 'sql'])
const depth = ref(3)
const loading = ref(false)
const error = ref('')
const result = ref(null)
const copied = ref(false)

const scopeOptions = [
  { label: 'Frontend', value: 'frontend' },
  { label: 'Backend', value: 'backend' },
  { label: 'Database / SQL', value: 'database' }
]

const relationOptions = [
  { label: 'Function Calls', value: 'calls' },
  { label: 'Module Imports', value: 'imports' },
  { label: 'API Routes', value: 'api' },
  { label: 'Model / Symbol References', value: 'references' },
  { label: 'SQL / ORM Relationships', value: 'sql' }
]

const summaryItems = [
  { key: 'files_scanned', label: 'Files Scanned' },
  { key: 'matched_nodes', label: 'Matched Nodes' },
  { key: 'trace_nodes', label: 'Trace Nodes' },
  { key: 'trace_edges', label: 'Relationships' },
  { key: 'files_in_trace', label: 'Related Files' }
]

const canRun = computed(() => Boolean(topic.value && scope.value.length && relations.value.length && !loading.value))
const hasStructuredResult = computed(() => Boolean(
  result.value && (result.value.summary || result.value.files || result.value.nodes || result.value.edges)
))

const requestOptions = computed(() => ({
  topic: topic.value,
  scope: [...scope.value],
  relations: [...relations.value],
  depth: depth.value,
  max_nodes: 160
}))

function close() {
  emit('update:modelValue', false)
}

async function runTrace() {
  if (!canRun.value) return

  if (typeof sourceTraceRunner !== 'function') {
    error.value = 'Source Trace service is not registered.'
    return
  }

  loading.value = true
  error.value = ''
  result.value = null
  copied.value = false

  try {
    const response = await sourceTraceRunner(requestOptions.value)
    const payload = response?.data ?? response

    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      throw new Error('Source Trace returned an invalid response.')
    }

    result.value = payload
    emit('trace-completed', payload)
  } catch (exception) {
    error.value = exception?.response?.data?.detail
      || exception?.message
      || 'Source trace failed.'
  } finally {
    loading.value = false
  }
}

async function copyResult() {
  if (!result.value) return

  try {
    if (!navigator?.clipboard?.writeText) {
      throw new Error('Clipboard access is unavailable.')
    }

    await navigator.clipboard.writeText(JSON.stringify(result.value, null, 2))
    copied.value = true
    error.value = ''
  } catch (exception) {
    error.value = exception?.message || 'Unable to copy the result.'
  }
}

watch(() => props.modelValue, opened => {
  if (opened) {
    error.value = ''
    copied.value = false
  }
})
</script>

<style scoped>
.trace-panel {
  color: var(--color-label);
}

.trace-input {
  width: 100%;
  height: 42px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-app);
  padding: 0 12px;
  color: var(--color-label);
  font-size: 13px;
  outline: none;
  transition: border-color .2s ease, box-shadow .2s ease;
}

.trace-input:focus {
  border-color: var(--pulsar-level-accent);
  box-shadow: 0 0 0 3px var(--pulsar-level-accent-soft);
}

.trace-option {
  display: flex;
  align-items: center;
  gap: 9px;
  cursor: pointer;
  color: var(--color-label);
  font-size: 12px;
}

.trace-option input {
  width: 15px;
  height: 15px;
  accent-color: var(--pulsar-level-accent);
}

.trace-run-button {
  display: flex;
  width: 100%;
  height: 42px;
  align-items: center;
  justify-content: center;
  gap: 9px;
  border-radius: 10px;
  background: var(--pulsar-level-accent);
  color: white;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .08em;
  transition: opacity .2s ease, transform .2s ease;
}

.trace-run-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.trace-run-button:disabled {
  cursor: not-allowed;
  opacity: .45;
}

.trace-icon-button {
  display: flex;
  width: 36px;
  height: 36px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  color: var(--color-muted);
}

.trace-icon-button:hover,
.trace-secondary-button:hover,
.trace-copy-button:hover {
  border-color: var(--pulsar-level-accent);
  color: var(--pulsar-level-accent);
}

.trace-stat {
  display: flex;
  flex-direction: column;
  gap: 5px;
  border: 1px solid var(--color-border);
  border-radius: 9px;
  padding: 10px;
}

.trace-stat span {
  color: var(--color-muted);
  font-size: 10px;
}

.trace-stat strong {
  color: var(--color-label);
  font-size: 18px;
  font-weight: 700;
}

.trace-meta {
  display: inline-flex;
  align-items: center;
  border-radius: 6px;
  background: var(--color-panel);
  padding: 3px 7px;
  color: var(--color-muted);
}

.trace-warning {
  color: #dc8b35;
}

.trace-section-title {
  margin-bottom: 8px;
  color: var(--color-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .06em;
  text-transform: uppercase;
}

.trace-list-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 8px;
  color: var(--color-label);
  font-size: 10px;
}

.trace-copy-button,
.trace-secondary-button {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 6px 10px;
  color: var(--color-muted);
  font-size: 11px;
  transition: color .2s ease, border-color .2s ease;
}

.trace-fade-enter-active,
.trace-fade-leave-active {
  transition: opacity .2s ease;
}

.trace-fade-enter-from,
.trace-fade-leave-to {
  opacity: 0;
}
</style>
