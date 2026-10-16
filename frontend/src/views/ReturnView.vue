<template>
  <div>
    <!-- Title and steps stay at the top; only what is below them scrolls -->
    <div class="flow-top">
      <div class="page-head">
        <div>
          <h1>Return book</h1>
          <p class="sub">Scan the member, tick the books returned.</p>
        </div>
        <button v-if="st || done" class="btn" @click="next"><RotateCcw :size="16" /> Start again</button>
      </div>

      <div class="steps">
        <div class="step" :class="{ on: step === 'scan', done: step !== 'scan' }"><b>1</b> Member</div>
        <div class="step" :class="{ on: step === 'check', done: step === 'pay' || step === 'done' }"><b>2</b> Books</div>
        <div v-if="needsPay" class="step" :class="{ on: step === 'pay', done: step === 'done' }"><b>3</b> Pay</div>
        <div class="step" :class="{ on: step === 'done' }"><b>{{ needsPay ? 4 : 3 }}</b> Done</div>
      </div>
    </div>

    <!-- Finished -->
    <div v-if="step === 'done'" class="card issue-done">
      <div class="idone-head">
        <span class="idone-ok"><Check :size="26" /></span>
        <div>
          <h2>{{ done.items.length }} book{{ done.items.length === 1 ? '' : 's' }} returned</h2>
          <div class="muted">by {{ done.status.member.name }} · {{ done.status.member.membership_no }}</div>
        </div>
      </div>

      <div class="idone-tiles">
        <div class="idone-tile cards">
          <IdCard :size="22" />
          <span><small>Give back to the member</small><strong>{{ cardsBack }} card{{ cardsBack === 1 ? '' : 's' }}</strong>
            <small>They now hold {{ done.status.can_borrow }} of {{ done.status.max_books }} card(s)</small></span>
        </div>
        <div class="idone-tile" :class="done.total > 0 && !receipts.length ? 'owe' : done.total > 0 ? 'fee' : ''">
          <Banknote :size="22" />
          <span><small>Charges for this return</small><strong>{{ done.total > 0 ? money(done.total) : 'None' }}</strong>
            <small>{{ done.total > 0 ? (receipts.length ? 'Paid · receipt ' + done.items.filter((r) => r.payment).map((r) => r.payment.receipt_no).join(', ') : 'Not paid: added to their next payment')
              : 'On time and in good condition' }}</small></span>
        </div>
        <div class="idone-tile">
          <BookOpen :size="22" />
          <span><small>Books still with the member</small><strong>{{ done.status.loans.length }} of {{ done.status.max_books }}</strong>
            <small>{{ done.status.loans.length ? done.status.loans.map((l) => l.book.acc_no).join(', ') : 'All books are back' }}</small></span>
        </div>
      </div>

      <h3 class="idone-h">Returned now</h3>
      <div class="idone-books">
        <div v-for="r in done.items" :key="r.loan.id" class="idone-book" :class="{ late: r.loan.is_lost }">
          <span class="suggest-box book">{{ firstLetter(r.loan.book.title) }}</span>
          <span class="idone-book-text">
            <strong :title="r.loan.book.title">{{ r.loan.book.title }}</strong>
            <small><span class="code-tag">{{ r.loan.book.acc_no }}</span>
              <template v-if="r.total"> · {{ money(r.total) }}</template></small>
          </span>
          <span class="idone-book-due">
            <span v-if="r.loan.is_lost" class="badge red">Missing</span>
            <span v-else-if="r.loan.is_damaged" class="badge orange">Damaged: keep aside</span>
            <span v-else class="badge green">Put back on the shelf</span>
            <small v-if="!r.loan.is_lost && !r.loan.is_damaged">{{ r.loan.book.location || r.loan.book.section || 'Shelf not set' }}</small>
          </span>
        </div>
      </div>

      <div class="idone-actions">
        <button v-if="receipts.length" class="btn big" @click="printReceipts"><Printer :size="20" /> Print receipt</button>
        <router-link v-if="done.total > 0 && !receipts.length" :to="'/pay?member=' + done.status.member.id" class="btn big"><Banknote :size="20" /> Pay now</router-link>
        <router-link v-if="done.status.can_borrow > 0 && !(done.total > 0 && !receipts.length)" :to="'/issue?member=' + done.status.member.id" class="btn big">
          <ArrowUpRight :size="20" /> Issue books to this member
        </router-link>
        <button class="btn primary big" @click="next"><Check :size="20" /> Done · next member</button>
      </div>
    </div>

    <!-- Step 2: pay -->
    <div v-else-if="step === 'pay'" class="card pay-step">
      <h2>Charges to pay</h2>
      <p class="muted">{{ st.member.name }} ({{ st.member.membership_no }})</p>
      <table class="table report-table">
        <thead><tr><th>Acc. No.</th><th>Title</th><th>For</th><th class="num">To pay</th></tr></thead>
        <tbody>
          <tr v-for="r in picked.filter((x) => x.pv.total > 0)" :key="r.loan.id">
            <td><span class="code-tag">{{ r.loan.book.acc_no }}</span></td>
            <td :title="r.loan.book.title">{{ r.loan.book.title }}</td>
            <td>{{ why(r) }}</td>
            <td class="num">{{ money(r.pv.total) }}</td>
          </tr>
          <tr><td colspan="3" class="totalrow"><strong>Total to pay</strong></td><td class="num totalrow total-big">{{ money(total) }}</td></tr>
        </tbody>
      </table>
      <div class="pay-actions">
        <button class="btn big" @click="step = 'check'"><ChevronLeft :size="20" /> Back</button>
        <button class="btn big" :disabled="busy" @click="confirm(false)">Return without paying</button>
        <button class="btn success big" :disabled="busy" @click="confirm(true)"><Printer :size="20" /> Collect {{ money(total) }} and return</button>
      </div>
      <p class="muted small" style="margin: 10px 0 0; text-align: right">Unpaid amounts go to the next payment.</p>
    </div>

    <!-- Step 1: the member (same as Issue book), then step 2: their books -->
    <template v-else>
      <div v-if="!st" class="card">
        <ScanBox ref="scan" label="Scan the member card" placeholder="Scan card, or type name / member no."
          hint="Type to search, then pick." suggest="member"
          @scan="onMemberScan" @pick="(s) => pickMember(s.id)" />
        <p v-if="error" class="alert red">{{ error }}</p>
        <!-- A book was scanned instead of the card: offer the member who has it -->
        <button v-if="holder" class="pick mt" @click="pickMember(holder.id)">
          <span><strong>{{ holder.name }}</strong> <span class="muted">· {{ holder.membership_no }}</span></span>
          <span class="muted small">Has this book</span>
        </button>
        <div v-if="matches.length" class="mt">
          <p class="muted">Choose the member:</p>
          <button v-for="m in matches" :key="m.id" class="pick" @click="pickMember(m.id)">
            <span><strong>{{ m.name }}</strong> <span class="muted">· {{ m.membership_no }}</span></span>
            <span class="muted small">{{ m.borrowed_acc_nos ? 'Has ' + m.borrowed_acc_nos : 'No books now' }}</span>
          </button>
        </div>
      </div>

      <div v-if="st" class="card">
        <div class="ret-head">
          <div>
            <h2 style="margin: 0">{{ st.member.name }}</h2>
            <div class="muted small">{{ st.member.membership_no }} · has {{ st.loans.length }} book(s)</div>
          </div>
          <div class="ret-tools">
            <button class="btn sm" @click="setAll(true)">Tick all</button>
            <button class="btn sm" @click="setAll(false)">Untick all</button>
          </div>
        </div>
        <p v-if="rows.length && !picked.length" class="ret-hint">Tick the books returned.</p>
        <div v-if="!rows.length" class="alert blue">This member has no books to return.</div>
        <table v-else class="table report-table ret-table">
          <colgroup><col style="width: 48px" /><col style="width: 92px" /><col /><col style="width: 108px" /><col style="width: 124px" /><col style="width: 92px" /><col style="width: 132px" /><col style="width: 146px" /></colgroup>
          <thead><tr><th></th><th>Acc. No.</th><th>Title</th><th>Borrowed</th><th>Due</th><th>Late</th><th>Condition</th><th class="num">To pay</th></tr></thead>
          <tbody>
            <tr v-for="r in rows" :key="r.loan.id" :class="{ off: !r.pick }" @click="r.pick = !r.pick">
              <td @click.stop><input v-model="r.pick" type="checkbox" :aria-label="'Return ' + r.loan.book.acc_no" /></td>
              <td><span class="code-tag">{{ r.loan.book.acc_no }}</span></td>
              <td :title="r.loan.book.title">{{ r.loan.book.title }}</td>
              <td>{{ fmtDate(r.loan.issue_date) }}</td>
              <td><span :class="{ 'badge red': r.loan.is_overdue }">{{ fmtDate(r.loan.due_date) }}</span></td>
              <td>{{ !r.pv ? '…' : r.cond === 'lost' ? '-' : r.pv.late_days ? r.pv.late_days + ' day(s)' : 'On time' }}</td>
              <td @click.stop>
                <select v-model="r.cond" class="cond" :class="r.cond" :aria-label="'Condition of ' + r.loan.book.acc_no" @change="preview(r)">
                  <option value="ok">Good</option>
                  <option value="damaged">Damaged</option>
                  <option value="lost">Missing</option>
                </select>
              </td>
              <td class="num"><strong v-if="r.pv && r.pv.total">{{ money(r.pv.total) }}</strong><span v-else>-</span></td>
            </tr>
            <tr><td colspan="7" class="totalrow"><strong>{{ picked.length }} book(s) ticked · total to pay</strong></td><td class="num totalrow total-big">{{ money(total) }}</td></tr>
          </tbody>
        </table>
        <p class="muted small">Late: {{ rows[0]?.pv?.grace_days ?? 2 }} day(s) free, then Rs. {{ rows[0]?.pv?.fine_per_day ?? 2 }}/day · Damaged: {{ rows[0]?.pv?.damage_multiplier ?? 2 }}× price · Missing: {{ rows[0]?.pv?.lost_multiplier ?? 2 }}× price</p>
        <div class="ret-foot">
          <input v-model="notes" placeholder="Notes (optional)" />
          <button v-if="total > 0" class="btn primary big" :disabled="!picked.length || loading" @click="step = 'pay'">
            Next: pay {{ money(total) }} <ChevronRight :size="20" />
          </button>
          <button v-else class="btn success big" :disabled="!picked.length || busy || loading" @click="confirm(false)">
            <Check :size="20" /> Return {{ picked.length }} book(s)
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowUpRight, Banknote, BookOpen, Check, ChevronLeft, ChevronRight, IdCard, Printer, RotateCcw } from 'lucide-vue-next'
import ScanBox from '../components/ScanBox.vue'
import { api } from '../api'
import { toast } from '../store'
import { fmtDate, money, openPrint } from '../utils'

