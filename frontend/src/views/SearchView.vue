<template>
  <div>
    <div class="page-head">
      <div>
        <h1>Search</h1>
        <p class="sub">Find a book and where it is, or find a member.</p>
      </div>
    </div>

    <div class="card">
      <ScanBox placeholder="Title, author, ISBN, Acc. No., keyword, member name or number"
        button-text="Search" keep @scan="run" />
      <div class="chips">
        <button class="chip" :class="{ on: !section }" @click="setSection('')">All sections</button>
        <button v-for="s in SECTIONS" :key="s" class="chip" :class="{ on: section === s }" @click="setSection(s)">{{ s }}</button>
      </div>
    </div>

    <p v-if="error" class="alert red">{{ error }}</p>

    <div v-if="searched && !books.length && !members.length" class="card empty">
      Nothing found for "{{ q }}". Try a shorter word or check the spelling.
    </div>

    <div v-if="members.length" class="card">
      <h2>Members ({{ members.length }})</h2>
      <div v-for="m in members" :key="m.id" class="result">
        <div>
          <h3><router-link :to="'/members/' + m.id">{{ m.name }}</router-link></h3>
          <div class="meta">{{ m.membership_no }} · {{ typeLabel(m.membership_type) }} · {{ m.telephone || 'no phone' }}</div>
          <div v-if="!m.is_active" class="badge gray mt">Not active</div>
          <div v-else-if="m.is_expired" class="badge red mt">Membership expired</div>
        </div>
        <div class="where" :class="m.borrowed_acc_nos ? 'orange' : 'gray'">
          <strong>{{ m.borrowed_acc_nos ? 'Has books now' : 'No books with this member' }}</strong>
          <span v-if="m.borrowed_acc_nos">Acc. No/s: {{ m.borrowed_acc_nos }}</span>
        </div>
      </div>
    </div>

    <div v-if="books.length" class="card">
      <div class="card-head">
        <h2>Books ({{ books.length }})</h2>
        <span class="badge green">{{ availableCount }} in the library now</span>
      </div>
      <div v-for="b in books" :key="b.id" class="result">
        <div>
          <h3><router-link :to="'/books/' + b.id">{{ b.title }}</router-link></h3>
          <div v-if="b.sinhala_title || b.tamil_title" class="meta">{{ [b.sinhala_title, b.tamil_title].filter(Boolean).join(' / ') }}</div>
          <div class="meta">
            {{ b.persons || 'Unknown author' }}<span v-if="b.year_of_publication"> · {{ b.year_of_publication }}</span>
          </div>
          <div class="meta">Acc. No. <strong>{{ b.acc_no }}</strong> · {{ b.section || 'No section' }}<span v-if="b.call_no"> · Call No. {{ b.call_no }}</span></div>
        </div>
        <div class="where" :class="where(b).cls">
          <strong>{{ where(b).title }}</strong>
          <span>{{ where(b).text }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import ScanBox from '../components/ScanBox.vue'
import { api } from '../api'
import { SECTIONS, typeLabel } from '../constants'
import { fmtDate } from '../utils'

const q = ref('')
const section = ref('')
const books = ref([])
const members = ref([])
const searched = ref(false)
const error = ref('')

const availableCount = computed(() => books.value.filter((b) => b.status === 'AVAILABLE').length)

async function run(text) {
  if (text !== undefined) q.value = text
  error.value = ''
  try {
    const r = await api.get('/search', { q: q.value, section: section.value })
    books.value = r.books
    members.value = r.members
    searched.value = true
  } catch (e) {
    error.value = e.message
  }
}

function setSection(s) {
  section.value = s
  if (q.value || s) run()
}

function where(b) {
  if (b.status === 'AVAILABLE') {
    return { cls: 'green', title: 'In the library', text: b.location ? `Look in ${b.location}${b.section ? ' (' + b.section + ')' : ''}` : `Section: ${b.section || 'not set'}` }
  }
  if (b.status === 'ISSUED') {
    const overdue = b.due_date && new Date(b.due_date + 'T23:59:59') < new Date()
    return {
      cls: 'orange',
      title: overdue ? `Overdue since ${fmtDate(b.due_date)}` : `You can get it after ${fmtDate(b.due_date)}`,
      text: `Now with ${b.borrower_name} (${b.borrower_no}), borrowed ${fmtDate(b.date_borrowed)}`,
    }
  }
  return { cls: 'gray', title: 'Not available', text: `Marked as ${b.status.toLowerCase()}` }
}
</script>
