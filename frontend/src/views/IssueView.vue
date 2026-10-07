<template>
  <div>
    <div class="page-head">
      <div>
        <h1>Issue book</h1>
        <p class="sub">Scan the member card first, then scan each book.</p>
      </div>
      <button v-if="status || result" class="btn" @click="reset"><RotateCcw :size="16" /> Start again</button>
    </div>

    <div class="steps">
      <div class="step" :class="{ on: !status && !result, done: status || result }"><b>1</b> Member</div>
      <div class="step" :class="{ on: status && !result, done: result }"><b>2</b> Books</div>
      <div class="step" :class="{ on: result }"><b>3</b> Done</div>
    </div>

    <!-- Step 3: finished -->
    <div v-if="result" class="card done-panel">
      <div class="ok"><Check :size="34" /></div>
      <h2>{{ result.loans.length }} book(s) issued to {{ status.member.name }}</h2>
      <p class="muted">Please tell the member to return the books on or before</p>
      <div class="due-big">{{ fmtDate(result.due_date) }}</div>
      <div class="table-wrap" style="max-width: 640px; margin: 0 auto 20px">
        <table class="table">
          <thead><tr><th>Acc. No.</th><th>Title</th></tr></thead>
          <tbody><tr v-for="l in result.loans" :key="l.id"><td>{{ l.book.acc_no }}</td><td>{{ l.book.title }}</td></tr></tbody>
        </table>
      </div>
      <button class="btn primary big" @click="reset">Issue to next member</button>
    </div>

    <!-- Step 1: member -->
    <div v-else-if="!status" class="card">
      <ScanBox label="Scan the member card" placeholder="Scan card, or type membership no. or name"
        hint="You can also type part of the member's name and press Enter." @scan="onMemberScan" />
      <p v-if="error" class="alert red">{{ error }}</p>
      <div v-if="matches.length" class="mt">
        <p class="muted">Choose the member:</p>
        <button v-for="m in matches" :key="m.id" class="pick" @click="loadMember(m.id)">
          <span><strong>{{ m.name }}</strong> <span class="muted">· {{ m.membership_no }} · {{ typeLabel(m.membership_type) }}</span></span>
          <span class="muted small">{{ m.school || m.telephone }}</span>
        </button>
      </div>
    </div>

    <!-- Step 2: books -->
    <div v-else class="grid-side">
      <div class="card">
        <div class="person">
          <img class="qr" :src="qrUrl(status.member.membership_no, 4)" alt="" />
          <div>
            <p class="big-name">{{ status.member.name }}</p>
            <div class="muted">{{ status.member.membership_no }}</div>
            <span class="badge blue">{{ typeLabel(status.member.membership_type) }}</span>
          </div>
        </div>
        <dl class="info mt">
          <dt>Telephone</dt><dd>{{ status.member.telephone || '-' }}</dd>
          <dt>Expiry date</dt><dd>{{ status.member.membership_type === 'LIFETIME' ? 'Life time' : fmtDate(status.member.expiry_date) }}</dd>
          <dt>Can take now</dt><dd>{{ status.can_borrow }} of {{ status.max_books }} book(s)</dd>
        </dl>
        <p v-for="b in status.blocks" :key="b" class="alert red">{{ b }}</p>
        <p v-for="w in status.warnings" :key="w" class="alert orange">{{ w }}</p>
        <div v-if="status.loans.length" class="mt">
          <h3>Books the member has now</h3>
          <div v-for="l in status.loans" :key="l.id" class="small" style="margin-bottom: 6px">
            {{ l.book.acc_no }} · {{ l.book.title }}<br />
            <span :class="l.is_overdue ? 'badge red' : 'muted'">Due {{ fmtDate(l.due_date) }}</span>
          </div>
        </div>
        <router-link :to="'/members/' + status.member.id" class="btn sm mt">Open profile</router-link>
      </div>

      <div class="card">
        <ScanBox ref="bookScan" label="Scan the book" placeholder="Scan the book QR / barcode or type Acc. No."
          button-text="Add" :disabled="blocked" @scan="onBookScan" />
        <p v-if="bookError" class="alert red">{{ bookError }}</p>

        <div v-if="choices.length" class="mt">
          <p class="muted">This ISBN has more than one copy. Choose the copy in your hand:</p>
          <button v-for="b in choices" :key="b.id" class="pick" :disabled="b.status !== 'AVAILABLE'" @click="addBook(b)">
            <span><strong>{{ b.acc_no }}</strong> · {{ b.title }}</span>
            <StatusBadge :status="b.status" />
          </button>
        </div>

        <h3 class="mt">Books to issue ({{ basket.length }})</h3>
        <div v-if="!basket.length" class="empty">No books yet. Scan a book to add it here.</div>
        <div v-else class="table-wrap">
          <table class="table">
            <thead><tr><th>Acc. No.</th><th>Title</th><th>Section</th><th></th></tr></thead>
            <tbody>
              <tr v-for="(b, i) in basket" :key="b.id">
                <td>{{ b.acc_no }}</td>
                <td>{{ b.title }}<div class="muted small">{{ b.persons }}</div></td>
                <td>{{ b.section }}</td>
                <td class="num"><button class="icon-btn" title="Remove" @click="basket.splice(i, 1)"><Trash2 :size="18" /></button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <button class="btn success big full mt" :disabled="!basket.length || blocked || busy" @click="confirmIssue">
          <Check :size="20" /> Issue {{ basket.length || '' }} book(s)
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { Check, RotateCcw, Trash2 } from 'lucide-vue-next'
import ScanBox from '../components/ScanBox.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api, qrUrl } from '../api'
import { appSettings, toast } from '../store'
import { typeLabel } from '../constants'
import { fmtDate } from '../utils'

const status = ref(null)
const basket = ref([])
const result = ref(null)
const error = ref('')
const bookError = ref('')
const matches = ref([])
const choices = ref([])
const busy = ref(false)
const bookScan = ref(null)

const blocked = computed(() => !!status.value?.blocks.length)
const nonLending = computed(() =>
  (appSettings.non_lending_sections || '').split(',').map((s) => s.trim().toLowerCase()).filter(Boolean))

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
  await nextTick()
  bookScan.value?.focus()
}

async function onBookScan(code) {
  bookError.value = ''
  choices.value = []
  try {
    const r = await api.get('/circulation/scan', { code })
    if (r.type === 'member') {
      bookError.value = 'That is a member card. Scan the book now, or press "Start again" to change the member.'
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
    toast('Books issued')
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    busy.value = false
  }
}

function reset() {
  status.value = null
  basket.value = []
  result.value = null
  error.value = ''
  bookError.value = ''
  matches.value = []
  choices.value = []
}
</script>
