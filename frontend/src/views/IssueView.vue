<template>
  <div class="flow-page">
    <!-- Title and steps stay at the top; only what is below them scrolls -->
    <div class="flow-top">
      <div class="page-head">
        <div>
          <h1>Issue book</h1>
          <p class="sub">Member → books → summary → payment. Several members can come together.</p>
        </div>
        <button v-if="members.length || result" class="btn" @click="reset"><RotateCcw :size="16" /> Start again</button>
      </div>

      <!-- The steps. A step already passed is a button: click it to go back and change something. -->
      <div class="steps">
        <component :is="step > i + 1 ? 'button' : 'div'" v-for="(name, i) in STEPS" :key="name" class="step"
                   :class="{ on: step === i + 1, done: step > i + 1, back: step > i + 1 }"
                   :title="step > i + 1 ? 'Go back to ' + name : null" @click="goStep(i + 1)"><b>{{ i + 1 }}</b> {{ name }}</component>
      </div>

      <!-- The members of this visit (family, friends...). Click one to see it; on the Books step, books go to the one highlighted. -->
      <div v-if="members.length && step <= 2" class="grp-bar">
        <span class="grp-label">{{ step === 1 ? 'In this visit' : 'Books go to' }}</span>
        <button v-for="(x, i) in members" :key="x.status.member.id" type="button" class="grp-chip"
                :class="{ on: i === cur, bad: x.status.blocks.length }" :title="x.status.blocks.join(' ') || 'Click to choose'" @click="pick(i)">
          <UserRound :size="15" />
          <strong>{{ x.status.member.name }}</strong>
          <span class="code-tag">{{ x.status.member.membership_no }}</span>
          <small v-if="x.status.blocks.length">cannot borrow</small>
          <small v-else>{{ x.basket.length }} / {{ x.status.can_borrow }}</small>
          <span class="grp-x" role="button" title="Remove from this visit" @click.stop="removeMember(i)"><X :size="14" /></span>
        </button>
        <span v-if="step === 2" class="muted small grp-tip">Scan a member card to switch</span>
      </div>
    </div>

    <!-- Step 1: the members. The search bar, and below it the member chosen. -->
    <div v-show="step === 1" class="card">
      <ScanBox ref="memberScan" :label="members.length ? 'Add another member (optional)' : 'Scan the member card'"
        placeholder="Scan card, or type name / member no." hint="Type to search, then pick." suggest="member"
        @scan="onMemberScan" @pick="(s) => { error = ''; loadMember(s.id) }" />
      <p v-if="error" class="alert red">{{ error }}</p>
      <div v-if="matches.length" class="mt">
        <p class="muted">Choose the member:</p>
        <button v-for="m in matches" :key="m.id" class="pick" @click="loadMember(m.id)">
          <span><strong>{{ m.name }}</strong> <span class="muted">· {{ m.membership_no }} · {{ typeLabel(m.membership_type) }}</span></span>
          <span class="muted small">{{ m.school || m.telephone }}</span>
        </button>
      </div>

      <!-- The member chosen: check it is the right person, then press Next -->
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
            <router-link v-if="!isGroup" :to="'/return?member=' + status.member.id" class="btn sm soft"><ArrowDownLeft :size="15" /> Return books first</router-link>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 2: only the books, for the member highlighted above. Same search bar as the member step. -->
    <div v-if="status" v-show="step === 2" class="card">
      <ScanBox ref="bookScan" :label="isGroup ? `Scan the book for ${status.member.name}` : 'Scan the book'"
        placeholder="Scan book, or type Acc. No. / title" hint="Type to search, then pick." button-text="Add" :disabled="blocked"
        suggest="book" @scan="onBookScan" @pick="(s) => onBookScan(s.code)" />
      <p v-if="bookError" class="alert red">{{ bookError }}</p>
      <p v-if="blocked" class="alert red">{{ status.member.name }} cannot borrow now: {{ status.blocks.join(' ') }}</p>

      <div v-if="choices.length" class="mt">
        <p class="muted">{{ choicesNote || 'Several copies. Pick the one in hand:' }}</p>
        <button v-for="b in choices" :key="b.id" class="pick" :disabled="b.status !== 'AVAILABLE'" @click="addBook(b)">
          <span><strong>{{ b.acc_no }}</strong> · {{ b.title }}</span>
          <StatusBadge :status="b.status" />
        </button>
      </div>

      <!-- The member's cards: books already borrowed, books being added now, and free places -->
      <div class="slots-head mt">
        <strong v-if="status.loans.length">{{ isGroup ? status.member.name + ': already' : 'Already' }} borrowed {{ status.loans.length }} book{{ status.loans.length === 1 ? '' : 's' }}</strong>
        <strong v-else>{{ isGroup ? status.member.name + ': no' : 'No' }} books borrowed now</strong>
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

      <!-- A group: what everyone is taking, at a glance -->
      <div v-if="isGroup" class="grp-sum">
        <span v-for="x in members" :key="x.status.member.id"><b>{{ x.status.member.name }}</b>
          {{ x.basket.length ? x.basket.map((b) => b.acc_no).join(', ') : 'no books' }}</span>
      </div>

      <p v-if="feeTotal > 0 && totalBooks" class="fee-line">
        Issue fee: <strong>{{ money(feeTotal) }}</strong>
        <span class="muted">&nbsp;· {{ isGroup ? totalBooks + ' book(s) for ' + members.filter((x) => x.basket.length).length + ' member(s)' : basket.length + ' × ' + money(status.issue_fee) }}
          · pay at next step<template v-if="unpaidAll > 0"> (+ {{ money(unpaidAll) }} earlier)</template></span>
      </p>
    </div>

    <!-- Step 3: what was issued -->
    <div v-if="result" v-show="step === 3" class="card issue-done">
      <div class="idone-head">
        <span class="idone-ok"><Check :size="26" /></span>
        <div>
          <h2>{{ result.loans.length }} book{{ result.loans.length === 1 ? '' : 's' }} issued</h2>
          <div class="muted">to {{ issuedTo }}</div>
        </div>
      </div>

      <!-- one member -->
      <template v-if="result.members.length === 1">
        <div class="idone-tiles four">
          <div class="idone-tile due">
            <CalendarClock :size="20" />
            <span><small>Return on or before</small><strong>{{ fmtDate(result.due_date) }}</strong><small>{{ daysText }}</small></span>
          </div>
          <div class="idone-tile cards">
            <IdCard :size="20" />
            <span><small>Take from the member</small><strong>{{ result.loans.length }} card{{ result.loans.length === 1 ? '' : 's' }}</strong>
              <small>They keep {{ res1.status.can_borrow }} of {{ res1.status.max_books }}</small></span>
          </div>
          <div class="idone-tile" :class="{ fee: result.fee_total > 0 }">
            <Banknote :size="20" />
            <span><small>Issue fee</small><strong>{{ money(result.fee_total) }}</strong>
              <small>{{ result.fee_total > 0 ? result.loans.length + ' × ' + money(res1.fee_per_book) : 'No fee' }}</small></span>
          </div>
          <div class="idone-tile">
            <BookOpen :size="20" />
            <span><small>Books with the member now</small><strong>{{ res1.status.loans.length }} of {{ res1.status.max_books }}</strong>
              <small>{{ res1.status.loans.length - result.loans.length ? (res1.status.loans.length - result.loans.length) + ' borrowed earlier' : 'all issued today' }}</small></span>
          </div>
        </div>

        <h3 class="idone-h">All books with the member now</h3>
        <div class="idone-books compact">
          <div v-for="l in res1.status.loans" :key="l.id" class="idone-book" :class="{ new: isNew(l), late: l.is_overdue }">
            <span class="code-tag">{{ l.book.acc_no }}</span>
            <strong :title="l.book.title">{{ l.book.title }}</strong>
            <span class="badge" :class="isNew(l) ? 'green' : l.is_overdue ? 'red' : 'gray'">{{ isNew(l) ? 'Issued today' : l.is_overdue ? 'Overdue' : 'Borrowed ' + fmtDate(l.issue_date) }}</span>
            <small>Due {{ fmtDate(l.due_date) }}</small>
          </div>
        </div>
      </template>

      <!-- a group: totals, then each member's books -->
      <template v-else>
        <div class="idone-tiles four">
          <div class="idone-tile due">
            <CalendarClock :size="20" />
            <span><small>Return on or before</small><strong>{{ fmtDate(result.due_date) }}</strong><small>{{ daysText }}</small></span>
          </div>
          <div class="idone-tile cards">
            <IdCard :size="20" />
            <span><small>Take from the members</small><strong>{{ result.loans.length }} cards</strong>
              <small>from {{ result.members.length }} members</small></span>
          </div>
          <div class="idone-tile" :class="{ fee: result.fee_total > 0 }">
            <Banknote :size="20" />
            <span><small>Issue fee (all together)</small><strong>{{ money(result.fee_total) }}</strong>
              <small>{{ result.fee_total > 0 ? 'paid on one receipt' : 'No fee' }}</small></span>
          </div>
          <div class="idone-tile">
            <Users :size="20" />
            <span><small>Members</small><strong>{{ result.members.length }}</strong>
              <small>{{ result.members.map((m) => m.status.member.membership_no).join(', ') }}</small></span>
          </div>
        </div>

        <template v-for="m in result.members" :key="m.member_id">
          <h3 class="idone-h grp-h"><UserRound :size="16" /> {{ m.status.member.name }} <span class="code-tag">{{ m.status.member.membership_no }}</span>
            <small class="muted">· {{ m.loans.length }} issued now · has {{ m.status.loans.length }} of {{ m.status.max_books }}
              <template v-if="m.fee_total > 0"> · fee {{ money(m.fee_total) }}</template></small></h3>
          <div class="idone-books compact">
            <div v-for="l in m.status.loans" :key="l.id" class="idone-book" :class="{ new: isNew(l), late: l.is_overdue }">
              <span class="code-tag">{{ l.book.acc_no }}</span>
              <strong :title="l.book.title">{{ l.book.title }}</strong>
              <span class="badge" :class="isNew(l) ? 'green' : l.is_overdue ? 'red' : 'gray'">{{ isNew(l) ? 'Issued today' : l.is_overdue ? 'Overdue' : 'Borrowed ' + fmtDate(l.issue_date) }}</span>
              <small>Due {{ fmtDate(l.due_date) }}</small>
            </div>
          </div>
        </template>
      </template>
    </div>

    <!-- Step 4: payment for the member(s). Kept in place while looking back at the summary, so its receipts stay listed. -->
    <PaymentPanel v-if="result && openedPay" v-show="step === 4" ref="pay" :member-ids="payIds" flow />

    <!-- Always at the bottom of the screen: Back, where you are, and the next thing to do -->
    <div class="flow-bar">
      <button class="btn big" :disabled="step === 1 || busy" @click="goStep(step - 1)"><ChevronLeft :size="20" /> Back</button>
      <div class="flow-bar-mid">
        <strong>Step {{ step }} of 4 · {{ STEPS[step - 1] }}</strong>
        <small>{{ barNote }}</small>
      </div>
      <button v-if="step === 1" class="btn primary big" :disabled="!canGoBooks" @click="goBooks">Next: books <ChevronRight :size="20" /></button>
      <button v-else-if="step === 2" class="btn success big" :disabled="!totalBooks || busy" @click="confirmIssue">
        <Check :size="20" /> Issue {{ totalBooks || '' }} book(s)
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
  ArrowDownLeft, Banknote, BookOpen, CalendarClock, Check, ChevronLeft, ChevronRight, IdCard, Phone, Printer, RotateCcw, UserRound, Users, X,
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
// The members of this visit: usually one, sometimes a family or friends together.
// Each has their own status (books now, limit, what they owe) and their own books chosen now.
const members = ref([]) // [{ status, basket: [] }]
const cur = ref(0) // the member shown / getting the books scanned now
const status = computed(() => members.value[cur.value]?.status || null)
const basket = computed(() => members.value[cur.value]?.basket || [])
const isGroup = computed(() => members.value.length > 1)
const result = ref(null) // the issue, once saved: { due_date, ref, fee_total, members: [...], loans: [...all] }
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
const unpaidAll = computed(() => members.value.reduce((t, x) => t + x.status.fines.reduce((s, l) => s + l.balance, 0), 0))
const blocked = computed(() => !!status.value?.blocks.length)
const totalBooks = computed(() => members.value.reduce((t, x) => t + x.basket.length, 0))
const feeTotal = computed(() => members.value.reduce((t, x) => t + x.basket.length * (x.status.issue_fee || 0), 0))
// The member step can be left when at least one member may borrow
const canGoBooks = computed(() => members.value.some((x) => !x.status.blocks.length))
const payDue = computed(() => pay.value?.unpaid || 0)
const nonLending = computed(() =>
  (appSettings.non_lending_sections || '').split(',').map((s) => s.trim().toLowerCase()).filter(Boolean))
