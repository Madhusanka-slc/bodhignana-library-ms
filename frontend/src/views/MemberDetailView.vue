<template>
  <div v-if="d">
    <div class="page-head">
      <div>
        <h1>{{ m.name }}</h1>
        <p class="sub">
          {{ m.membership_no }} · {{ typeLabel(m.membership_type) }}
          <span v-if="!m.is_active" class="badge gray">Not active</span>
          <span v-else-if="m.is_expired" class="badge red">Membership expired</span>
          <span v-else class="badge green">Active</span>
        </p>
      </div>
      <div class="actions">
        <router-link :to="`/members/${m.id}/edit`" class="btn"><Pencil :size="16" /> Edit</router-link>
        <button class="btn" @click="openPrint('/print/member-card/' + m.id)"><Printer :size="16" /> Print card</button>
        <button class="btn" @click="showRenew = true"><RefreshCw :size="16" /> Renew membership</button>
        <button class="btn" @click="showPay = true"><Wallet :size="16" /> Record payment</button>
        <button class="btn" :class="{ danger: m.is_active }" @click="toggleActive">
          {{ m.is_active ? 'Make not active' : 'Make active' }}
        </button>
      </div>
    </div>

    <div class="grid-side">
      <div class="card">
        <div class="center">
          <img :src="qrUrl(m.membership_no, 6)" alt="Member QR code" style="width: 170px; height: 170px" />
          <div class="muted small">Member QR code</div>
        </div>
        <dl class="info mt">
          <dt>NIC No.</dt><dd>{{ m.nic_no || '-' }}</dd>
          <dt>Birthday</dt><dd>{{ fmtDate(m.birthday) }}<span v-if="m.age !== null"> ({{ m.age }} years)</span></dd>
          <dt>Telephone</dt><dd>{{ m.telephone || '-' }}</dd>
          <dt>Email</dt><dd>{{ m.email || '-' }}</dd>
          <dt>School</dt><dd>{{ m.school || '-' }}</dd>
          <dt>Address</dt><dd>{{ m.address || '-' }}</dd>
          <dt>Date</dt><dd>{{ fmtDate(m.registered_date) }}</dd>
          <dt>Expiry date</dt><dd>{{ m.membership_type === 'LIFETIME' ? 'Life time' : fmtDate(m.expiry_date) }}</dd>
          <dt>Renewal date</dt><dd>{{ fmtDate(m.renewal_date) }}</dd>
          <dt>Guarantor</dt><dd>{{ m.guarantor_name || '-' }}</dd>
          <dt>Guarantor address</dt><dd>{{ m.guarantor_address || '-' }}</dd>
          <dt>Acc. No/s</dt><dd>{{ m.borrowed_acc_nos || '-' }}</dd>
          <dt v-if="m.notes">Notes</dt><dd v-if="m.notes">{{ m.notes }}</dd>
        </dl>
      </div>

      <div>
        <div class="card">
          <h2>Books with this member now ({{ d.current_loans.length }})</h2>
          <div v-if="!d.current_loans.length" class="empty">No books with this member.</div>
          <div v-else class="table-wrap">
            <table class="table">
              <thead><tr><th>Acc. No.</th><th>Title</th><th>Date borrowed</th><th>Due date</th><th></th></tr></thead>
              <tbody>
                <tr v-for="l in d.current_loans" :key="l.id">
                  <td>{{ l.book.acc_no }}</td>
                  <td>{{ l.book.title }}</td>
                  <td>{{ fmtDate(l.issue_date) }}</td>
                  <td><span :class="l.is_overdue ? 'badge red' : ''">{{ fmtDate(l.due_date) }}</span></td>
                  <td class="num"><button v-if="!l.is_overdue" class="btn sm" @click="renewLoan(l)">Extend</button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-if="d.fines.length" class="card">
          <div class="card-head">
            <h2>Unpaid fines</h2>
            <span class="badge red">{{ money(d.unpaid) }}</span>
          </div>
          <div class="table-wrap">
            <table class="table">
              <thead><tr><th>Book</th><th>Returned</th><th class="num">Fine</th><th class="num">Paid</th><th class="num">To pay</th><th></th></tr></thead>
              <tbody>
                <tr v-for="l in d.fines" :key="l.id">
                  <td>{{ l.book.acc_no }} · {{ l.book.title }}</td>
                  <td>{{ fmtDate(l.return_date) }}</td>
                  <td class="num">{{ money(l.total_fine) }}</td>
                  <td class="num">{{ money(l.paid_amount) }}</td>
                  <td class="num"><strong>{{ money(l.balance) }}</strong></td>
                  <td class="num"><button class="btn sm primary" @click="payFine(l)">Collect</button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <h2>Payments</h2>
          <div v-if="!d.payments.length" class="empty">No payments yet.</div>
          <div v-else class="table-wrap">
            <table class="table">
              <thead><tr><th>Receipt</th><th>Date</th><th>For</th><th class="num">Amount</th><th></th></tr></thead>
              <tbody>
                <tr v-for="p in d.payments" :key="p.id">
                  <td>{{ p.receipt_no }}</td>
                  <td>{{ fmtDateTime(p.paid_at) }}</td>
                  <td>{{ PAYMENT_TYPES[p.payment_type] || p.payment_type }}<div v-if="p.book_title" class="muted small">{{ p.book_acc_no }} · {{ p.book_title }}</div></td>
                  <td class="num">{{ money(p.amount) }}</td>
                  <td class="num"><button class="icon-btn" title="Print receipt" @click="openPrint('/print/receipt/' + p.id)"><Printer :size="17" /></button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <h2>Borrowing history</h2>
          <div v-if="!d.history.length" class="empty">No returned books yet.</div>
          <div v-else class="table-wrap">
            <table class="table">
              <thead><tr><th>Acc. No.</th><th>Title</th><th>Borrowed</th><th>Due</th><th>Returned</th><th class="num">Fine</th></tr></thead>
              <tbody>
                <tr v-for="l in d.history" :key="l.id">
                  <td>{{ l.book.acc_no }}</td>
                  <td>{{ l.book.title }} <span v-if="l.is_damaged" class="badge red">Damaged</span></td>
                  <td>{{ fmtDate(l.issue_date) }}</td>
                  <td>{{ fmtDate(l.due_date) }}</td>
                  <td>{{ fmtDate(l.return_date) }}</td>
                  <td class="num">{{ l.total_fine ? money(l.total_fine) : '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <Modal v-if="showRenew" title="Renew membership" @close="showRenew = false">
      <p class="muted">Current expiry date: {{ m.membership_type === 'LIFETIME' ? 'Life time' : fmtDate(m.expiry_date) }}</p>
      <div class="form-grid">
        <div class="field"><label>Years</label><input v-model.number="renew.years" type="number" min="1" /></div>
        <div class="field"><label>Fee paid (Rs.)</label><input v-model.number="renew.fee" type="number" min="0" /></div>
      </div>
      <template #footer>
        <button class="btn" @click="showRenew = false">Cancel</button>
        <button class="btn primary" @click="doRenew">Renew</button>
      </template>
    </Modal>

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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Pencil, Printer, RefreshCw, Wallet } from 'lucide-vue-next'
import Modal from '../components/Modal.vue'
import { api, qrUrl } from '../api'
import { toast } from '../store'
import { PAYMENT_TYPES, typeLabel } from '../constants'
import { fmtDate, fmtDateTime, money, openPrint } from '../utils'

const route = useRoute()
const d = ref(null)
const m = computed(() => d.value.member)
const showRenew = ref(false)
const showPay = ref(false)
const renew = reactive({ years: 1, fee: 0 })
const pay = reactive({ payment_type: 'MEMBERSHIP', amount: 0, notes: '' })

async function load() {
  d.value = await api.get(`/members/${route.params.id}`)
}

async function toggleActive() {
  const msg = m.value.is_active ? 'Make this member not active? They will not be able to borrow books.' : 'Make this member active again?'
  if (!confirm(msg)) return
  try {
    await api.put(`/members/${m.value.id}`, { ...m.value, is_active: !m.value.is_active })
    toast('Saved')
    load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

async function doRenew() {
  try {
    const r = await api.post(`/members/${m.value.id}/renew`, renew)
    showRenew.value = false
    toast(`Membership renewed until ${fmtDate(r.member.expiry_date)}`)
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
    toast(`Payment saved. Receipt ${p.receipt_no}`)
    openPrint('/print/receipt/' + p.id)
    load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

function payFine(loan) {
  if (confirm(`Collect ${money(loan.balance)} for "${loan.book.title}"?`)) savePayment(loan)
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

onMounted(load)
</script>
