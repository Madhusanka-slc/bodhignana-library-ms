<template>
  <router-view v-if="$route.meta.bare" />
  <div v-else class="layout">
    <aside class="sidebar no-print">
      <div class="brand">
        <div class="brand-mark"><BookOpen :size="22" /></div>
        <div class="brand-text">
          <strong>{{ appSettings.library_name }}</strong>
          <span>Library system</span>
        </div>
      </div>

      <nav>
        <router-link v-for="item in mainMenu" :key="item.to" :to="item.to"
          class="nav-item nav-main" :class="{ active: isActive(item.to) }">
          <component :is="item.icon" :size="20" /> {{ item.label }}
        </router-link>
        <div class="nav-sep"></div>
        <router-link v-for="item in menu.filter((x) => !x.admin || isAdmin())" :key="item.to" :to="item.to"
          class="nav-item" :class="{ active: isActive(item.to) }">
          <component :is="item.icon" :size="18" /> {{ item.label }}
        </router-link>
      </nav>

      <div class="sidebar-foot">
        <button class="who" title="My account" @click="openAccount">
          <UserCircle :size="18" />
          <span>{{ auth.user?.full_name || auth.user?.username }}<small>{{ isAdmin() ? 'Administrator' : 'Staff' }} · My account</small></span>
        </button>
        <button class="nav-item logout" @click="doLogout"><LogOut :size="18" /> Sign out</button>
      </div>
    </aside>

    <main class="content">
      <router-view :key="$route.fullPath" />
    </main>
  </div>

  <!-- My account: every user can change their own password here -->
  <Modal v-if="account" title="My account" @close="account = null">
    <dl class="info">
      <dt>Name</dt><dd>{{ auth.user?.full_name || '-' }}</dd>
      <dt>Username</dt><dd>{{ auth.user?.username }}</dd>
      <dt>Role</dt><dd>{{ isAdmin() ? 'Administrator' : 'Staff' }}</dd>
    </dl>
    <h3 class="mt">Change my password</h3>
    <div class="form-grid">
      <div class="field"><label>Current password</label><input v-model="account.old_password" type="password" autocomplete="current-password" /></div>
      <div class="field"><label>New password</label><input v-model="account.new_password" type="password" autocomplete="new-password" /></div>
    </div>
    <p class="help">At least 6 characters.</p>
    <template #footer>
      <button class="btn" @click="account = null">Close</button>
      <button class="btn primary" :disabled="!account.old_password || !account.new_password" @click="changePassword">Change password</button>
    </template>
  </Modal>

  <div class="toasts">
    <div v-for="t in toasts" :key="t.id" class="toast" :class="t.type">{{ t.message }}</div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BookOpen, LayoutDashboard, ArrowUpRight, ArrowDownLeft, Search, Users, Library,
  Wallet, BarChart3, CalendarDays, Settings, LogOut, UserCircle,
} from 'lucide-vue-next'
import Modal from './components/Modal.vue'
import { api } from './api'
import { auth, appSettings, isAdmin, loadSettings, logout, toast, toasts } from './store'

const route = useRoute()
const router = useRouter()

const mainMenu = [
  { to: '/issue', label: 'Issue book', icon: ArrowUpRight },
  { to: '/return', label: 'Return book', icon: ArrowDownLeft },
  { to: '/search', label: 'Search', icon: Search },
]
const menu = [
  { to: '/', label: 'Home', icon: LayoutDashboard },
  { to: '/members', label: 'Members', icon: Users },
  { to: '/books', label: 'Books', icon: Library },
  { to: '/payments', label: 'Payments', icon: Wallet },
  { to: '/reports', label: 'Reports', icon: BarChart3 },
  { to: '/holidays', label: 'Holidays', icon: CalendarDays },
  { to: '/settings', label: 'Settings', icon: Settings, admin: true },
]

function isActive(to) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}

const account = ref(null)
const openAccount = () => { account.value = { old_password: '', new_password: '' } }
async function changePassword() {
  try {
    await api.post('/auth/change-password', account.value)
    account.value = null
    toast('Password changed')
  } catch (e) {
    toast(e.message, 'error')
  }
}

function doLogout() {
  logout()
  router.push('/login')
}

onMounted(() => {
  if (auth.token) loadSettings()
})
</script>
