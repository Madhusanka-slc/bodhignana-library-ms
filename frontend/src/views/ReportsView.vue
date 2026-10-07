<template>
  <div>
    <div class="page-head no-print">
      <h1>Reports</h1>
    </div>

    <div class="grid-side">
      <div class="card no-print">
        <button v-for="r in REPORTS" :key="r.key" class="pick" :style="current.key === r.key ? 'border-color: var(--blue-600); background: var(--blue-50)' : ''" @click="select(r)">
          <span>{{ r.title }}</span>
        </button>
      </div>

      <div class="card">
        <div class="card-head">
          <div>
            <h2>{{ current.title }}</h2>
            <p class="muted small" style="margin: 0">{{ appSettings.library_name }} · printed {{ fmtDate(isoDate()) }}</p>
          </div>
          <div class="actions no-print">
            <button class="btn" :disabled="!rows.length" @click="exportCsv(current.key, current.columns, rows)"><Download :size="16" /> Excel (CSV)</button>
            <button class="btn" :disabled="!rows.length" @click="print"><Printer :size="16" /> Print</button>
          </div>
        </div>

        <div v-if="current.params" class="filters no-print">
          <div v-for="p in current.params" :key="p.key">
            <label>{{ p.label }}</label>
            <select v-if="p.type === 'select'" v-model="params[p.key]">
              <option v-for="o in p.options" :key="o.value" :value="o.value">{{ o.label }}</option>
            </select>
            <input v-else v-model="params[p.key]" :type="p.type" />
          </div>
          <button class="btn primary" @click="run">Show</button>
        </div>

        <div class="actions" style="margin-bottom: 10px">
          <span class="badge blue">{{ count }} record(s)</span>
          <span v-if="current.total" class="badge green">Total: {{ current.total === 'money' ? money(totalValue) : totalValue }}</span>
        </div>

        <div class="table-wrap">
          <table class="table">
            <thead><tr><th v-for="c in current.columns" :key="c.key" :class="{ num: c.kind === 'money' || c.num }">{{ c.label }}</th></tr></thead>
            <tbody>
              <tr v-for="(r, i) in rows" :key="i">
                <td v-for="c in current.columns" :key="c.key" :class="{ num: c.kind === 'money' || c.num }">{{ formatCell(getPath(r, c.key), c.kind) }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="loaded && !rows.length" class="empty">Nothing to show.</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Download, Printer } from 'lucide-vue-next'
import { api } from '../api'
import { appSettings } from '../store'
import { MEMBERSHIP_TYPES, PAYMENT_TYPES, SECTIONS } from '../constants'
import { exportCsv, fmtDate, formatCell, getPath, isoDate, money } from '../utils'

const col = (key, label, kind, num) => ({ key, label, kind, num })
const loanCols = [
  col('book.acc_no', 'Acc. No.'), col('book.title', 'Title'), col('book.section', 'Section'),
  col('member.membership_no', 'Member No.'), col('member.name', 'Member'), col('member.telephone', 'Telephone'),
  col('issue_date', 'Borrowed', 'date'), col('due_date', 'Due date', 'date'),
]
const memberCols = [
  col('membership_no', 'Member No.'), col('name', 'Name'), col('membership_type', 'Type', 'type'),
  col('telephone', 'Telephone'), col('school', 'School'),
]
const now = new Date()

