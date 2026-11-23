<template>
  <div v-if="modelValue" class="fixed inset-0 z-[90] flex items-center justify-center bg-black/50 p-3" @click.self="close">
    <section class="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-border bg-panel shadow-2xl">
      <header class="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          <h2 class="text-sm font-semibold text-label">{{ labels.title }}</h2>
          <p class="mt-1 text-[10px] text-muted">{{ labels.scopeNote }}</p>
        </div>
        <button class="rounded-lg px-2 py-1 text-lg text-muted hover:bg-hover" @click="close">×</button>
      </header>

      <div class="min-h-0 flex-1 overflow-y-auto p-4">
        <div v-if="error" class="mb-3 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-700" role="alert">
          {{ error }}
        </div>

        <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)]">
          <section class="space-y-3 rounded-xl border border-border p-3">
            <h3 class="text-xs font-semibold text-label">{{ labels.grant }}</h3>

            <div class="space-y-1">
              <label class="text-[10px] text-muted">{{ labels.findUser }}</label>
              <div class="flex gap-2">
                <input v-model="userQuery" class="min-w-0 flex-1 rounded-lg border border-border bg-panel px-2.5 py-2 text-xs" :placeholder="labels.userSearch" @keyup.enter="searchUsers" />
                <button class="permission-action" :disabled="loading || userQuery.trim().length < 2" @click="searchUsers">{{ labels.search }}</button>
              </div>
              <div v-if="users.length" class="max-h-36 overflow-y-auto rounded-lg border border-border">
                <button
                  v-for="user in users"
                  :key="user.c_user_id"
                  class="flex w-full flex-col border-b border-border px-2.5 py-2 text-left last:border-0 hover:bg-hover"
                  :class="selectedUserId === user.c_user_id ? 'bg-hover' : ''"
                  @click="selectUser(user)"
                >
                  <span class="text-xs font-medium text-label">{{ user.c_user_full_name || user.c_user_email }}</span>
                  <span class="text-[10px] text-muted">{{ user.c_user_email }}</span>
                </button>
              </div>
              <div v-if="selectedUser" class="rounded-lg bg-hover px-2.5 py-2 text-[10px] text-label">
                {{ labels.selectedUser }}: {{ selectedUser.c_user_full_name || selectedUser.c_user_email }}
              </div>
            </div>

            <div class="space-y-1">
              <label class="text-[10px] text-muted">{{ labels.permission }}</label>
              <select v-model="permissionId" class="w-full rounded-lg border border-border bg-panel px-2.5 py-2 text-xs">
                <option value="">{{ labels.selectPermission }}</option>
                <option v-for="permission in manageableCatalog" :key="permission.permission_id" :value="String(permission.permission_id)">
                  {{ permission.permission_code }} · {{ permission.permission_title }}{{ permission.page_key ? ' · ' + permission.page_key : '' }}
                </option>
              </select>
              <p v-if="selectedPermission" class="text-[10px] text-muted">
                {{ labels.scope }}: {{ selectedPermission.scope_type }}{{ selectedPermission.scope_key ? ' / ' + selectedPermission.scope_key : '' }}
              </p>
            </div>

            <div class="grid grid-cols-2 gap-2">
              <div class="space-y-1">
                <label class="text-[10px] text-muted">{{ labels.startAt }}</label>
                <input v-model="validFrom" type="datetime-local" class="w-full rounded-lg border border-border bg-panel px-2 py-2 text-[10px]" />
              </div>
              <div class="space-y-1">
                <label class="text-[10px] text-muted">{{ labels.endAt }}</label>
                <input v-model="validUntil" type="datetime-local" class="w-full rounded-lg border border-border bg-panel px-2 py-2 text-[10px]" />
              </div>
            </div>

            <div class="space-y-1">
              <label class="text-[10px] text-muted">{{ labels.reason }}</label>
              <textarea v-model="grantReason" rows="2" class="w-full rounded-lg border border-border bg-panel px-2.5 py-2 text-xs" />
            </div>

            <button class="permission-action permission-primary w-full" :disabled="loading || !selectedUserId || !permissionId" @click="grantPermission">
              {{ labels.grant }}
            </button>
          </section>

          <section class="min-w-0 space-y-3 rounded-xl border border-border p-3">
            <div class="flex items-center justify-between">
              <h3 class="text-xs font-semibold text-label">{{ labels.history }}</h3>
              <span v-if="selectedUser" class="truncate text-[10px] text-muted">{{ selectedUser.c_user_email }}</span>
            </div>

            <div v-if="!selectedUser" class="rounded-lg border border-dashed border-border px-3 py-8 text-center text-xs text-muted">
              {{ labels.selectUserFirst }}
            </div>

            <div v-else-if="history.length === 0" class="rounded-lg border border-dashed border-border px-3 py-8 text-center text-xs text-muted">
              {{ labels.noGrants }}
            </div>

            <div v-else class="space-y-2">
              <article v-for="grant in history" :key="grant.permit_id" class="rounded-lg border border-border p-2.5">
                <div class="flex items-start justify-between gap-2">
                  <div class="min-w-0">
                    <div class="break-all text-xs font-semibold text-label">{{ grant.permission_code }}</div>
                    <div class="mt-0.5 text-[10px] text-muted">{{ grant.permission_title }} · {{ grant.page_key || grant.scope_type }}</div>
                  </div>
                  <span class="shrink-0 rounded-full px-2 py-0.5 text-[10px]" :class="grant.is_effective ? 'bg-emerald-100 text-emerald-700' : 'bg-hover text-muted'">
                    {{ grant.is_effective ? labels.active : labels.inactive }}
                  </span>
                </div>
                <div class="mt-2 grid grid-cols-2 gap-2 text-[10px] text-muted">
                  <span>{{ labels.startAt }}: {{ formatDate(grant.valid_from) }}</span>
                  <span>{{ labels.endAt }}: {{ grant.valid_until ? formatDate(grant.valid_until) : '—' }}</span>
                  <span>{{ labels.grantedBy }}: {{ grant.granted_by }}</span>
                  <span>{{ labels.grantedAt }}: {{ formatDate(grant.granted_at) }}</span>
                </div>
                <div v-if="grant.grant_reason" class="mt-2 text-[10px] text-muted">{{ grant.grant_reason }}</div>
                <div v-if="grant.is_active" class="mt-2 flex justify-end">
                  <button class="text-[10px] font-semibold text-red-500 hover:underline" :disabled="loading" @click="revokeGrant(grant.permit_id)">
                    {{ labels.revoke }}
                  </button>
                </div>
              </article>
            </div>
          </section>
        </div>
      </div>

      <footer class="flex items-center justify-between border-t border-border px-4 py-2.5">
        <span class="text-[10px] text-muted">{{ loading ? labels.loading : labels.auditNote }}</span>
        <button class="permission-action" @click="close">{{ labels.close }}</button>
      </footer>
    </section>
  </div>
