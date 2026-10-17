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
        <div class="status-box tint-4" :title="`${n(s.books_total)} books (copies), ${n(s.titles_total)} different books`"><Library :size="20" />
          <span class="v">{{ n(s.titles_total) }}</span><span class="l">Different books · {{ n(s.books_total) }} copies</span></div>
      </div>
    </template>

    <!-- 3. Today: the day's totals, then everything done at the counter, newest first -->
    <div class="card activity">
      <div class="card-head">
        <h2>Today's activity <span class="badge blue">{{ n(activity.length) }}</span></h2>
        <div class="activity-filter">
          <button v-for="f in FILTERS" :key="f.key" class="chip"
                  :class="{ on: show === f.key }" @click="show = f.key">
            {{ f.label }} <span v-if="f.key !== 'all'" class="chip-n">{{ countOf(f.key) }}</span>
          </button>
        </div>
      </div>
      <div v-if="s" class="today-strip">
        <div class="today-stat"><ArrowUpRight :size="16" /><b>{{ n(s.issued_today) }}</b> Books issued</div>
        <div class="today-stat"><ArrowDownLeft :size="16" /><b>{{ n(s.returned_today) }}</b> Books returned</div>
        <!-- added today (counted from today's activity below); click to show only those -->
        <button type="button" class="today-stat link" title="Show the members added today" @click="show = 'member'"><UserPlus :size="16" /><b>{{ n(countOf('member')) }}</b> New members</button>
        <button type="button" class="today-stat link" title="Show the books added today" @click="show = 'book'"><BookPlus :size="16" /><b>{{ n(countOf('book')) }}</b> New books</button>
        <router-link to="/payments" class="today-stat link" title="Open payments">
          <Wallet :size="16" /><b>{{ money(s.collected_today) }}</b> Collected
        </router-link>
      </div>
      <div v-if="!shown.length" class="activity-empty muted">
        {{ activity.length ? 'Nothing of this kind today.' : 'Nothing yet today. Issues, returns, new members, new books and payments appear here as they happen.' }}
      </div>
      <div v-else class="activity-list">
        <div v-for="(e, i) in shown" :key="i" class="act" :class="'k-' + e.kind" title="Click to see the details" @click="openEvent(e)">
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

    <!-- Details of one line of today's activity -->
    <Modal v-if="sel" :title="KIND[sel.kind].verb + (sel.kind === 'payment' ? ' ' + sel.receipt_no : sel.acc_no ? ' · ' + sel.acc_no : sel.member_no ? ' · ' + sel.member_no : '')" wide @close="sel = null">
      <div class="rs-tiles">
        <div v-for="t in detailTiles" :key="t.label" class="rs-tile"><small>{{ t.label }}</small><strong :title="t.value">{{ t.value || '-' }}</strong><small v-if="t.sub">{{ t.sub }}</small></div>
      </div>

      <!-- issue / return: the borrowing record -->
      <table v-if="sel.kind === 'issue' || sel.kind === 'return'" class="table report-table rs-lines">
        <tbody>
          <tr><td style="width: 34%">Book</td><td><span class="code-tag">{{ sel.acc_no }}</span> {{ sel.title }}<span v-if="sel.author" class="muted"> · {{ sel.author }}</span></td></tr>
          <tr><td>Member</td><td><span class="code-tag">{{ sel.member_no }}</span> {{ sel.member_name }}</td></tr>
          <tr v-if="sel.ref"><td>Reference</td><td><span class="ref-tag">{{ sel.ref }}</span></td></tr>
          <tr><td>Borrowed / due</td><td>{{ fmtDate(sel.issue_date) }} · due {{ fmtDate(sel.loan_due) }}</td></tr>
          <tr v-if="sel.kind === 'return'"><td>Returned</td><td>{{ fmtDate(sel.return_date) }} · {{ sel.lost ? 'missing' : sel.damaged ? 'damaged' : sel.late_days ? sel.late_days + ' day(s) late' : 'on time, good condition' }}</td></tr>
          <tr v-if="sel.issue_fee"><td>Issue fee</td><td>{{ money(sel.issue_fee) }}</td></tr>
          <tr v-if="sel.late_fine || sel.damage_fine || sel.lost_fine"><td>Charges</td><td>
            <template v-if="sel.late_fine">Late {{ money(sel.late_fine) }} </template><template v-if="sel.damage_fine">Damaged {{ money(sel.damage_fine) }} </template><template v-if="sel.lost_fine">Missing {{ money(sel.lost_fine) }}</template></td></tr>
          <tr><td>Still to pay</td><td><strong :class="{ 'text-red': sel.balance > 0 }">{{ sel.balance > 0 ? money(sel.balance) : 'Nothing' }}</strong><span v-if="sel.receipt_no" class="muted"> · paid on receipt {{ sel.receipt_no }}</span></td></tr>
        </tbody>
      </table>

      <!-- payment: every line of the receipt -->
      <template v-else-if="sel.kind === 'payment'">
        <p v-if="!receipt" class="muted">Loading the receipt…</p>
        <ReceiptLines v-else :receipt="receipt" />
      </template>

      <template #footer>
        <router-link v-if="sel.member_id && !receipt?.isGroup" :to="'/members/' + sel.member_id" class="btn"><UserRound :size="16" /> Member profile</router-link>
        <router-link v-if="sel.book_id" :to="'/books/' + sel.book_id" class="btn"><BookOpen :size="16" /> Book page</router-link>
        <button class="btn" @click="sel = null">Close</button>
        <button v-if="sel.kind === 'payment' && receipt" class="btn primary" @click="openPrint('/print/receipt/' + receipt.id)"><Printer :size="16" /> Print receipt</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowDownLeft, ArrowUpRight, BookOpen, BookPlus, CircleAlert, CircleCheck, Clock, Library, Printer, Search, UserPlus, UserRound, Users, Wallet,
} from 'lucide-vue-next'
import { api } from '../api'
import { auth } from '../store'
import { fmtDate, money, openPrint } from '../utils'
import Modal from '../components/Modal.vue'
import ReceiptLines from '../components/ReceiptLines.vue'
import { toReceipt } from '../receipts'
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
// every kind is always shown (with 0 when nothing of it happened today)
const FILTERS = [
  { key: 'all', label: 'All' }, { key: 'issue', label: 'Issued' }, { key: 'return', label: 'Returned' },
  { key: 'member', label: 'New members' }, { key: 'book', label: 'New books' }, { key: 'payment', label: 'Payments' },
]
const shown = computed(() => (show.value === 'all' ? activity.value : activity.value.filter((e) => e.kind === show.value)))
const countOf = (k) => activity.value.filter((e) => e.kind === k).length
const timeOf = (t) => (t ? new Date(t).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : '--')
const mainCode = (e) => (e.kind === 'member' ? e.member_no : e.kind === 'payment' ? e.receipt_no : e.acc_no)
const mainText = (e) => (e.kind === 'member' ? e.member_name : e.kind === 'payment' ? money(e.amount) : e.title)