const scan = ref(null)
const st = ref(null) // the member and the books they have now
const rows = ref([]) // one per book: { loan, pick, damaged, pv (fine preview) }
const notes = ref('')
const error = ref('')
const holder = ref(null) // who has the book that was scanned on the Member step
const matches = ref([])
const step = ref('scan') // scan | check | pay | done
const done = ref(null)
const busy = ref(false)
const route = useRoute()

const picked = computed(() => rows.value.filter((r) => r.pick))
const total = computed(() => picked.value.reduce((s, r) => s + (r.pv?.total || 0), 0))
const loading = computed(() => picked.value.some((r) => !r.pv))
// The Pay step is part of this return only when something has to be paid: late, damaged or missing
const needsPay = computed(() => (step.value === 'done' ? (done.value?.total || 0) > 0 : total.value > 0))
const cardsBack = computed(() => (done.value?.items || []).length)
const firstLetter = (t) => ((t || '').replace(/^SAMPLE\s*-\s*/i, '').match(/\p{L}/u) || ['?'])[0].toUpperCase()
const receipts = computed(() => (done.value?.items || []).filter((r) => r.payment).map((r) => r.payment.id))

function why(r) {
  const parts = []
  if (r.pv.fee_due) parts.push('issue fee')
  if (r.pv.late_fine) parts.push(`${r.pv.late_days} day(s) late`)
  if (r.pv.damage_fine) parts.push('damaged')
  if (r.pv.lost_fine) parts.push('missing')
  return parts.join(' + ')
}