const REPORTS = [
  { key: 'overdue', title: 'Overdue books', url: '/reports/overdue', total: 'money',
    columns: [...loanCols, col('days_overdue', 'Days late', null, true), col('estimated_fine', 'Fine now', 'money')] },
  { key: 'pending', title: 'Pending returns (all books out)', url: '/reports/pending-returns',
    params: [{ key: 'section', label: 'Section', type: 'select', default: '', options: [{ value: '', label: 'All sections' }, ...SECTIONS.map((s) => ({ value: s, label: s }))] }],
    columns: loanCols },
  { key: 'not-returning', title: 'Members not returning books', url: '/reports/members-with-overdue',
    columns: [col('member.membership_no', 'Member No.'), col('member.name', 'Name'), col('member.telephone', 'Telephone'),
      col('member.address', 'Address'), col('count', 'Books', null, true), col('books', 'Book details'), col('oldest_due', 'Oldest due date', 'date')] },
  { key: 'age', title: 'Children by age', url: '/reports/members-by-age',
    params: [
      { key: 'min_age', label: 'From age', type: 'number', default: 10 },
      { key: 'max_age', label: 'To age', type: 'number', default: 11 },
      { key: 'membership_type', label: 'Membership type', type: 'select', default: '', options: [{ value: '', label: 'All types' }, ...MEMBERSHIP_TYPES] },
    ],
    columns: [...memberCols, col('birthday', 'Birthday', 'date'), col('age', 'Age', null, true)] },
  { key: 'inactive', title: 'Non-active members', url: '/reports/inactive-members',
    params: [
      { key: 'mode', label: 'Show', type: 'select', default: 'no_borrow', options: [{ value: 'no_borrow', label: 'Not borrowing recently' }, { value: 'status', label: 'Marked as not active' }] },
      { key: 'months', label: 'No borrowing for (months)', type: 'number', default: 6 },
    ],
    columns: [...memberCols, col('last_borrowed', 'Last borrowed', 'date')] },
  { key: 'unpaid', title: 'Unpaid fines', url: '/reports/unpaid-fines', total: 'money',
    columns: [...loanCols.slice(0, 6), col('return_date', 'Returned', 'date'), col('total_fine', 'Fine', 'money'), col('paid_amount', 'Paid', 'money'), col('balance', 'To pay', 'money')] },
  { key: 'expiring', title: 'Memberships expiring or expired', url: '/reports/expiring-members',
    params: [{ key: 'days', label: 'Expiring within (days)', type: 'number', default: 30 }],
    columns: [...memberCols, col('expiry_date', 'Expiry date', 'date')] },
  { key: 'sections', title: 'Books by section', url: '/reports/section-summary', total: 'number',
    columns: [col('section', 'Section'), col('total', 'Total', null, true), col('available', 'In library', null, true), col('issued', 'Issued', null, true), col('other', 'Damaged / lost / withdrawn', null, true)] },
  { key: 'membership', title: 'Members by membership type', url: '/reports/membership-summary', total: 'number',
    columns: [col('membership_type', 'Membership type', 'type'), col('total', 'Total', null, true), col('active', 'Active', null, true), col('expired', 'Expired', null, true)] },
  { key: 'payments', title: 'Payments collected', url: '/reports/payments', total: 'money',
    params: [
      { key: 'from_date', label: 'From', type: 'date', default: isoDate(new Date(now.getFullYear(), now.getMonth(), 1)) },
      { key: 'to_date', label: 'To', type: 'date', default: isoDate() },
      { key: 'payment_type', label: 'Type', type: 'select', default: '', options: [{ value: '', label: 'All types' }, ...Object.entries(PAYMENT_TYPES).map(([value, label]) => ({ value, label }))] },
    ],
    columns: [col('receipt_no', 'Receipt'), col('paid_at', 'Date', 'datetime'), col('member_no', 'Member No.'), col('member_name', 'Member'),
      col('payment_type', 'For', 'ptype'), col('book_title', 'Book'), col('received_by', 'Received by'), col('amount', 'Amount', 'money')] },
]

const route = useRoute()
const current = ref(REPORTS.find((r) => r.key === route.query.r) || REPORTS[0])
const params = reactive({})
const rows = ref([])
const count = ref(0)
const totalValue = ref(0)
const loaded = ref(false)

function select(r) {
  current.value = r
  Object.keys(params).forEach((k) => delete params[k])
  ;(r.params || []).forEach((p) => { params[p.key] = p.default })
  run()
}

async function run() {
  loaded.value = false
  const r = await api.get(current.value.url, params)
  rows.value = r.items
  count.value = r.count
  totalValue.value = r.total ?? 0
  loaded.value = true
}

function print() {
  window.print()
}

onMounted(() => select(current.value))
</script>
