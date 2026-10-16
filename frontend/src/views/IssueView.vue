<template>
  <div class="flow-page">
    <!-- Title and steps stay at the top; only what is below them scrolls -->
    <div class="flow-top">
      <div class="page-head">
        <div>
          <h1>Issue book</h1>
          <p class="sub">Member → books → summary → payment.</p>
        </div>
        <button v-if="status || result" class="btn" @click="reset"><RotateCcw :size="16" /> Start again</button>
      </div>

      <!-- The steps. A step already passed is a button: click it to go back and change something. -->
      <div class="steps">
        <component :is="step > i + 1 ? 'button' : 'div'" v-for="(name, i) in STEPS" :key="name" class="step"
                   :class="{ on: step === i + 1, done: step > i + 1, back: step > i + 1 }"
                   :title="step > i + 1 ? 'Go back to ' + name : null" @click="goStep(i + 1)"><b>{{ i + 1 }}</b> {{ name }}</component>
      </div>
    </div>

    <!-- Step 1: the member. The search bar, and below it who was found. -->
    <div v-show="step === 1" class="card">
      <ScanBox ref="memberScan" label="Scan the member card" placeholder="Scan card, or type name / member no."
        hint="Type to search, then pick." suggest="member"
        @scan="onMemberScan" @pick="(s) => { error = ''; loadMember(s.id) }" />
      <p v-if="error" class="alert red">{{ error }}</p>
      <div v-if="matches.length" class="mt">
        <p class="muted">Choose the member:</p>
        <button v-for="m in matches" :key="m.id" class="pick" @click="loadMember(m.id)">
          <span><strong>{{ m.name }}</strong> <span class="muted">· {{ m.membership_no }} · {{ typeLabel(m.membership_type) }}</span></span>
          <span class="muted small">{{ m.school || m.telephone }}</span>
        </button>
      </div>

      <!-- Who was found: check it is the right person, then press Next -->
      <div v-if="status" class="mem-sum">
        <MemberPhoto :src="status.member.photo_url" :name="status.member.name" size="lg" />
        <div class="mem-sum-main">
          <div class="mem-sum-name">
            <h2>{{ status.member.name }}</h2>
            <span class="ph-no"><small>Membership No.</small><strong>{{ status.member.membership_no }}</strong></span>
          </div>
          <div class="mem-sum-tiles">
            <div class="mem-tile"><IdCard :size="18" /><span><small>Membership type</small><strong>{{ typeLabel(status.member.membership_type) }}</strong></span></div>
            <div class="mem-tile" :class="{ bad: status.member.is_expired }"><CalendarClock :size="18" /><span><small>Expiry date</small>
              <strong>{{ status.member.membership_type === 'LIFETIME' ? 'Life time' : status.member.expiry_date ? fmtDate(status.member.expiry_date) : 'Not set' }}</strong></span></div>
            <div class="mem-tile"><Phone :size="18" /><span><small>Telephone</small><strong>{{ status.member.telephone || '-' }}</strong></span></div>
            <div class="mem-tile" :class="{ bad: !status.can_borrow }"><BookOpen :size="18" /><span><small>Can take now</small>
              <strong>{{ status.can_borrow }} of {{ status.max_books }} book(s)</strong></span></div>
          </div>
          <p v-for="b in status.blocks" :key="b" class="alert red">{{ b }}</p>
          <p v-if="unpaid > 0" class="alert blue">
            <strong>Unpaid earlier: {{ money(unpaid) }}</strong> ({{ status.fines.map((l) => l.book.acc_no).join(', ') }}).
            Added to this payment.
          </p>
          <p v-for="w in status.warnings.filter((x) => !x.startsWith('Unpaid'))" :key="w" class="alert orange">{{ w }}</p>
          <div v-if="status.loans.length" class="mem-sum-books">
            <small>Has now:</small>
            <span v-for="l in status.loans" :key="l.id" class="mem-book" :class="{ late: l.is_overdue }" :title="l.book.title">
              <span class="code-tag">{{ l.book.acc_no }}</span> {{ l.book.title }} · due {{ fmtDate(l.due_date) }}
            </span>
            <router-link :to="'/return?member=' + status.member.id" class="btn sm soft"><ArrowDownLeft :size="15" /> Return books first</router-link>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 2: only the books. Same search bar as the member step. -->
    <div v-if="status" v-show="step === 2" class="card">
      <ScanBox ref="bookScan" label="Scan the book" placeholder="Scan book, or type Acc. No. / title"
        hint="Type to search, then pick." button-text="Add" :disabled="blocked"
        suggest="book" @scan="onBookScan" @pick="(s) => onBookScan(s.code)" />
      <p v-if="bookError" class="alert red">{{ bookError }}</p>

      <div v-if="choices.length" class="mt">
        <p class="muted">Several copies. Pick the one in hand:</p>
        <button v-for="b in choices" :key="b.id" class="pick" :disabled="b.status !== 'AVAILABLE'" @click="addBook(b)">
          <span><strong>{{ b.acc_no }}</strong> · {{ b.title }}</span>
          <StatusBadge :status="b.status" />
        </button>
      </div>

      <!-- The member's cards: books already borrowed, books being added now, and free places -->
      <div class="slots-head mt">
        <strong v-if="status.loans.length">Already borrowed {{ status.loans.length }} book{{ status.loans.length === 1 ? '' : 's' }}</strong>
        <strong v-else>No books borrowed now</strong>
        <span class="muted">&nbsp;· can take {{ Math.max(0, status.can_borrow - basket.length) }} more (limit {{ status.max_books }})</span>
      </div>
      <div class="slots">
        <div v-for="l in status.loans" :key="'l' + l.id" class="slot taken" :class="{ late: l.is_overdue }" :title="l.book.title">
          <small>{{ l.is_overdue ? 'Overdue' : 'Borrowed' }} · {{ fmtDate(l.issue_date) }}</small>
          <strong><span class="code-tag">{{ l.book.acc_no }}</span> {{ l.book.title }}</strong>
          <small>Due {{ fmtDate(l.due_date) }}</small>
        </div>
        <div v-for="(b, i) in basket" :key="'b' + b.id" class="slot new" :title="b.title">
          <small>Now · being issued <button class="slot-x" title="Remove this book" @click="basket.splice(i, 1)"><X :size="14" /></button></small>
          <strong><span class="code-tag">{{ b.acc_no }}</span> {{ b.title }}</strong>
          <small>{{ b.persons || b.section }}</small>
        </div>
        <div v-for="n in Math.max(0, status.can_borrow - basket.length)" :key="'f' + n" class="slot free">
          <small>Free</small>
          <strong>Scan a book</strong>
        </div>
      </div>

      <p v-if="status.issue_fee > 0 && basket.length" class="fee-line">
        Issue fee: {{ basket.length }} × {{ money(status.issue_fee) }} = <strong>{{ money(basket.length * status.issue_fee) }}</strong>
        <span class="muted">&nbsp;({{ typeLabel(status.member.membership_type) }}) · pay at next step<template v-if="unpaid > 0"> (+ {{ money(unpaid) }} earlier)</template></span>
      </p>
    </div>

    <!-- Step 3: what was issued -->
    <div v-if="result" v-show="step === 3" class="card issue-done">
      <div class="idone-head">
        <span class="idone-ok"><Check :size="26" /></span>
        <div>
          <h2>{{ result.loans.length }} book{{ result.loans.length === 1 ? '' : 's' }} issued</h2>
          <div class="muted">to {{ status.member.name }} · {{ status.member.membership_no }}</div>
        </div>
      </div>

      <div class="idone-tiles four">
        <div class="idone-tile due">
          <CalendarClock :size="20" />
          <span><small>Return on or before</small><strong>{{ fmtDate(result.due_date) }}</strong><small>{{ daysText }}</small></span>
        </div>
        <div class="idone-tile cards">
          <IdCard :size="20" />
          <span><small>Take from the member</small><strong>{{ result.loans.length }} card{{ result.loans.length === 1 ? '' : 's' }}</strong>
            <small>They keep {{ result.status.can_borrow }} of {{ result.status.max_books }}</small></span>
        </div>
        <div class="idone-tile" :class="{ fee: result.fee_total > 0 }">
          <Banknote :size="20" />
          <span><small>Issue fee</small><strong>{{ money(result.fee_total) }}</strong>
            <small>{{ result.fee_total > 0 ? result.loans.length + ' × ' + money(result.fee_per_book) : 'No fee' }}</small></span>
        </div>
        <div class="idone-tile">
          <BookOpen :size="20" />
          <span><small>Books with the member now</small><strong>{{ result.status.loans.length }} of {{ result.status.max_books }}</strong>
            <small>{{ result.status.loans.length - result.loans.length ? (result.status.loans.length - result.loans.length) + ' borrowed earlier' : 'all issued today' }}</small></span>
        </div>
      </div>

      <h3 class="idone-h">All books with the member now</h3>
      <div class="idone-books compact">
        <div v-for="l in result.status.loans" :key="l.id" class="idone-book" :class="{ new: isNew(l), late: l.is_overdue }">
          <span class="code-tag">{{ l.book.acc_no }}</span>
          <strong :title="l.book.title">{{ l.book.title }}</strong>
          <span class="badge" :class="isNew(l) ? 'green' : l.is_overdue ? 'red' : 'gray'">{{ isNew(l) ? 'Issued today' : l.is_overdue ? 'Overdue' : 'Borrowed ' + fmtDate(l.issue_date) }}</span>
          <small>Due {{ fmtDate(l.due_date) }}</small>
        </div>
      </div>
    </div>

    <!-- Step 4: payment for this member. Kept in place while looking back at the summary, so its receipts stay listed. -->
    <PaymentPanel v-if="result && openedPay" v-show="step === 4" ref="pay" :member-id="status.member.id" flow />

    <!-- Always at the bottom of the screen: Back, where you are, and the next thing to do -->
    <div class="flow-bar">
      <button class="btn big" :disabled="step === 1 || busy" @click="goStep(step - 1)"><ChevronLeft :size="20" /> Back</button>
      <div class="flow-bar-mid">
        <strong>Step {{ step }} of 4 · {{ STEPS[step - 1] }}</strong>
        <small>{{ barNote }}</small>
      </div>
      <button v-if="step === 1" class="btn primary big" :disabled="!canGoBooks" @click="goBooks">Next: books <ChevronRight :size="20" /></button>
      <button v-else-if="step === 2" class="btn success big" :disabled="!basket.length || blocked || busy" @click="confirmIssue">
        <Check :size="20" /> Issue {{ basket.length || '' }} book(s)
      </button>
      <button v-else-if="step === 3" class="btn primary big" @click="openPay"><Banknote :size="20" /> Next: payment <ChevronRight :size="20" /></button>
      <button v-else-if="payDue > 0" class="btn success big" :disabled="pay?.busy" @click="pay.collectAll()">
        <Printer :size="20" /> Collect {{ money(payDue) }}
      </button>
      <button v-else class="btn primary big" :disabled="!pay?.loaded" @click="reset"><Check :size="20" /> Done · next member</button>
    </div>

    <!-- Going back after the books were issued takes the issue back -->
    <Modal v-if="askUndo" title="Go back and change the books?" @close="askUndo = false">
      <p style="margin: 0">The {{ result.loans.length }} book(s) just issued will be taken back, so you can change them.
        Nothing has been paid for them yet. Then press Issue again.</p>
      <template #footer>
        <button class="btn" @click="askUndo = false">Stay here</button>
        <button class="btn primary" :disabled="busy" @click="undoIssue"><ChevronLeft :size="16" /> Yes, change the books</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  ArrowDownLeft, Banknote, BookOpen, CalendarClock, Check, ChevronLeft, ChevronRight, IdCard, Phone, Printer, RotateCcw, X,
} from 'lucide-vue-next'
import MemberPhoto from '../components/MemberPhoto.vue'
import Modal from '../components/Modal.vue'
import PaymentPanel from '../components/PaymentPanel.vue'
import ScanBox from '../components/ScanBox.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api } from '../api'
import { appSettings, toast } from '../store'
import { typeLabel } from '../constants'
import { fmtDate, money } from '../utils'

