<template>  <div class="pay-records">
    <div class="page-head">
      <h1>Payment records</h1>
      <router-link to="/pay" class="btn primary"><Plus :size="18" /> New payment</router-link>
    </div>

    <!-- Same look as "Today's activity" on Home: one line per receipt, newest first -->
    <div class="card activity">
      <div class="card-head">
        <h2>Receipts <span class="badge blue">{{ receipts.length }}</span></h2>
        <div class="pr-dates">
          <DateInput v-model="from" aria-label="From" @change="load" />
          <span class="muted">to</span>
          <DateInput v-model="to" aria-label="To" @change="load" />
        </div>
      </div>

      <!-- What was collected in these dates -->
      <div class="today-strip">
        <div class="today-stat"><Wallet :size="16" /><b>{{ money(total) }}</b> Collected</div>
        <div class="today-stat"><ReceiptText :size="16" /><b>{{ receipts.length }}</b> Receipts</div>
        <div class="today-stat"><BookOpen :size="16" /><b>{{ money(feesTotal) }}</b> Issue fees</div>
        <div class="today-stat"><CircleAlert :size="16" /><b>{{ money(finesTotal) }}</b> Fines &amp; charges</div>
      </div>

      <div class="activity-filter pr-filter">
        <button class="chip" :class="{ on: !show }" @click="show = ''">All</button>
        <button v-if="groupCount" class="chip" :class="{ on: show === 'group' }" @click="show = 'group'">
          <Users :size="14" /> Group receipts <span class="chip-n">{{ groupCount }}</span>
        </button>
        <button v-for="t in typesHere" :key="t" class="chip" :class="{ on: show === t }" @click="show = t">
          {{ PAYMENT_TYPES[t] || t }} <span class="chip-n">{{ countOf(t) }}</span>
        </button>
      </div>

      <div v-if="!shown.length" class="activity-empty muted">{{ receipts.length ? 'No receipts of this kind in these dates.' : 'No payments in these dates.' }}</div>
      <div v-else class="activity-list">
        <div v-for="r in shown" :key="r.receipt_no" class="act" :class="'k-' + r.kind" title="Click to see the details" @click="sel = r">
          <span class="act-time pr-when" :title="fullDate(r.paid_at)"><b>{{ timeOf(r.paid_at) }}</b><small>{{ dayOf(r.paid_at) }}</small></span>
          <span class="act-icon"><component :is="KIND[r.kind].icon" :size="17" /></span>
          <!-- Short, like Home: everything else is in the details popup (click the line) -->
          <div class="act-text">
            <strong>Payment <span class="code-tag">{{ r.receipt_no }}</span> {{ money(r.total) }} · {{ whoPaid(r) }}
              <span v-if="r.isGroup" class="group-mark" :title="r.members.map((m) => m.member_name).join(', ')"><Users :size="13" /> {{ r.members.length }} members</span></strong>
            <span class="muted small">{{ r.short }}</span>
          </div>
          <span class="act-tag">{{ r.label }}</span>
          <span v-if="r.received_by" class="act-by" :title="`Received by ${r.received_by}`"><UserRound :size="13" /> {{ r.received_by }}</span>
          <button class="icon-btn" title="Print receipt" @click.stop="openPrint('/print/receipt/' + r.id)"><Printer :size="17" /></button>
        </div>
      </div>
    </div>

    <!-- Details of one receipt (the printed receipt itself opens only from the printer icon) -->
    <Modal v-if="sel" :title="'Receipt ' + sel.receipt_no" wide @close="sel = null">
      <div class="rs-tiles">
        <div class="rs-tile"><small>Total</small><strong>{{ money(sel.total) }}</strong></div>
        <div class="rs-tile"><small>Date and time</small><strong>{{ fullDate(sel.paid_at) }}</strong></div>
        <div v-if="sel.isGroup" class="rs-tile"><small>Group of members</small><strong :title="sel.members.map((m) => m.member_name).join(', ')">{{ sel.members.length }} members</strong>
          <small>No. {{ sel.members.map((m) => m.member_no).join(', ') }}</small></div>
        <div v-else class="rs-tile"><small>Member</small><strong :title="sel.member_name">{{ sel.member_name }}</strong><small>No. {{ sel.member_no }}</small></div>
        <div class="rs-tile"><small>Received by</small><strong>{{ sel.received_by || '-' }}</strong></div>
      </div>
      <ReceiptLines :receipt="sel" />
      <p v-if="sel.refs" class="muted small" style="margin: 10px 0 0">Reference: {{ sel.refs }}</p>
      <template #footer>
        <router-link v-if="!sel.isGroup" :to="'/members/' + sel.member_id" class="btn"><UserRound :size="16" /> Open member profile</router-link>
        <button class="btn" @click="sel = null">Close</button>
        <button class="btn primary" @click="openPrint('/print/receipt/' + sel.id)"><Printer :size="16" /> Print receipt</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { BookOpen, CircleAlert, IdCard, Plus, Printer, ReceiptText, UserRound, Users, Wallet } from 'lucide-vue-next'
