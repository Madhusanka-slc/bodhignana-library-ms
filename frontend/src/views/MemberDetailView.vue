<template>
  <div v-if="d" class="profile2">
    <!-- Left: vertical profile bar with photo, who and all details -->
    <aside class="card profile-bar">
      <div class="bar-top">
        <MemberPhoto :src="m.photo_url" :name="m.name" size="lg" />
        <h1>{{ m.name }}</h1>
        <div class="profile-tags">
          <span class="code-tag big">{{ m.membership_no }}</span>
          <span class="badge blue">{{ typeLabel(m.membership_type) }}</span>
          <span v-if="!m.is_active" class="badge gray">Not active</span>
          <span v-else-if="m.is_expired" class="badge red">Expired</span>
          <span v-else class="badge green">Active</span>
        </div>
        <button class="profile-qr" title="Print member card" @click="openPrint('/print/member-card/' + m.id)">
          <img :src="qrUrl(m.membership_no, 4)" alt="Member QR code" />
          <span><Printer :size="13" /> Member card</span>
        </button>
      </div>

      <div class="bar-section">
        <h2><User :size="16" /> Personal details</h2>
        <dl class="bar-info">
          <dt>NIC No.</dt><dd>{{ m.nic_no || '-' }}</dd>
          <dt>Birthday</dt><dd>{{ fmtDate(m.birthday) }}<span v-if="m.age !== null" class="muted"> ({{ m.age }} yrs)</span></dd>
          <dt>Telephone</dt><dd>{{ m.telephone || '-' }}</dd>
          <dt>Email</dt><dd>{{ m.email || '-' }}</dd>
          <dt>School</dt><dd>{{ m.school || '-' }}</dd>
          <dt>Address</dt><dd>{{ m.address || '-' }}</dd>
        </dl>
      </div>

      <div class="bar-section">
        <h2><IdCard :size="16" /> Membership</h2>
        <dl class="bar-info">
          <dt>Type</dt><dd>{{ typeLabel(m.membership_type) }}</dd>
          <dt>Registered</dt><dd>{{ fmtDate(m.registered_date) }}</dd>
          <dt>Registered by</dt><dd>{{ m.created_by || '-' }}</dd>
          <dt>Expiry date</dt><dd>{{ m.membership_type === 'LIFETIME' ? 'Life time' : fmtDate(m.expiry_date) }}</dd>
          <dt>Renewed</dt><dd>{{ fmtDate(m.renewal_date) }}</dd>
        </dl>
      </div>

      <div class="bar-section">
        <h2><Users :size="16" /> Guarantor</h2>
        <dl class="bar-info">
          <dt>Name</dt><dd>{{ m.guarantor_name || '-' }}</dd>
          <dt>Address</dt><dd>{{ m.guarantor_address || '-' }}</dd>
          <template v-if="m.notes"><dt>Notes</dt><dd>{{ m.notes }}</dd></template>
        </dl>
      </div>
    </aside>

    <!-- Right: actions, at a glance, books and money -->
    <div class="profile-content">
      <div class="card profile-actions2">
        <router-link :to="`/members/${m.id}/edit`" class="btn"><Pencil :size="16" /> Edit</router-link>
        <button class="btn" @click="openPrint('/print/member-card/' + m.id)"><Printer :size="16" /> Print card</button>
        <button class="btn" @click="showRenew = true"><RefreshCw :size="16" /> Renew</button>
        <button class="btn" @click="showPay = true"><Wallet :size="16" /> Record payment</button>
        <span class="grow"></span>
        <button class="btn" :class="{ danger: m.is_active }" @click="askActive">
          <UserX v-if="m.is_active" :size="16" /><UserCheck v-else :size="16" /> {{ m.is_active ? 'Make not active' : 'Make active' }}
        </button>
      </div>

      <div class="status-row profile-stats">
        <div class="status-box tint-1"><BookOpen :size="20" /><span class="v">{{ d.current_loans.length }} <small>of {{ maxBooks }}</small></span><span class="l">Books now</span></div>
        <div class="status-box tint-2"><CircleAlert :size="20" /><span class="v">{{ overdueCount }}</span><span class="l">Overdue</span></div>
        <div class="status-box tint-3"><Wallet :size="20" /><span class="v">{{ money(d.unpaid) }}</span><span class="l">Unpaid fines</span></div>
        <div class="status-box tint-4"><CalendarCheck :size="20" /><span class="v small-v">{{ validText }}</span><span class="l">{{ m.is_expired ? 'Membership expired on' : m.membership_type === 'LIFETIME' ? 'Membership' : m.expiry_date ? 'Membership valid until' : 'Expiry date' }}</span></div>
      </div>

      <!-- Books and money, as tabs -->
      <div class="card profile-records">
        <div class="record-tabs" role="tablist">
          <button v-for="t in tabs" :key="t.key" role="tab" class="report-chip" :class="{ on: tab === t.key }" @click="tab = t.key">
            {{ t.label }} <span class="chip-n">{{ t.count }}</span>
          </button>
        </div>

        <!-- Books now -->
        <template v-if="tab === 'now'">
          <div v-if="!d.current_loans.length" class="empty">No books with this member now.</div>
          <table v-else class="table report-table">
            <colgroup><col style="width: 104px" /><col /><col style="width: 116px" /><col style="width: 130px" /><col style="width: 100px" /></colgroup>
            <thead><tr><th>Acc. No.</th><th>Title</th><th>Borrowed</th><th>Due date</th><th></th></tr></thead>
            <tbody>
              <tr v-for="l in d.current_loans" :key="l.id" class="click" @click="$router.push('/books/' + l.book.id)">
                <td><span class="code-tag">{{ l.book.acc_no }}</span></td>
                <td :title="l.book.title">{{ l.book.title }}</td>
                <td>{{ fmtDate(l.issue_date) }}</td>
                <td><span :class="l.is_overdue ? 'badge red' : ''">{{ fmtDate(l.due_date) }}</span></td>
                <td class="num" @click.stop><button v-if="!l.is_overdue" class="btn sm" title="Give 14 more days" @click="renewLoan(l)">Extend</button></td>
              </tr>
            </tbody>
          </table>
        </template>

        <!-- Unpaid fines -->
        <template v-else-if="tab === 'fines'">
          <div v-if="!d.fines.length" class="empty">No unpaid fines.</div>
          <table v-else class="table report-table">
            <colgroup><col style="width: 104px" /><col /><col style="width: 116px" /><col style="width: 110px" /><col style="width: 110px" /><col style="width: 110px" /></colgroup>
            <thead><tr><th>Acc. No.</th><th>Book</th><th>Returned</th><th class="num">Fine</th><th class="num">To pay</th><th></th></tr></thead>
            <tbody>
              <tr v-for="l in d.fines" :key="l.id">
                <td><span class="code-tag">{{ l.book.acc_no }}</span></td>
                <td :title="l.book.title">{{ l.book.title }}</td>
                <td>{{ fmtDate(l.return_date) }}</td>
                <td class="num">{{ money(l.total_fine) }}</td>
                <td class="num"><strong>{{ money(l.balance) }}</strong></td>
                <td class="num"><button class="btn sm primary" @click="askFine(l)">Collect</button></td>
              </tr>
            </tbody>
          </table>
        </template>

        <!-- Payments -->
        <template v-else-if="tab === 'payments'">
          <div v-if="!d.payments.length" class="empty">No payments yet.</div>
          <table v-else class="table report-table">
            <colgroup><col style="width: 140px" /><col style="width: 160px" /><col /><col style="width: 120px" /><col style="width: 56px" /></colgroup>
            <thead><tr><th>Receipt</th><th>Date</th><th>For</th><th class="num">Amount</th><th></th></tr></thead>
            <tbody>
              <tr v-for="p in d.payments" :key="p.id">
                <td><span class="code-tag">{{ p.receipt_no }}</span></td>
                <td>{{ fmtDateTime(p.paid_at) }}</td>
                <td :title="p.book_title">{{ PAYMENT_TYPES[p.payment_type] || p.payment_type }}<span v-if="p.book_acc_no" class="muted"> · {{ p.book_acc_no }}</span></td>
                <td class="num">{{ money(p.amount) }}</td>
                <td class="num"><button class="icon-btn" title="Print receipt" @click="openPrint('/print/receipt/' + p.id)"><Printer :size="17" /></button></td>
              </tr>
            </tbody>
          </table>
        </template>

        <!-- History -->
        <template v-else>
          <div v-if="!d.history.length" class="empty">No returned books yet.</div>
          <table v-else class="table report-table">
            <colgroup><col style="width: 104px" /><col /><col style="width: 116px" /><col style="width: 116px" /><col style="width: 110px" /></colgroup>
            <thead><tr><th>Acc. No.</th><th>Title</th><th>Borrowed</th><th>Returned</th><th class="num">Fine</th></tr></thead>
            <tbody>
              <tr v-for="l in d.history" :key="l.id" class="click" @click="$router.push('/books/' + l.book.id)">
                <td><span class="code-tag">{{ l.book.acc_no }}</span></td>
                <td :title="l.book.title">{{ l.book.title }} <span v-if="l.is_damaged" class="badge red">Damaged</span><span v-else-if="l.late_days" class="badge orange">{{ l.late_days }} day(s) late</span></td>
                <td>{{ fmtDate(l.issue_date) }}</td>
                <td>{{ fmtDate(l.return_date) }}</td>
                <td class="num">{{ l.total_fine ? money(l.total_fine) : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </template>
      </div>
    </div>

    <!-- Renew membership -->
    <Modal v-if="showRenew" title="Renew membership" @close="showRenew = false">
      <p class="muted">Current expiry date: <strong>{{ m.membership_type === 'LIFETIME' ? 'Life time' : fmtDate(m.expiry_date) }}</strong></p>
      <div class="form-grid">
        <div class="field"><label>Years</label><input v-model.number="renew.years" type="number" min="1" /></div>
        <div class="field"><label>Fee paid (Rs.)</label><input v-model.number="renew.fee" type="number" min="0" /></div>
      </div>
      <template #footer>
        <button class="btn" @click="showRenew = false">Cancel</button>
        <button class="btn primary" @click="doRenew"><RefreshCw :size="16" /> Renew</button>
      </template>
    </Modal>

    <!-- Record payment -->
    <Modal v-if="showPay" title="Record payment" @close="showPay = false">
      <div class="form-grid">
        <div class="field">
          <label>Payment for</label>
          <select v-model="pay.payment_type">
            <option v-for="(label, k) in PAYMENT_TYPES" :key="k" :value="k">{{ label }}</option>
          </select>
        </div>
        <div class="field"><label>Amount (Rs.)</label><input v-model.number="pay.amount" type="number" min="0" /></div>
        <div class="field wide"><label>Notes</label><input v-model="pay.notes" /></div>
      </div>
      <template #footer>
        <button class="btn" @click="showPay = false">Cancel</button>
        <button class="btn primary" @click="savePayment()"><Printer :size="16" /> Save and print receipt</button>
      </template>
    </Modal>

    <!-- Confirm (instead of the browser's plain pop-up) -->
    <Modal v-if="ask" :title="ask.title" @close="ask = null">
      <p style="margin: 0">{{ ask.text }}</p>
      <template #footer>
        <button class="btn" @click="ask = null">Cancel</button>
        <button class="btn" :class="ask.danger ? 'danger' : 'primary'" :disabled="busy" @click="ask.run()">{{ ask.ok }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  BookOpen, CalendarCheck, CircleAlert, IdCard, Pencil, Printer, RefreshCw, User, UserCheck, Users, UserX, Wallet,
} from 'lucide-vue-next'
import Modal from '../components/Modal.vue'
import MemberPhoto from '../components/MemberPhoto.vue'
import { api, qrUrl } from '../api'
import { appSettings, toast } from '../store'
import { PAYMENT_TYPES, typeLabel } from '../constants'
import { fmtDate, fmtDateTime, money, openPrint } from '../utils'

const route = useRoute()
const d = ref(null)
const m = computed(() => d.value.member)
const tab = ref('now')
const showRenew = ref(false)
const showPay = ref(false)
const ask = ref(null) // { title, text, ok, danger, run }
const busy = ref(false)
const renew = reactive({ years: 1, fee: 0 })
const pay = reactive({ payment_type: 'MEMBERSHIP', amount: 0, notes: '' })

const overdueCount = computed(() => d.value.current_loans.filter((l) => l.is_overdue).length)
const maxBooks = computed(() => Number(appSettings[`max_books_${(m.value.membership_type || '').toLowerCase()}`] ?? appSettings.max_books_default ?? 2))
const validText = computed(() => (m.value.membership_type === 'LIFETIME' ? 'Life time' : m.value.expiry_date ? fmtDate(m.value.expiry_date) : 'Not set'))
const tabs = computed(() => [
  { key: 'now', label: 'Books now', count: d.value.current_loans.length },
  { key: 'fines', label: 'Unpaid fines', count: d.value.fines.length },
  { key: 'payments', label: 'Payments', count: d.value.payments.length },
  { key: 'history', label: 'History', count: d.value.history.length },
])

async function load(first = false) {
  d.value = await api.get(`/members/${route.params.id}`)
  // Open the tab that matters most: books out, then fines, then history.
  if (first) tab.value = d.value.current_loans.length ? 'now' : d.value.fines.length ? 'fines' : 'history'
}

async function run(fn, done) {
  busy.value = true
  try {
    await fn()
    ask.value = null
    if (done) toast(done)
    await load()
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    busy.value = false
  }
}

function askActive() {
  const active = m.value.is_active
  ask.value = {
    title: active ? 'Make not active?' : 'Make active again?',
    text: active ? `${m.value.name} will not be able to borrow books until made active again.` : `${m.value.name} will be able to borrow books again.`,
    ok: active ? 'Make not active' : 'Make active',
    danger: active,
    run: () => run(() => api.put(`/members/${m.value.id}`, { ...m.value, is_active: !active }), 'Saved'),
  }
}

async function doRenew() {
  try {
    const r = await api.post(`/members/${m.value.id}/renew`, renew)
    showRenew.value = false
    toast(r.member.membership_type === 'LIFETIME' ? 'Membership renewed' : `Membership renewed until ${fmtDate(r.member.expiry_date)}`)
    if (r.payment) openPrint('/print/receipt/' + r.payment.id)
    load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

async function savePayment(loan = null) {
  try {
    const body = loan
      ? { member_id: m.value.id, loan_id: loan.id, payment_type: loan.damage_fine > 0 && loan.late_fine > 0 ? 'FINE' : loan.damage_fine > 0 ? 'DAMAGE_FINE' : 'LATE_FINE', amount: loan.balance, notes: 'Fine for ' + loan.book.acc_no }
      : { member_id: m.value.id, ...pay }
    const p = await api.post('/payments', body)
    showPay.value = false
    ask.value = null
    toast(`Payment saved. Receipt ${p.receipt_no}`)
    openPrint('/print/receipt/' + p.id)
    load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

function askFine(loan) {
  ask.value = {
    title: 'Collect fine?',
    text: `Collect ${money(loan.balance)} for "${loan.book.title}" (${loan.book.acc_no}). A receipt will be printed.`,
    ok: `Collect ${money(loan.balance)}`,
    danger: false,
    run: () => savePayment(loan),
  }
}

async function renewLoan(l) {
  try {
    const r = await api.post(`/circulation/renew/${l.id}`)
    toast(`New due date: ${fmtDate(r.due_date)}`)
    load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

onMounted(() => load(true))
</script>