const STEPS = ['Member', 'Books', 'Issued', 'Payment']
const route = useRoute()
const step = ref(1)
const status = ref(null) // the member found, with their books now and what they owe
const basket = ref([]) // books chosen to issue
const result = ref(null) // the issue, once saved
const error = ref('')
const bookError = ref('')
const matches = ref([])
const choices = ref([])
const busy = ref(false)
const memberScan = ref(null)
const bookScan = ref(null)
const pay = ref(null) // the Payment step (it tells this page what is owed)
const openedPay = ref(false)
const askUndo = ref(false)

const unpaid = computed(() => (status.value?.fines || []).reduce((s, l) => s + l.balance, 0))
const blocked = computed(() => !!status.value?.blocks.length)
// The member step can be left when a member is found, may borrow, and owes nothing
const canGoBooks = computed(() => !!status.value && !blocked.value)
const payDue = computed(() => pay.value?.unpaid || 0)
const nonLending = computed(() =>
  (appSettings.non_lending_sections || '').split(',').map((s) => s.trim().toLowerCase()).filter(Boolean))
const barNote = computed(() => {
  if (step.value === 1) {
    if (!status.value) return 'Scan or find the member'
    if (blocked.value) return 'This member cannot borrow now'
    return status.value.member.name
  }
  const who = `${status.value.member.name} · ${status.value.member.membership_no}`
  if (step.value === 2) return basket.value.length ? `${who} · ${basket.value.length} book(s) chosen` : `${who} · scan the books`
  if (step.value === 3) return `${who} · ${result.loans.length} book(s) issued`
  return payDue.value > 0 ? `${who} · everything is paid together` : `${who} · nothing left to pay`
})