const res1 = computed(() => result.value?.members[0])
const issuedTo = computed(() => {
  const ms = result.value?.members || []
  if (ms.length === 1) return `${ms[0].status.member.name} · ${ms[0].status.member.membership_no}`
  return `${ms.length} members: ${ms.map((m) => m.status.member.name).join(', ')}`
})
// Paying together: everyone who got books, and anyone in the visit who still owes from earlier
const payIds = computed(() => members.value
  .filter((x) => x.basket.length || x.status.fines.length || result.value?.members.some((m) => m.member_id === x.status.member.id))
  .map((x) => x.status.member.id))
const barNote = computed(() => {
  const n = members.value.length
  if (step.value === 1) {
    if (!n) return 'Scan or find the member'
    if (n > 1) return `${n} members · scan another card to add more`
    if (blocked.value) return 'This member cannot borrow now'
    return status.value.member.name
  }
  const who = n > 1 ? `${n} members` : `${status.value.member.name} · ${status.value.member.membership_no}`
  if (step.value === 2) return totalBooks.value ? `${who} · ${totalBooks.value} book(s) chosen` : `${who} · scan the books`
  if (step.value === 3) return `${who} · ${result.value.loans.length} book(s) issued`
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
  if (blocked.value) cur.value = members.value.findIndex((x) => !x.status.blocks.length)
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
    // the books are already issued: changing the members or the books means taking that issue back first
    undoTo = n
    askUndo.value = true
  } else {
    step.value = n // the members and the books chosen so far stay as they are
    if (n === 1) nextTick(() => memberScan.value?.focus())
  }
}