</template>

<script setup>
import {
  computed,
  ref,
  watch
} from 'vue'

import axios from '@/utils/axiosInstance'
import { language } from '@/stores/uiStore'
import { useTranslation } from '@/composables/useTranslation'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])
const { translate } = useTranslation()

const loading = ref(false)
const error = ref('')
const labels = ref({})
const userQuery = ref('')
const users = ref([])
const selectedUser = ref(null)
const selectedUserId = ref('')
const permissionId = ref('')
const catalog = ref([])
const adminGrants = ref([])
const history = ref([])
const validFrom = ref(toLocalInput(new Date()))
const validUntil = ref('')
const grantReason = ref('')

const translationKeys = {
  title: 'security.permissionManager',
  scopeNote: 'security.scopeNote',
  grant: 'security.grant',
  findUser: 'security.findUser',
  userSearch: 'security.userSearch',
  search: 'security.search',
  selectedUser: 'security.selectedUser',
  permission: 'security.permission',
  selectPermission: 'security.selectPermission',
  scope: 'security.scope',
  startAt: 'security.startAt',
  endAt: 'security.endAt',
  reason: 'security.reason',
  history: 'security.history',
  selectUserFirst: 'security.selectUserFirst',
  noGrants: 'security.noGrants',
  active: 'security.active',
  inactive: 'security.inactive',
  grantedBy: 'security.grantedBy',
  grantedAt: 'security.grantedAt',
  revoke: 'security.revoke',
  loading: 'security.loading',
  auditNote: 'security.auditNote',
  close: 'security.close',
  errorData: 'security.error.data',
  errorSearch: 'security.error.search',
  errorHistory: 'security.error.history',
  errorGrant: 'security.error.grant',
  errorRevoke: 'security.error.revoke',
  errorAdmin: 'security.error.admin'
}

