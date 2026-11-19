<!-- ========================================
File: src/views/profile.vue
Description: Logged in user profile page
======================================== -->

<template>
  <div class="pulsar-shell min-h-screen px-4 pt-24">
    <div class="mx-auto w-full max-w-xl pulsar-surface overflow-hidden">
      <div class="border-b border-border bg-panel-alt px-6 py-5">
        <div class="pulsar-section-label">Account</div>
        <h2 class="mt-1 text-xl font-bold text-label">User Profile</h2>
      </div>
      <div class="p-6">
        <div v-if="user" class="flex items-center gap-4">
          <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-white font-bold" style="background:var(--color-primary)">{{ user.email?.charAt(0)?.toUpperCase() || '?' }}</div>
          <div><div class="text-xs text-muted">Email</div><div class="mt-0.5 text-sm font-semibold text-label">{{ user.email }}</div></div>
        </div>
        <div v-else class="text-sm text-muted">در حال دریافت اطلاعات...</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from '@/utils/axiosInstance'
import { useRouter } from 'vue-router'

const user = ref(null) 
const router = useRouter()
 
onMounted(async () => {
  try {
    const token = localStorage.getItem("token")
    const response = await get(axios.defaults.baseURL + 'auth/me', {
      headers: {        
        Authorization: `Bearer ${token}`,
      }      
    })
    user.value = response.data
  } catch (error) {
    console.error("Error getting profile:", error)
    router.push("/login")
  }
})
</script>

<style scoped>

</style>
