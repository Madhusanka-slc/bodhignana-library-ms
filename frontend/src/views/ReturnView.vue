<template>
  <div>
    <div class="page-head">
      <div>
        <h1>Return book</h1>
        <p class="sub">Scan the book. Fines are worked out automatically.</p>
      </div>
    </div>

    <div class="card">
      <ScanBox ref="scan" label="Scan the book being returned"
        placeholder="Scan book QR / barcode, type Acc. No., or scan the member card"
        hint="Scanning a member card shows all books that member has." @scan="onScan" />
      <p v-if="error" class="alert red">{{ error }}</p>

      <div v-if="memberLoans" class="mt">
        <p class="muted">Books with {{ memberLoans.member.name }} ({{ memberLoans.member.membership_no }}). Choose the one being returned:</p>
        <div v-if="!memberLoans.loans.length" class="alert blue">This member has no books to return.</div>
        <button v-for="l in memberLoans.loans" :key="l.id" class="pick" @click="loadPreview(l.book.acc_no)">
          <span><strong>{{ l.book.acc_no }}</strong> · {{ l.book.title }}</span>
          <span :class="l.is_overdue ? 'badge red' : 'badge gray'">Due {{ fmtDate(l.due_date) }}</span>
        </button>
      </div>

      <div v-if="choices.length" class="mt">
        <p class="muted">Choose the copy being returned:</p>
        <button v-for="b in choices" :key="b.id" class="pick" @click="loadPreview(b.acc_no)">
          <span><strong>{{ b.acc_no }}</strong> · {{ b.title }} <span class="muted">· {{ b.borrower_name }}</span></span>
          <StatusBadge :status="b.status" />
        </button>
      </div>
    </div>

    <!-- Finished -->
    <div v-if="result" class="card done-panel">
      <div class="ok"><Check :size="34" /></div>
      <h2>"{{ result.loan.book.title }}" returned</h2>
      <p v-if="!result.loan.is_damaged" class="muted">Put it back on the shelf:</p>
      <div v-if="!result.loan.is_damaged" class="due-big">{{ result.loan.book.location || result.loan.book.section || 'Shelf not set' }}</div>
      <p v-else class="alert orange">The book is marked as damaged. Keep it aside for repair.</p>
      <p v-if="result.payment" class="alert green">Payment received: {{ money(result.payment.amount) }} · Receipt {{ result.payment.receipt_no }}</p>
      <p v-else-if="result.total > 0" class="alert orange">Fine of {{ money(result.total) }} is not paid yet. It is saved on the member's account.</p>
      <div class="actions" style="justify-content: center">
        <button v-if="result.payment" class="btn primary big" @click="openPrint('/print/receipt/' + result.payment.id)">
          <Printer :size="20" /> Print receipt
        </button>
        <button class="btn big" @click="next">Return next book</button>
      </div>
    </div>

    <!-- Preview -->
    <div v-else-if="p" class="grid-2">
      <div class="card">
        <h2>{{ p.loan.book.title }}</h2>
        <dl class="info">
          <dt>Acc. No.</dt><dd>{{ p.loan.book.acc_no }}</dd>
          <dt>Member</dt><dd>{{ p.loan.member.name }} ({{ p.loan.member.membership_no }})</dd>
          <dt>Issued on</dt><dd>{{ fmtDate(p.loan.issue_date) }}</dd>
          <dt>Due date</dt><dd>{{ fmtDate(p.loan.due_date) }}</dd>
          <dt>Returned on</dt><dd>{{ fmtDate(p.return_date) }}</dd>
          <dt>Book price</dt><dd>{{ money(p.loan.book.price) }}</dd>
        </dl>
        <p v-if="p.late_days === 0" class="alert green">Returned on time. No late fine.</p>
        <p v-else-if="p.late_fine === 0" class="alert blue">
          {{ p.late_days }} day(s) late, but within the {{ p.grace_days }}-day free period. No late fine.
        </p>
      </div>

      <div class="card">
        <h2>Fines</h2>
        <table class="table">
          <tbody>
            <tr>
              <td>Late fine<div class="muted small">
                {{ p.late_days }} working day(s) late<span v-if="p.calendar_days_late !== p.late_days"> (holidays not counted)</span>.
                First {{ p.grace_days }} day(s) free, then Rs. {{ p.fine_per_day }} per day.
              </div></td>
              <td class="num">{{ money(p.late_fine) }}</td>
            </tr>
            <tr>
              <td>
                <label class="check"><input v-model="damaged" type="checkbox" @change="refresh" /> The book is damaged</label>
                <div class="muted small">Damage fine = {{ p.damage_multiplier }} × book price</div>
              </td>
              <td class="num">{{ money(p.damage_fine) }}</td>
            </tr>
            <tr>
              <td><strong>Total to pay</strong></td>
              <td class="num total-big">{{ money(p.total) }}</td>
            </tr>
          </tbody>
        </table>

        <div v-if="p.total > 0" class="mt">
          <label class="check"><input v-model="collect" type="checkbox" /> Member paid now (print receipt)</label>
        </div>
        <div class="mt">
          <label for="notes">Notes (optional)</label>
          <input id="notes" v-model="notes" placeholder="e.g. cover torn" />
        </div>
        <button class="btn success big full mt" :disabled="busy" @click="confirmReturn">
          <Check :size="20" /> Confirm return
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Check, Printer } from 'lucide-vue-next'
import ScanBox from '../components/ScanBox.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api } from '../api'
import { toast } from '../store'
import { fmtDate, money, openPrint } from '../utils'

const scan = ref(null)
const p = ref(null)
const acc = ref('')
const damaged = ref(false)
const collect = ref(true)
const notes = ref('')
const error = ref('')
const result = ref(null)
const busy = ref(false)
const memberLoans = ref(null)
const choices = ref([])

function clear() {
  p.value = null
  result.value = null
  error.value = ''
  memberLoans.value = null
  choices.value = []
  damaged.value = false
  collect.value = true
  notes.value = ''
}

async function onScan(code) {
  clear()
  try {
    const r = await api.get('/circulation/scan', { code })
    if (r.type === 'member') {
      memberLoans.value = await api.get(`/circulation/member-status/${r.member.id}`)
    } else if (r.type === 'isbn') {
      const out = r.books.filter((b) => b.status === 'ISSUED')
      if (out.length === 1) await loadPreview(out[0].acc_no)
      else if (!out.length) error.value = 'None of the copies with this ISBN are issued.'
      else choices.value = out
    } else {
      await loadPreview(r.book.acc_no)
    }
  } catch (e) {
    error.value = e.message
  }
}

async function loadPreview(accNo) {
  memberLoans.value = null
  choices.value = []
  error.value = ''
  acc.value = accNo
  try {
    p.value = await api.get('/circulation/return-preview', { acc_no: accNo, damaged: damaged.value })
  } catch (e) {
    p.value = null
    error.value = e.message
  }
}

async function refresh() {
  p.value = await api.get('/circulation/return-preview', { acc_no: acc.value, damaged: damaged.value })
}

async function confirmReturn() {
  busy.value = true
  try {
    result.value = await api.post('/circulation/return', {
      acc_no: acc.value,
      damaged: damaged.value,
      notes: notes.value,
      collect_payment: collect.value,
    })
    toast('Book returned')
    if (result.value.payment) openPrint('/print/receipt/' + result.value.payment.id)
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    busy.value = false
  }
}

function next() {
  clear()
  scan.value?.focus()
}
</script>
