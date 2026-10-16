import { createRouter, createWebHistory } from 'vue-router'
import { auth } from './store'

const routes = [
  { path: '/login', component: () => import('./views/LoginView.vue'), meta: { public: true, bare: true } },
  { path: '/', component: () => import('./views/DashboardView.vue') },
  { path: '/issue', component: () => import('./views/IssueView.vue') },
  { path: '/return', component: () => import('./views/ReturnView.vue') },
  { path: '/pay', component: () => import('./views/PayView.vue') },
  { path: '/search', component: () => import('./views/SearchView.vue') },
  { path: '/members', component: () => import('./views/MembersView.vue') },
  { path: '/members/new', component: () => import('./views/MemberFormView.vue') },
  { path: '/members/:id', component: () => import('./views/MemberDetailView.vue') },
  { path: '/members/:id/edit', component: () => import('./views/MemberFormView.vue') },
  { path: '/books', component: () => import('./views/BooksView.vue') },
  { path: '/books/new', component: () => import('./views/BookFormView.vue') },
  { path: '/books/:id', component: () => import('./views/BookDetailView.vue') },
  { path: '/books/:id/edit', component: () => import('./views/BookFormView.vue') },
  { path: '/payments', component: () => import('./views/PaymentsView.vue') },
  { path: '/reports', component: () => import('./views/ReportsView.vue') },
  { path: '/holidays', component: () => import('./views/HolidaysView.vue') },
  { path: '/settings', component: () => import('./views/SettingsView.vue'), meta: { admin: true } },
  { path: '/print/receipt/:id', component: () => import('./views/PrintReceipt.vue'), meta: { bare: true } },
  { path: '/print/member-card/:id', component: () => import('./views/PrintMemberCard.vue'), meta: { bare: true } },
  { path: '/print/member-cards', component: () => import('./views/PrintMemberCard.vue'), meta: { bare: true } },
  { path: '/print/book-labels', component: () => import('./views/PrintBookLabels.vue'), meta: { bare: true } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  if (!to.meta.public && !auth.token) return '/login'
  if (to.meta.admin && auth.user?.role !== 'admin') return '/' // staff cannot open Settings
})

export default router