// Summary screen: books issued in this visit, and how long until they are due
const isNew = (l) => result.value?.loans.some((x) => x.id === l.id)
const daysText = computed(() => {
  if (!result.value) return ''
  const days = Math.round((new Date(result.value.due_date + 'T00:00:00') - new Date(new Date().toDateString())) / 86400000)
  return `${days} day${days === 1 ? '' : 's'} from today`
})

// ---- moving between the steps ----
async function goBooks() {
  if (!canGoBooks.value) return
  step.value = 2
  await nextTick()
  bookScan.value?.focus()
}

function openPay() {
  openedPay.value = true
  step.value = 4
}

// Back, or a click on a step already passed
let undoTo = 2
function goStep(n) {
  if (n < 1 || n >= step.value || busy.value) return
  if (step.value === 4 && n === 3) {
    step.value = 3
  } else if (step.value >= 3) {
    // the books are already issued: changing the member or the books means taking that issue back first
    undoTo = n
    askUndo.value = true
  } else {
    step.value = n // the member and the books chosen so far stay as they are
    if (n === 1) nextTick(() => memberScan.value?.focus())
  }
}

async function undoIssue() {
  busy.value = true
  try {
    status.value = await api.post('/circulation/cancel-issue', { loan_ids: result.value.loans.map((l) => l.id) })
    result.value = null
    openedPay.value = false
    askUndo.value = false
    step.value = undoTo
    toast('Issue taken back. Change the books and issue again.')
    await nextTick()
    ;(undoTo === 1 ? memberScan : bookScan).value?.focus()
  } catch (e) {
    askUndo.value = false
    toast(e.message, 'error')
  } finally {
    busy.value = false
  }
}