function subText(e) {
  if (e.kind === 'issue') return `to ${e.member_name} (${e.member_no}) · due ${fmtDate(e.due_date)}`
  if (e.kind === 'return') {
    // only when the return itself had a charge (late, damaged, missing) and it was paid
    const charged = e.late_fine || e.damage_fine || e.lost_fine
    const paid = charged ? (e.balance > 0 ? ' · charge not paid yet' : e.receipt_no ? ` · charge paid, receipt ${e.receipt_no}` : '') : ''
    return `from ${e.member_name} (${e.member_no})${paid}`
  }
  if (e.kind === 'member') return typeLabel(e.membership_type)
  if (e.kind === 'book') return e.section || 'No section'
  const what = (e.types || [e.payment_type]).map((t) => PAYMENT_TYPES[t] || t).join(' + ')
  const who = e.members && e.members.length > 1 ? `${e.member_name} + ${e.members.length - 1} more (group)` : `${e.member_name} (${e.member_no})`
  return `${what}${e.lines > 1 ? ` · ${e.lines} books` : ''} · ${who}`
}

function tagOf(e) {
  if (e.kind !== 'return') return ''
  if (e.damaged) return 'Damaged'
  if (e.late_days) return `${e.late_days} day(s) late · ${money(e.fine)}`
  return 'On time'
}

// A click shows the details in a popup (like Payment records); the buttons there open the member or book
const sel = ref(null)
const receipt = ref(null) // the receipt of a payment line (with a section per member on a group receipt)
async function openEvent(e) {
  sel.value = e
  receipt.value = null
  if (e.kind === 'payment' && e.receipt_no) receipt.value = toReceipt(await api.get('/payments', { receipt_no: e.receipt_no }))
}
const timeFull = (t) => (t ? new Date(t).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' }) : '-')
const detailTiles = computed(() => {
  const e = sel.value
  if (!e) return []
  const when = { label: 'When', value: timeFull(e.time) }
  const by = { label: 'Done by', value: e.by }
  if (e.kind === 'issue') return [when, { label: 'Member', value: e.member_name, sub: 'No. ' + e.member_no }, { label: 'Due back', value: fmtDate(e.loan_due) }, by]
  if (e.kind === 'return') return [when, { label: 'Member', value: e.member_name, sub: 'No. ' + e.member_no },
    { label: 'Condition', value: e.lost ? 'Missing' : e.damaged ? 'Damaged' : e.late_days ? `${e.late_days} day(s) late` : 'On time' }, by]
  if (e.kind === 'member') return [when, { label: 'Membership type', value: typeLabel(e.membership_type) },
    { label: 'Telephone', value: e.telephone }, { label: 'Expiry date', value: e.expiry_date ? fmtDate(e.expiry_date) : 'Never / not set' },
    { label: 'Address', value: e.address }, by]
  if (e.kind === 'book') return [when, { label: 'Title', value: e.title, sub: e.author }, { label: 'Section', value: e.section },
    { label: 'Call No.', value: e.call_no }, { label: 'Price', value: e.price ? money(e.price) : '' }, by]
  const r = receipt.value
  const who = r && r.isGroup
    ? { label: 'Group of members', value: `${r.members.length} members`, sub: 'No. ' + r.members.map((m) => m.member_no).join(', ') }
    : { label: 'Member', value: e.member_name, sub: 'No. ' + e.member_no }
  return [when, { label: 'Total', value: money(e.amount) }, who, by]
})

onMounted(async () => {
  const [stats, act] = await Promise.all([api.get('/reports/dashboard'), api.get('/reports/today-activity')])
  s.value = stats
  activity.value = oneLinePerReceipt(act.items)
})

// One receipt can cover several books (one payment each): show it as one line with its total
function oneLinePerReceipt(items) {
  const out = []
  const byNo = new Map()
  for (const e of items) {
    if (e.kind !== 'payment' || !e.receipt_no) { out.push(e); continue }
    const first = byNo.get(e.receipt_no)
    if (!first) {
      const copy = { ...e, amount: Number(e.amount), types: [e.payment_type], lines: 1, members: [e.member_id] }
      byNo.set(e.receipt_no, copy)
      out.push(copy)
    } else {
      first.amount += Number(e.amount)
      first.lines += 1
      if (!first.members.includes(e.member_id)) first.members.push(e.member_id)
      if (!first.types.includes(e.payment_type)) first.types.push(e.payment_type)
    }
  }
  return out
}
</script>
