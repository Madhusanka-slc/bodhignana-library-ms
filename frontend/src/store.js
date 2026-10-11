import { reactive } from 'vue'
import { api } from './api'

export const auth = reactive({
  token: localStorage.getItem('token') || '',
  user: JSON.parse(localStorage.getItem('user') || 'null'),
})

export function setAuth(token, user) {
  auth.token = token
  auth.user = user
  localStorage.setItem('token', token)
  localStorage.setItem('user', JSON.stringify(user))
}

export function logout() {
  auth.token = ''
  auth.user = null
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

export const isAdmin = () => auth.user?.role === 'admin'

// Library settings (name, fine rules ...)
export const appSettings = reactive({ library_name: 'Library' })
export async function loadSettings() {
  try {
    Object.assign(appSettings, await api.get('/settings'))
  } catch {
    /* not logged in yet */
  }
}

// Small pop-up messages
export const toasts = reactive([])
export function toast(message, type = 'success') {
  const id = Date.now() + Math.random()
  toasts.push({ id, message, type })
  setTimeout(() => {
    const i = toasts.findIndex((t) => t.id === id)
    if (i >= 0) toasts.splice(i, 1)
  }, type === 'error' ? 6000 : 3500)
}

// What is being shown in the print preview popup ('' = closed). See components/PrintPreview.vue
export const printJob = reactive({ path: '', title: '' })