// ---- step 1: member ----
async function onMemberScan(code) {
  error.value = ''
  matches.value = []
  try {
    const r = await api.get('/circulation/scan', { code })
    if (r.type === 'member') return loadMember(r.member.id)
    error.value = 'That is a book. Please scan the member card first.'
  } catch (e) {
    const res = await api.get('/members', { q: code, size: 15 })
    if (res.items.length === 1) return loadMember(res.items[0].id)
    if (res.items.length) matches.value = res.items
    else error.value = `No member found for "${code}".`
  }
}

async function loadMember(id) {
  matches.value = []
  status.value = await api.get(`/circulation/member-status/${id}`)
  // another member chosen with books already in the list: keep only as many as this member can take
  if (basket.value.length > status.value.can_borrow) {
    basket.value = basket.value.slice(0, status.value.can_borrow)
    bookError.value = `This member can take only ${status.value.can_borrow} book(s), so the list was shortened.`
  }
}

// ---- step 2: books ----
async function onBookScan(code) {
  bookError.value = ''
  choices.value = []
  try {
    const r = await api.get('/circulation/scan', { code, prefer: 'book' })
    if (r.type === 'member') {
      bookError.value = 'That is a member card. Scan the book now, or press Back to change the member.'
    } else if (r.type === 'isbn') {
      const free = r.books.filter((b) => b.status === 'AVAILABLE' && !basket.value.some((x) => x.id === b.id))
      if (free.length === 1) addBook(free[0])
      else choices.value = r.books
    } else {
      addBook(r.book)
    }
  } catch (e) {
    bookError.value = e.message
  }
}