import DateInput from '../components/DateInput.vue'
import Modal from '../components/Modal.vue'
import ReceiptLines from '../components/ReceiptLines.vue'
import { api } from '../api'
import { PAYMENT_TYPES } from '../constants'
import { fmtDateTime, isoDate, money, openPrint } from '../utils'
import { groupReceipts, whoPaid } from '../receipts'

const now = new Date()
const from = ref(isoDate(new Date(now.getFullYear(), now.getMonth(), 1)))
const to = ref(isoDate())
const items = ref([]) // every payment line (one per book)
const total = ref(0)
const show = ref('') // payment type shown ('' = all)
const sel = ref(null) // the receipt whose details are shown

// The icon of a receipt, from what it was mostly for
const KIND = {
  fee: { icon: BookOpen },
  fine: { icon: CircleAlert },
  membership: { icon: IdCard },
  other: { icon: Wallet },
}
const kindOf = (type) => (type === 'ISSUE_FEE' ? 'fee' : type === 'MEMBERSHIP' ? 'membership' : type === 'OTHER' ? 'other' : 'fine')

// One line per receipt: a receipt can hold several books, and several members (a group visit)
const receipts = computed(() => groupReceipts(items.value).map((r) => {
  const books = r.lines.filter((p) => p.book_acc_no)
  const what = r.types.map((t) => PAYMENT_TYPES[t] || t).join(' + ')
  return {
    ...r,
    // one short line for the list, e.g. "No. 695 · Book issue fee + Damaged book charge · 3 books"
    short: [r.isGroup ? `No. ${r.members.map((m) => m.member_no).join(', ')}` : `No. ${r.member_no}`, what,
      books.length ? `${books.length} book${books.length === 1 ? '' : 's'}` : ''].filter(Boolean).join(' · '),
    kind: kindOf(r.types.length === 1 ? r.types[0] : r.types.find((t) => t !== 'ISSUE_FEE') || r.types[0]),
    label: r.types.length === 1 ? (PAYMENT_TYPES[r.types[0]] || r.types[0]) + (books.length > 1 ? ` · ${books.length} books` : '') : `${r.types.length} kinds`,
  }
}).sort((a, b) => (a.paid_at < b.paid_at ? 1 : -1)))
const typesHere = computed(() => Object.keys(PAYMENT_TYPES).filter((t) => receipts.value.some((r) => r.types.includes(t))))
const countOf = (t) => receipts.value.filter((r) => r.types.includes(t)).length
const shown = computed(() => (show.value === 'group' ? receipts.value.filter((r) => r.isGroup)
  : show.value ? receipts.value.filter((r) => r.types.includes(show.value)) : receipts.value))
const groupCount = computed(() => receipts.value.filter((r) => r.isGroup).length)
const feesTotal = computed(() => items.value.filter((p) => p.payment_type === 'ISSUE_FEE').reduce((t, p) => t + Number(p.amount), 0))
const finesTotal = computed(() => items.value.filter((p) => ['LATE_FINE', 'DAMAGE_FINE', 'LOST_FINE', 'FINE'].includes(p.payment_type))
  .reduce((t, p) => t + Number(p.amount), 0))

const timeOf = (t) => new Date(t).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
const dayOf = (t) => {
  const d = new Date(t)
  if (d.toDateString() === new Date().toDateString()) return 'Today'
  // the year only when it is not this year
  return d.toLocaleDateString('en-GB', d.getFullYear() === new Date().getFullYear() ? { day: '2-digit', month: 'short' } : { day: '2-digit', month: 'short', year: 'numeric' })
}
const fullDate = (t) => fmtDateTime(t)

async function load() {
  const r = await api.get('/reports/payments', { from_date: from.value, to_date: to.value })
  items.value = r.items
  total.value = r.total
}

onMounted(load)
</script>