async function loadLabels() {
  const result = {}
  for (const [name, key] of Object.entries(translationKeys)) {
    result[name] = await translate(key, language.value)
  }
  labels.value = result
}

function toLocalInput(value) {
  const date = new Date(value.getTime() - value.getTimezoneOffset() * 60000)
  return date.toISOString().slice(0, 16)
}

function toIso(value) {
  return value ? new Date(value).toISOString() : null
}

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
}

const manageableCatalog = computed(() => {
  return catalog.value.filter(permission =>
    adminGrants.value.some(admin => {
      if (admin.scope_type === 'SYSTEM') return true
      if (
        admin.scope_type === 'SUBSYSTEM' &&
        (
          permission.subsystem_key === admin.scope_key ||
          (permission.scope_type === 'SUBSYSTEM' && permission.scope_key === admin.scope_key)
        )
      ) return true
      if (
        admin.scope_type === 'PAGE' &&
        permission.page_key &&
        permission.page_key === admin.page_key
      ) return true
      return false
    })
  )
})

const selectedPermission = computed(() =>
  manageableCatalog.value.find(item =>
    String(item.permission_id) === String(permissionId.value)
  ) || null
)

async function loadManagerData() {
  loading.value = true
  error.value = ''

  try {
    const [grantResponse, catalogResponse] = await Promise.all([
      axios.get('/permissions/me'),
      axios.get('/permissions/catalog')
    ])

    adminGrants.value = (grantResponse.data || []).filter(item =>
      item.permission_code === 'SECURITY.PERMISSION.GRANT' &&
      item.is_effective === true
    )
    catalog.value = catalogResponse.data || []

    if (!adminGrants.value.length) {
      throw new Error(labels.value.errorAdmin)
    }
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || labels.value.errorData
  } finally {
    loading.value = false
  }
}

async function searchUsers() {
  if (userQuery.value.trim().length < 2) return
  loading.value = true
  error.value = ''

  try {
    const response = await axios.get('/permissions/users/lookup', {
      params: { query: userQuery.value.trim() }
    })
    users.value = response.data || []
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || labels.value.errorSearch
  } finally {
    loading.value = false
  }
}

async function selectUser(user) {
  selectedUser.value = user
  selectedUserId.value = user.c_user_id
  await loadHistory()
}

async function loadHistory() {
  if (!selectedUserId.value) {
    history.value = []
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await axios.get('/permissions/users/' + selectedUserId.value + '/grants')
    history.value = response.data || []
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || labels.value.errorHistory
  } finally {
    loading.value = false
  }
}

async function grantPermission() {
  if (!selectedUserId.value || !permissionId.value) return
  loading.value = true
  error.value = ''

  try {
    await axios.post('/permissions/grants', {
      c_user_id: selectedUserId.value,
      permission_id: Number(permissionId.value),
      valid_from: toIso(validFrom.value),
      valid_until: toIso(validUntil.value),
      grant_reason: grantReason.value || null
    })

    grantReason.value = ''
    validUntil.value = ''
    await loadHistory()
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || labels.value.errorGrant
  } finally {
    loading.value = false
  }
}

async function revokeGrant(permitId) {
  loading.value = true
  error.value = ''

  try {
    await axios.delete('/permissions/grants/' + permitId)
    await loadHistory()
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || labels.value.errorRevoke
  } finally {
    loading.value = false
  }
}

function close() {
  emit('update:modelValue', false)
}

watch(
  () => props.modelValue,
  async open => {
    if (open) {
      await loadLabels()
      await loadManagerData()
    }
  }
)

watch(language, loadLabels)
</script>

<style scoped>
.permission-action {
  border: 1px solid var(--pulsar-level-border);
  border-radius: 0.55rem;
  padding: 0.48rem 0.7rem;
  color: var(--pulsar-level-text);
  font-size: 0.68rem;
  font-weight: 600;
  background: var(--pulsar-level-surface);
}
.permission-action:hover {
  background: var(--pulsar-level-hover);
}
.permission-action:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}
.permission-primary {
  border-color: var(--pulsar-level-accent);
  color: var(--pulsar-level-accent);
}
</style>