function addBook(b) {
  choices.value = []
  if (basket.value.some((x) => x.id === b.id)) {
    bookError.value = `"${b.title}" is already in the list.`
  } else if (b.status === 'ISSUED') {
    bookError.value = `"${b.title}" is already issued to ${b.borrower_name} (${b.borrower_no}).`
  } else if (b.status !== 'AVAILABLE') {
    bookError.value = `"${b.title}" cannot be issued. It is marked as ${b.status.toLowerCase()}.`
  } else if (nonLending.value.includes((b.section || '').toLowerCase())) {
    bookError.value = `"${b.title}" is a ${b.section} book. It can be read only inside the library.`
  } else if (basket.value.length >= status.value.can_borrow) {
    bookError.value = `This member can take only ${status.value.can_borrow} more book(s).`
  } else {
    basket.value.push(b)
  }
  bookScan.value?.focus()
}

async function confirmIssue() {
  busy.value = true
  try {
    result.value = await api.post('/circulation/issue', {
      member_id: status.value.member.id,
      acc_nos: basket.value.map((b) => b.acc_no),
    })
    step.value = 3
    toast('Books issued')
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    busy.value = false
  }
}

function reset() {
  step.value = 1
  openedPay.value = false
  askUndo.value = false
  status.value = null
  basket.value = []
  result.value = null
  error.value = ''
  bookError.value = ''
  matches.value = []
  choices.value = []
  nextTick(() => memberScan.value?.focus())
}

// The height of the title + steps, so parts of a step can stick just below them
let topObserver
onMounted(() => {
  const el = document.querySelector('.flow-top')
  if (!el) return
  topObserver = new ResizeObserver(() => el.parentElement.style.setProperty('--flow-top-h', el.offsetHeight + 'px'))
  topObserver.observe(el)
})
onBeforeUnmount(() => topObserver?.disconnect())

// Opened from Return book or Payment ("Issue books to this member"): that member is already found
onMounted(async () => {
  if (route.query.member) {
    await loadMember(route.query.member)
    goBooks()
  }
})
</script>
