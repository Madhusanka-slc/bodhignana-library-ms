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
        <router-link v-for="item in menu" :key="item.to" :to="item.to"
          class="nav-item" :class="{ active: isActive(item.to) }">
          <component :is="item.icon" :size="18" /> {{ item.label }}
        </router-link>
      </nav>

      <div class="sidebar-foot">
        <div class="who">
          <UserCircle :size="18" />
          <span>{{ auth.user?.full_name || auth.user?.username }}</span>
        </div>
        <button class="nav-item logout" @click="doLogout"><LogOut :size="18" /> Sign out</button>
      </div>
    </aside>

    <main class="content">
      <router-view :key="$route.fullPath" />
    </main>
  </div>

  <div class="toasts">
    <div v-for="t in toasts" :key="t.id" class="toast" :class="t.type">{{ t.message }}</div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BookOpen, LayoutDashboard, ArrowUpRight, ArrowDownLeft, Search, Users, Library,
  Wallet, BarChart3, CalendarDays, Settings, LogOut, UserCircle,
} from 'lucide-vue-next'
import { auth, appSettings, loadSettings, logout, toasts } from './store'

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
  { to: '/settings', label: 'Settings', icon: Settings },
]

function isActive(to) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}

function doLogout() {
  logout()
  router.push('/login')
}

onMounted(() => {
  if (auth.token) loadSettings()
})
</script>