function clear() {
  st.value = null
  rows.value = []
  notes.value = ''
  error.value = ''
  holder.value = null
  matches.value = []
  done.value = null
  step.value = 'scan'
}

// Step 1: the member card (or a name / number). A book scanned here only points to who has it.
async function onMemberScan(code) {
  error.value = ''
  holder.value = null
  matches.value = []
  try {
    const r = await api.get('/circulation/scan', { code })
    if (r.type === 'member') return pickMember(r.member.id)
    const b = r.type === 'book' ? r.book : (r.books || []).find((x) => x.status === 'ISSUED')
    if (b && b.status === 'ISSUED' && b.borrower_id) {
      error.value = `That is a book ("${b.title}"). Please choose the member first.`
      holder.value = { id: b.borrower_id, name: b.borrower_name, membership_no: b.borrower_no }
    } else {
      error.value = 'That is a book, and it is not issued to anyone. Please scan the member card.'
    }
  } catch {
    const res = await api.get('/members', { q: code, size: 15 })
    if (res.items.length === 1) return pickMember(res.items[0].id)
    if (res.items.length) matches.value = res.items
    else error.value = `No member found for "${code}".`
  }
}

async function pickMember(id) {
  error.value = ''
  holder.value = null
  matches.value = []
  try {
    await loadMember(id)
  } catch (e) {
    error.value = e.message
  }
}

