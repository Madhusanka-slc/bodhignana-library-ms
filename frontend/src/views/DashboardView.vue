<template>
  <div class="list-page home">
    <div class="page-head">
      <div>
        <h1>Good {{ greeting }}, {{ auth.user?.full_name || auth.user?.username }}</h1>
        <p class="sub">{{ todayText }}</p>
      </div>
    </div>

    <!-- 1. The counter work: each button shows what happened today -->
    <div class="home-actions">
      <router-link v-for="a in actions" :key="a.to" :to="a.to" class="action-card"
                   :title="a.desc">
        <span class="action-icon"><component :is="a.icon" :size="28" /></span>
        <span class="action-text"><strong>{{ a.label }}</strong><small>{{ a.desc }}</small></span>
      </router-link>
    </div>

    <template v-if="s">
      <!-- 2. Where the books are -->
      <h2 class="section-title">Books &amp; members</h2>
      <div class="status-row">
        <div class="status-box tint-1"><CircleCheck :size="20" /><span class="v">{{ n(s.books_available) }}</span><span class="l">In the library</span></div>
        <div class="status-box tint-2"><Clock :size="20" /><span class="v">{{ n(s.books_issued) }}</span><span class="l">With members</span></div>
        <router-link to="/reports?r=overdue" class="status-box tint-3 link" title="Open the overdue books report">
          <CircleAlert :size="20" />
          <span class="v">{{ n(s.overdue) }}</span><span class="l">Overdue</span>
        </router-link>
        <div class="status-box tint-4"><Users :size="20" /><span class="v">{{ n(s.members_active) }}</span><span class="l">Active members</span></div>
      </div>
    </template>

    <!-- 3. Today: the day's totals, then everything done at the counter, newest first -->
    <div class="card activity">
      <div class="card-head">
        <h2>Today's activity <span class="badge blue">{{ n(activity.length) }}</span></h2>
        <div class="activity-filter">
          <button v-for="f in FILTERS.filter((x) => x.key === 'all' || countOf(x.key))" :key="f.key" class="chip"
                  :class="{ on: show === f.key }" @click="show = f.key">
            {{ f.label }} <span v-if="f.key !== 'all'" class="chip-n">{{ countOf(f.key) }}</span>
          </button>
        </div>
      </div>
      <div v-if="s" class="today-strip">
        <div class="today-stat"><ArrowUpRight :size="16" /><b>{{ n(s.issued_today) }}</b> Books issued</div>
        <div class="today-stat"><ArrowDownLeft :size="16" /><b>{{ n(s.returned_today) }}</b> Books returned</div>
        <router-link to="/payments" class="today-stat link" title="Open payments">
          <Wallet :size="16" /><b>{{ money(s.collected_today) }}</b> Fines &amp; fees collected
        </router-link>
      </div>
      <div v-if="!shown.length" class="activity-empty muted">
        {{ activity.length ? 'Nothing of this kind today.' : 'Nothing yet today. Issues, returns, new members, new books and payments appear here as they happen.' }}
      </div>
      <div v-else class="activity-list">
        <div v-for="(e, i) in shown" :key="i" class="act" :class="'k-' + e.kind" @click="openEvent(e)">
          <span class="act-time">{{ timeOf(e.time) }}</span>
          <span class="act-icon"><component :is="KIND[e.kind].icon" :size="17" /></span>
          <div class="act-text">
            <strong>{{ KIND[e.kind].verb }} <span v-if="e.acc_no || e.member_no || e.receipt_no" class="code-tag">{{ mainCode(e) }}</span> {{ mainText(e) }}</strong>
            <span class="muted small">{{ subText(e) }}</span>
          </div>
          <span v-if="tagOf(e)" class="act-tag">{{ tagOf(e) }}</span>
          <span v-if="e.by" class="act-by" :title="`Done by ${e.by}`"><UserRound :size="13" /> {{ e.by }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowDownLeft, ArrowUpRight, BookPlus, CircleAlert, CircleCheck, Clock, Search, UserPlus, UserRound, Users, Wallet,
} from 'lucide-vue-next'
import { api } from '../api'
import { auth } from '../store'
import { fmtDate, money } from '../utils'
import { PAYMENT_TYPES, typeLabel } from '../constants'

const s = ref(null)
const h = new Date().getHours()
const greeting = h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening'
const todayText = new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
const n = (v) => Number(v || 0).toLocaleString('en-US')

// The five counter buttons.
const actions = [
  { to: '/issue', label: 'Issue book', desc: 'Member takes books out', icon: ArrowUpRight },
  { to: '/return', label: 'Return book', desc: 'Member brings books back', icon: ArrowDownLeft },
  { to: '/search', label: 'Search', desc: 'Find a book or member', icon: Search },
  { to: '/members/new', label: 'New member', desc: 'Register a reader', icon: UserPlus },
  { to: '/books/new', label: 'New book', desc: 'Add a book to the library', icon: BookPlus },
]

// ---------- Today's activity ----------
const router = useRouter()
const activity = ref([])
const show = ref('all')
const KIND = {
  issue: { verb: 'Issued', icon: ArrowUpRight },
  return: { verb: 'Returned', icon: ArrowDownLeft },
  member: { verb: 'New member', icon: UserPlus },
  book: { verb: 'New book', icon: BookPlus },
  payment: { verb: 'Payment', icon: Wallet },
}
const FILTERS = [
  { key: 'all', label: 'All' }, { key: 'issue', label: 'Issued' }, { key: 'return', label: 'Returned' },
  { key: 'member', label: 'Members' }, { key: 'book', label: 'Books' }, { key: 'payment', label: 'Payments' },
]
const shown = computed(() => (show.value === 'all' ? activity.value : activity.value.filter((e) => e.kind === show.value)))
const countOf = (k) => activity.value.filter((e) => e.kind === k).length
const timeOf = (t) => (t ? new Date(t).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : '--')
const mainCode = (e) => (e.kind === 'member' ? e.member_no : e.kind === 'payment' ? e.receipt_no : e.acc_no)
const mainText = (e) => (e.kind === 'member' ? e.member_name : e.kind === 'payment' ? money(e.amount) : e.title)

function subText(e) {
  if (e.kind === 'issue') return `to ${e.member_name} (${e.member_no}) · due ${fmtDate(e.due_date)}`
  if (e.kind === 'return') {
    const paid = e.receipt_no ? ` · fine paid, receipt ${e.receipt_no}` : ''
    return `from ${e.member_name} (${e.member_no})${paid}`
  }
  if (e.kind === 'member') return typeLabel(e.membership_type)
  if (e.kind === 'book') return e.section || 'No section'
  return `${PAYMENT_TYPES[e.payment_type] || e.payment_type} · ${e.member_name} (${e.member_no})`
}

function tagOf(e) {
  if (e.kind !== 'return') return ''
  if (e.damaged) return 'Damaged'
  if (e.late_days) return `${e.late_days} day(s) late · ${money(e.fine)}`
  return 'On time'
}

function openEvent(e) {
  if (e.kind === 'book') router.push('/books/' + e.book_id)
  else if (e.member_id) router.push('/members/' + e.member_id)
}

onMounted(async () => {
  const [stats, act] = await Promise.all([api.get('/reports/dashboard'), api.get('/reports/today-activity')])
  s.value = stats
  activity.value = act.items
})
</script>
