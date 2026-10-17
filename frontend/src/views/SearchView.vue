<template>
  <div>
    <div class="page-head">
      <div>
        <h1>Search</h1>
        <p class="sub">Books and members.</p>
      </div>
    </div>

    <div class="card">
      <ScanBox placeholder="Title, author, Acc. No., ISBN, member name or no."
        keep live @scan="run" @type="onType" />
      <div class="chips">
        <button class="chip" :class="{ on: !section }" @click="setSection('')">All sections</button>
        <button v-for="s in SECTIONS" :key="s" class="chip" :class="{ on: section === s }" @click="setSection(s)">{{ s }}</button>
      </div>
    </div>

    <p v-if="error" class="alert red">{{ error }}</p>

    <div v-if="searched && q && !books.length && !members.length" class="card empty">
      Nothing found for "{{ q }}". Try a shorter word or check the spelling.
    </div>

    <div v-if="members.length" class="card">
      <h2>Members ({{ members.length }})</h2>
      <div v-for="m in members" :key="m.id" class="result">
        <div class="result-book">
          <router-link :to="'/members/' + m.id" tabindex="-1"><MemberPhoto :src="m.photo_url" :name="m.name" size="sm" /></router-link>
          <div>
          <h3><router-link :to="'/members/' + m.id">{{ m.name }}</router-link></h3>
          <div class="meta">{{ m.membership_no }} · {{ typeLabel(m.membership_type) }} · {{ m.telephone || 'no phone' }}</div>
          <div v-if="!m.is_active" class="badge gray mt">Not active</div>
          <div v-else-if="m.is_expired" class="badge red mt">Membership expired</div>
          </div>
        </div>
        <div class="where" :class="m.borrowed_acc_nos ? 'orange' : 'gray'">
          <strong>{{ m.borrowed_acc_nos ? 'Has books now' : 'No books with this member' }}</strong>
          <span v-if="m.borrowed_acc_nos">Acc. No/s: {{ m.borrowed_acc_nos }}</span>
        </div>
      </div>
    </div>

    <!-- One result per book: copies of the same book together, with how many are in the library -->
    <div v-if="books.length" class="card">
      <div class="card-head">
        <h2>Books ({{ titles.length }})</h2>
        <span class="badge green">{{ titles.filter((t) => t.inLib).length }} with a copy in the library now</span>
      </div>
      <div v-for="t in titles" :key="t.key" class="result">
        <div class="result-book">
          <router-link :to="'/books/' + t.b.id" tabindex="-1"><BookCover :src="t.b.cover_url" :title="t.b.title" size="sm" /></router-link>
          <div>
          <h3><router-link :to="'/books/' + t.b.id">{{ t.b.title }}</router-link></h3>
          <div v-if="t.b.sinhala_title || t.b.tamil_title" class="meta">{{ [t.b.sinhala_title, t.b.tamil_title].filter(Boolean).join(' / ') }}</div>
          <div class="meta">
            {{ t.b.persons || 'Unknown author' }}<span v-if="t.b.year_of_publication"> · {{ t.b.year_of_publication }}</span>
            · {{ t.b.section || 'No section' }}<span v-if="t.b.call_no"> · Call No. {{ t.b.call_no }}</span>
          </div>
          <div class="meta copy-accs">
            <span class="copy-n">{{ t.total }} cop{{ t.total === 1 ? 'y' : 'ies' }}:</span>
            <router-link v-for="c in t.list.slice(0, 8)" :key="c.id" :to="'/books/' + c.id" class="acc-chip" :class="accCls(c)"
                         :title="c.status === 'ISSUED' ? `With ${c.borrower_name}, due ${fmtDate(c.due_date)}` : statusText(c)">{{ c.acc_no }}</router-link>
            <span v-if="t.list.length > 8" class="muted">+{{ t.list.length - 8 }}</span>
          </div>
          </div>
        </div>
        <div class="where" :class="where(t).cls">
          <strong>{{ where(t).title }}</strong>
          <span>{{ where(t).text }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import BookCover from '../components/BookCover.vue'
import MemberPhoto from '../components/MemberPhoto.vue'
import ScanBox from '../components/ScanBox.vue'
import { api } from '../api'
import { SECTIONS, typeLabel } from '../constants'
import { fmtDate } from '../utils'
import { latestOnly, useLiveSearch } from '../liveSearch'

const q = ref('')
const section = ref('')
const books = ref([])
const members = ref([])
const searched = ref(false)
const error = ref('')

// Copies of the same book together: one result per book
const titles = computed(() => {
  const by = new Map()
  for (const b of books.value) {
    const k = b.title_id || b.id
    if (!by.has(k)) by.set(k, { key: k, b, list: [] })
    by.get(k).list.push(b)
  }
  return [...by.values()].map((t) => {
    // the copy shown first: one in the library if there is one
    const first = t.list.find((c) => c.status === 'AVAILABLE') || t.list[0]
    return { ...t, b: first, total: Math.max(first.copies || 0, t.list.length), inLib: first.copies_in || t.list.filter((c) => c.status === 'AVAILABLE').length }
  })
})
const accCls = (c) => (c.status === 'AVAILABLE' ? 'in' : c.status === 'ISSUED' ? 'out' : 'off')
const statusText = (c) => (c.status === 'AVAILABLE' ? `In the library${c.location ? ', ' + c.location : ''}` : `Marked as ${c.status.toLowerCase()}`)

const fetchResults = latestOnly((params) => api.get('/search', params))
// Results update while typing (a moment after the last key); Enter or a scanned code searches at once.
const live = useLiveSearch(() => run())
function onType(text) {
  q.value = text
  live.soon()
}

async function run(text) {
  if (text !== undefined) q.value = text
  error.value = ''
  if (!q.value.trim() && !section.value) {
    books.value = []
    members.value = []
    searched.value = false
    return
  }
  try {
    const r = await fetchResults({ q: q.value, section: section.value })
    if (!r) return // a newer search has already answered
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

// Can the member get this book now? Where is a free copy, or when is the first one back?
function where(t) {
  const free = t.list.filter((c) => c.status === 'AVAILABLE')
  const out = t.list.filter((c) => c.status === 'ISSUED').sort((x, y) => (x.due_date < y.due_date ? -1 : 1))
  if (t.inLib > 0) {
    const c = free[0]
    const place = c?.location ? `Look in ${c.location}${c.section ? ' (' + c.section + ')' : ''}` : `Section: ${c?.section || t.b.section || 'not set'}`
    return {
      cls: 'green',
      title: t.total === 1 ? 'In the library' : `${t.inLib} of ${t.total} copies in the library`,
      text: free.length ? `${place} · Acc. ${free.slice(0, 4).map((x) => x.acc_no).join(', ')}` : place,
    }
  }
  if (out.length) {
    const c = out[0]
    const overdue = c.due_date && new Date(c.due_date + 'T23:59:59') < new Date()
    return {
      cls: 'orange',
      title: t.total === 1 ? (overdue ? `Overdue since ${fmtDate(c.due_date)}` : `You can get it after ${fmtDate(c.due_date)}`)
        : `All ${t.total} copies are out · first back ${fmtDate(c.due_date)}`,
      text: `Acc. ${c.acc_no} is with ${c.borrower_name} (${c.borrower_no})${overdue ? ', overdue' : ''}`,
    }
  }
  return { cls: 'gray', title: 'Not available', text: t.list.map((c) => `${c.acc_no}: ${c.status.toLowerCase()}`).join(' · ') }
}
</script>