// The member's books show straight away. Nothing is ticked to start with: tick what is really handed back.
async function loadMember(id) {
  const s = await api.get(`/circulation/member-status/${id}`)
  st.value = s
  rows.value = s.loans.map((loan) => ({ loan, pick: s.loans.length === 1, cond: 'ok', pv: null }))
  step.value = 'check'
  rows.value.forEach(preview)
}

async function preview(r) {
  r.pv = null
  try {
    r.pv = await api.get('/circulation/return-preview', { acc_no: r.loan.book.acc_no, damaged: r.cond === 'damaged', lost: r.cond === 'lost' })
  } catch (e) {
    toast(e.message, 'error')
  }
}

function setAll(on) {
  rows.value.forEach((r) => { r.pick = on })
}

async function confirm(collect) {
  busy.value = true
  try {
    done.value = await api.post('/circulation/return-many', {
      items: picked.value.map((r) => ({ acc_no: r.loan.book.acc_no, damaged: r.cond === 'damaged', lost: r.cond === 'lost' })),
      notes: notes.value,
      collect_payment: collect,
    })
    step.value = 'done'
    toast(`${done.value.items.length} book(s) returned`)
    if (receipts.value.length) printReceipts()
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    busy.value = false
  }
}

function printReceipts() {
  openPrint('/print/receipt/' + receipts.value.join(','))
}

function next() {
  clear()
  scan.value?.focus()
}

// Opened from Issue book ("Return books first"): start with that member's books
onMounted(() => {
  if (route.query.member) pickMember(route.query.member)
})
</script>