async function undoIssue() {
  busy.value = true
  try {
    await api.post('/circulation/cancel-issue', { loan_ids: result.value.loans.map((l) => l.id) })
    await refreshAll()
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

// ---- the members of the visit ----
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

// Add a member to the visit (or, if already in it, choose them)
async function loadMember(id) {
  matches.value = []
  const st = await api.get(`/circulation/member-status/${id}`)
  const at = members.value.findIndex((x) => x.status.member.id === st.member.id)
  if (at >= 0) {
    members.value[at].status = st
    cur.value = at
  } else {
    members.value.push({ status: st, basket: [] })
    cur.value = members.value.length - 1
  }
}

function pick(i) {
  cur.value = i
  bookError.value = ''
  choices.value = []
  if (step.value === 2) nextTick(() => bookScan.value?.focus())
}

function removeMember(i) {
  members.value.splice(i, 1)
  if (cur.value >= members.value.length) cur.value = Math.max(0, members.value.length - 1)
  if (!members.value.length && step.value === 2) step.value = 1
}

async function refreshAll() {
  for (const x of members.value) x.status = await api.get(`/circulation/member-status/${x.status.member.id}`)
}

// ---- step 2: books (for the member highlighted) ----
async function onBookScan(code) {
  bookError.value = ''
  choices.value = []
  choicesNote.value = ''
  try {
    const r = await api.get('/circulation/scan', { code, prefer: 'book' })
    if (r.type === 'member') {
      // a member card on the Books step: switch to that member (and add them to the visit if new)
      await loadMember(r.member.id)
      toast(`Now adding books for ${status.value.member.name}`)
      bookScan.value?.focus()
    } else if (r.type === 'isbn') {
      const free = r.books.filter((b) => b.status === 'AVAILABLE' && !inBaskets(b))
      if (free.length === 1) addBook(free[0])
      else choices.value = r.books
    } else {
      addBook(r.book)
    }
  } catch (e) {
    bookError.value = e.message
  }
}

// the member in this visit who already has this book in their list
const inBaskets = (b) => members.value.find((x) => x.basket.some((y) => y.id === b.id))

function addBook(b) {
  choices.value = []
  choicesNote.value = ''
  const owner = inBaskets(b)
  if (owner) {
    bookError.value = `"${b.title}" is already in the list` + (isGroup.value ? ` of ${owner.status.member.name}.` : '.')
  } else if (b.status === 'ISSUED') {
    bookError.value = `"${b.title}" (Acc. ${b.acc_no}) is already issued to ${b.borrower_name} (${b.borrower_no}).`
    otherCopies(b)
  } else if (b.status !== 'AVAILABLE') {
    bookError.value = `"${b.title}" (Acc. ${b.acc_no}) cannot be issued. It is marked as ${b.status.toLowerCase()}.`
    otherCopies(b)
  } else if (nonLending.value.includes((b.section || '').toLowerCase())) {
    bookError.value = `"${b.title}" is a ${b.section} book. It can be read only inside the library.`
  } else if (basket.value.length >= status.value.can_borrow) {
    bookError.value = `${status.value.member.name} can take only ${status.value.can_borrow} more book(s).`
  } else {
    basket.value.push(b)
  }
  bookScan.value?.focus()
}

// The copy picked is not free: show the other copies of the same book that are in the library
const choicesNote = ref('')
async function otherCopies(b) {
  try {
    const r = await api.get(`/books/${b.id}/copies`)
    const free = r.items.filter((c) => c.status === 'AVAILABLE' && !inBaskets(c))
    if (free.length) {
      choicesNote.value = `Another copy of this book is in the library (${free.length} of ${r.total}). Pick the one in hand:`
      choices.value = free
    }
  } catch { /* no other copies */ }
}

async function confirmIssue() {
  busy.value = true
  try {
    // everyone's books at once, under one reference: either all are issued or none
    const items = members.value.filter((x) => x.basket.length)
      .map((x) => ({ member_id: x.status.member.id, acc_nos: x.basket.map((b) => b.acc_no) }))
    const r = await api.post('/circulation/issue-group', { items })
    for (const m of r.members) {
      const x = members.value.find((y) => y.status.member.id === m.member_id)
      if (x) x.status = m.status
    }
    result.value = { ...r, loans: r.members.flatMap((m) => m.loans) }
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
  members.value = []
  cur.value = 0
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
