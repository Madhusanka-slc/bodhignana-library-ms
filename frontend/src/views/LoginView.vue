<template>
  <div class="login-page">
    <form class="login-card" @submit.prevent="login">
      <div class="login-logo"><BookOpen :size="30" /></div>
      <h1>Library system</h1>
      <p class="muted">Sign in to continue</p>
      <label for="u">Username</label>
      <input id="u" v-model="username" autocomplete="username" autofocus />
      <label for="p">Password</label>
      <input id="p" v-model="password" type="password" autocomplete="current-password" />
      <p v-if="error" class="alert red">{{ error }}</p>
      <button class="btn primary big full" :disabled="busy">{{ busy ? 'Signing in…' : 'Sign in' }}</button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { BookOpen } from 'lucide-vue-next'
import { api } from '../api'
import { loadSettings, setAuth } from '../store'

const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function login() {
  error.value = ''
  busy.value = true
  try {
    const r = await api.post('/auth/login', { username: username.value, password: password.value })
    setAuth(r.token, r.user)
    await loadSettings()
    router.push('/')
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>
