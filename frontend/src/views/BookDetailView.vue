<template>
  <div v-if="b" class="profile3">
    <!-- 1. Always on screen: which book this is, and what you can do -->
    <div class="card ph-head">
      <BookCover :src="b.cover_url" :title="b.title" size="lg" />
      <div class="ph-who">
        <h1 :title="b.title">{{ b.title }}</h1>
        <div class="ph-line">
          <span class="ph-no"><small>Acc. No.</small><strong>{{ b.acc_no }}</strong></span>
          <span class="ph-no"><small>Call No.</small><strong :class="{ none: !b.call_no }">{{ b.call_no || '-' }}</strong></span>
        </div>
        <div class="ph-actions">
          <router-link :to="`/books/${b.id}/edit`" class="btn sm"><Pencil :size="15" /> Edit details</router-link>
          <router-link :to="`/books/${b.id}/edit`" class="btn sm"><ImagePlus :size="15" /> {{ b.cover_url ? 'Change cover' : 'Add cover' }}</router-link>
          <router-link :to="`/books/new?copy=${b.id}`" class="btn sm"><Copy :size="15" /> Add another copy</router-link>
          <button class="btn sm" @click="openPrint('/print/book-labels?ids=' + b.id)"><Printer :size="15" /> Print label</button>
        </div>
      </div>
    </div>

    <!-- 2. Parts of the book page, as steps like Issue book: click one to see it -->
    <div class="steps ph-tabs" role="tablist">
      <button v-for="t in tabs" :key="t.key" role="tab" type="button" class="step" :class="{ on: tab === t.key }"
              :aria-selected="tab === t.key" @click="tab = t.key">
        <b><component :is="t.icon" v-if="t.icon" :size="14" /><template v-else>{{ t.count }}</template></b> {{ t.label }}
      </button>
    </div>

    <!-- 3. The chosen part -->
    <div class="card ph-panel">
      <div class="record-scroll">

        <!-- Details -->
        <template v-if="tab === 'details'">
          <div class="date-line">
            <div v-for="t in facts" :key="t.label" class="date-cell">
              <component :is="t.icon" :size="17" />
              <span><small>{{ t.label }}</small><strong>{{ t.value || '-' }}</strong></span>
            </div>
          </div>
          <!-- Every other detail as a tile, in the same style as the "All reports" grid.
               One group at a time; the bar at the bottom moves between them. -->
          <section v-if="sec" class="info-sec">
            <h3>{{ sec.title }} <span class="sec-count">{{ secIdx + 1 }} of {{ detailSecs.length }}</span></h3>
            <div class="info-grid">
              <div v-for="r in sec.rows" :key="r.label" class="num-tile info-tile" :class="[{ wide: r.wide }, r.tone && 'st-' + r.tone]" :title="r.value || ''">
                <span class="num-badge" :class="r.tone ? '' : sec.color"><component :is="r.icon" :size="17" /></span>
                <span class="num-text">
                  <small>{{ r.label }}</small>
                  <strong :class="{ none: !r.value }">{{ r.value || '-' }}</strong>
                </span>
              </div>
            </div>
          </section>
        </template>

        <!-- Where is it -->
        <template v-else-if="tab === 'where'">
          <!-- Who has it / where it is, as tiles -->
          <section class="info-sec">
            <h3>{{ b.status === 'ISSUED' ? 'With a member' : b.status === 'AVAILABLE' ? 'In the library' : 'Not in use' }}</h3>
            <div class="info-grid">
              <div v-if="b.status === 'ISSUED'" class="num-tile info-tile span3 who-tile">
                <span class="num-badge g-members"><UserRound :size="17" /></span>
                <span class="num-text">
                  <small>Borrowed by</small>
                  <strong :title="b.borrower_name">{{ b.borrower_name }}</strong>
                  <small>Membership No. {{ b.borrower_no }}</small>
                </span>
                <router-link :to="'/members/' + b.borrower_id" class="btn sm soft"><UserRound :size="15" /> Open member profile</router-link>
              </div>
              <div v-for="r in whereTiles" :key="r.label" class="num-tile info-tile" :class="r.tone && 'st-' + r.tone">
                <span class="num-badge" :class="r.tone ? '' : 'g-books'"><component :is="r.icon" :size="17" /></span>
                <span class="num-text">
                  <small>{{ r.label }}</small>
                  <strong :class="{ none: !r.value }">{{ r.value || '-' }}</strong>
                  <small v-if="r.note">{{ r.note }}</small>
                </span>
              </div>
            </div>
          </section>

          <div v-if="b.status !== 'ISSUED'" class="info-sec where-change">
            <h3>Change status</h3>
            <div class="actions">
              <button v-if="b.status !== 'AVAILABLE'" class="btn sm" @click="askStatus('AVAILABLE')">Back in library</button>
              <button v-if="b.status !== 'DAMAGED'" class="btn sm" @click="askStatus('DAMAGED')">Damaged</button>
              <button v-if="b.status !== 'LOST'" class="btn sm" @click="askStatus('LOST')">Lost</button>
              <button v-if="b.status !== 'WITHDRAWN'" class="btn sm danger" @click="askStatus('WITHDRAWN')">Withdraw</button>
            </div>
          </div>
        </template>

        <!-- Borrowing history -->
        <template v-else-if="tab === 'history'">
          <div v-if="!loans.length" class="empty">This book has not been borrowed yet.</div>
          <table v-else class="table report-table">
            <colgroup><col /><col style="width: 116px" /><col style="width: 116px" /><col style="width: 116px" /><col style="width: 100px" /></colgroup>
            <thead><tr><th>Member</th><th>Borrowed</th><th>Due</th><th>Returned</th><th class="num">Fine</th></tr></thead>
            <tbody>
              <tr v-for="l in loans" :key="l.id" class="click" @click="$router.push('/members/' + l.member.id)">
                <td :title="l.member.name">{{ l.member.name }} <span class="code-tag">{{ l.member.membership_no }}</span></td>
                <td>{{ fmtDate(l.issue_date) }}</td>
                <td>{{ fmtDate(l.due_date) }}</td>
                <td><span v-if="l.return_date">{{ fmtDate(l.return_date) }}</span><span v-else class="badge orange">Not yet</span></td>
                <td class="num">{{ l.total_fine ? money(l.total_fine) : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </template>

        <!-- QR label -->
        <template v-else>
          <div class="card-tab">
            <img :src="qrUrl(b.acc_no, 8)" alt="Book QR code" class="zoomable" title="Click to show the code big" @click="zoom = 'qr'" />
            <div class="card-tab-info">
              <h2>QR label</h2>
              <p class="muted">Scanned at the counter. Click to enlarge.</p>
              <img :src="barcodeUrl(b.acc_no)" alt="Book barcode" class="zoomable label-bar" title="Click to show the barcode big" @click="zoom = 'bar'" />
              <div class="actions">
                <button class="btn primary" @click="openPrint('/print/book-labels?ids=' + b.id)"><Printer :size="16" /> Print label</button>
                <button class="btn" @click="zoom = 'qr'"><Maximize2 :size="16" /> Show code big</button>
              </div>
              <div class="done-box" :class="{ done: b.label_done }">
                <span><component :is="b.label_done ? CircleCheck : CircleDashed" :size="17" />
                  <span><strong>{{ b.label_done ? 'QR label is on the book' : 'QR label not on the book yet' }}</strong>
                    <small v-if="b.label_done">{{ fmtDate(b.label_done_at) }}<template v-if="b.label_done_by"> · {{ b.label_done_by }}</template></small>
                    <small v-else>Print the label, stick it on, then mark it done</small></span></span>
                <button class="btn sm" :class="{ primary: !b.label_done }" @click="setLabel(!b.label_done)">{{ b.label_done ? 'Undo' : 'Mark as labelled' }}</button>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Stays at the bottom of the panel: move between the groups of details -->
      <div v-if="tab === 'details' && detailSecs.length > 1" class="sec-nav">
        <button class="btn sm" :disabled="secIdx === 0" @click="secIdx--"><ChevronLeft :size="16" /> Previous</button>
        <div class="sec-steps">
          <button v-for="(x, i) in detailSecs" :key="x.title" type="button" :class="{ on: i === secIdx }" @click="secIdx = i">{{ x.title }}</button>
        </div>
        <button class="btn sm" :disabled="secIdx === detailSecs.length - 1" @click="secIdx++">Next <ChevronRight :size="16" /></button>
      </div>
    </div>

    <!-- The code on its own, big enough to scan from the screen -->
    <Modal v-if="zoom" :title="b.acc_no" :wide="zoom === 'bar'" @close="zoom = ''">
      <div class="code-zoom" :class="zoom">
        <img v-if="zoom === 'qr'" :src="qrUrl(b.acc_no, 12)" alt="Book QR code" />
        <img v-else :src="barcodeUrl(b.acc_no)" alt="Book barcode" />
      </div>
    </Modal>

    <!-- Change status, with an optional reason -->
    <Modal v-if="newStatus" :title="`Mark as ${statusLabel(newStatus).toLowerCase()}?`" @close="newStatus = ''">
      <div class="field">
        <label>Reason (optional)</label>
        <input v-model="reason" placeholder="For example: pages torn" @keyup.enter="saveStatus" />
      </div>
      <template #footer>
        <button class="btn" @click="newStatus = ''">Cancel</button>
        <button class="btn" :class="newStatus === 'WITHDRAWN' ? 'danger' : 'primary'" :disabled="busy" @click="saveStatus">Mark as {{ statusLabel(newStatus).toLowerCase() }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  Barcode, BookCopy, BookOpen, Building2, CalendarClock, CalendarPlus, ChevronLeft, ChevronRight, CircleAlert, CircleCheck, CircleDashed, CircleMinus, Clock, Coins, Copy, FileText, Globe, Hash, History,
  ImagePlus, Languages, Layers, Library, ListChecks, MapPin, Maximize2, NotebookPen, Pencil, Printer, QrCode, Tag, User, UserPen, UserRound,
} from 'lucide-vue-next'
import BookCover from '../components/BookCover.vue'
import Modal from '../components/Modal.vue'
import { api, barcodeUrl, qrUrl } from '../api'
import { toast } from '../store'
import { BOOK_STATUS, statusLabel } from '../constants'
import { fmtDate, money, openPrint } from '../utils'

const route = useRoute()
const b = ref(null)
const loans = ref([])
const tab = ref('details')
const zoom = ref('') // '' | 'qr' | 'bar': which code is shown big
const newStatus = ref('') // status being chosen in the popup
const reason = ref('')
const busy = ref(false)

// Short facts of the same length share one line ...
const facts = computed(() => {
  const x = b.value
  return [
    { icon: CalendarPlus, label: 'Date entered', value: x.date_entered ? fmtDate(x.date_entered) : '' },
    { icon: Hash, label: 'Year of publication', value: x.year_of_publication },
    { icon: BookCopy, label: 'Edition', value: x.edition },
    { icon: Coins, label: 'Price', value: x.price ? money(x.price) : '' },
  ]
})
// ... every other detail gets a tile. The main ones always show; the rest only when filled in.
const STATUS_ICON = { AVAILABLE: CircleCheck, ISSUED: Clock, DAMAGED: CircleAlert, LOST: CircleAlert, WITHDRAWN: CircleMinus }
const has = (v) => v !== '' && v !== null && v !== undefined && v !== 0
const detailSecs = computed(() => {
  const x = b.value
  const keep = (rows) => rows.filter((r) => r.always || has(r.value))
  const keywords = [x.keyword_1, x.keyword_2, x.keyword_3, x.keyword_4].filter(has).join(', ')
  return [
    { title: 'Book', color: 'g-members', rows: keep([
      { icon: User, label: 'Person(s)', value: x.persons, always: true },
      { icon: Building2, label: 'Publisher', value: x.publisher, always: true },
      { icon: Barcode, label: 'ISBN', value: x.isbn, always: true },
      { icon: FileText, label: 'Physical description', value: x.physical_description, always: true },
      { icon: Languages, label: 'Sinhala title', value: x.sinhala_title, wide: true },
      { icon: Languages, label: 'Sinhala title (formal)', value: x.sinhala_title_formal, wide: true },
      { icon: Languages, label: 'Tamil title', value: x.tamil_title, wide: true },
      { icon: Building2, label: 'Corporate body', value: x.corporate_body },
      { icon: User, label: 'Meeting', value: x.meeting },
      { icon: BookOpen, label: 'Parent title', value: x.parent_title, wide: true },
      { icon: BookOpen, label: 'Parent title (2)', value: x.parent_title_2, wide: true },
      { icon: Layers, label: 'Series', value: x.series },
      { icon: Barcode, label: 'ISSN', value: x.issn },
      { icon: Globe, label: 'Medium', value: x.medium },
    ]) },
    { title: 'In the library', color: 'g-books', rows: keep([
      // Status: the whole tile takes the status colour
      { icon: STATUS_ICON[x.status] || CircleMinus, label: 'Book status', value: statusLabel(x.status), tone: BOOK_STATUS[x.status]?.cls || 'gray', always: true },
      { icon: Library, label: 'Section', value: x.section, always: true },
      { icon: MapPin, label: 'Rack / shelf', value: x.location, always: true },
      { icon: Tag, label: 'Class. No. & scheme', value: x.class_no_scheme },
      { icon: FileText, label: 'Type of material', value: x.material_type },
      { icon: FileText, label: 'Record type', value: x.record_type },
      { icon: Layers, label: 'Bibliographic level', value: x.bibliographic_level },
      { icon: Hash, label: 'Item identifier', value: x.item_identifier },
      { icon: UserPen, label: 'Entered by', value: x.entered_by },
      { icon: Hash, label: 'User code', value: x.user_code },
    ]) },
    { title: 'Subjects & notes', color: 'g-other', rows: keep([
      { icon: Tag, label: 'Keywords', value: keywords, wide: true },
      { icon: Layers, label: 'Broad heading(s)', value: x.broad_headings, wide: true },
      { icon: Hash, label: 'Heading identifier', value: x.heading_identifier },
      { icon: Layers, label: 'Heading', value: x.heading, wide: true },
      { icon: Globe, label: 'Geographical code', value: x.geographical_code },
      { icon: FileText, label: 'Citation', value: x.citation, wide: true },
      { icon: NotebookPen, label: 'Notes (bib. re.)', value: x.notes_bib, wide: true },
      { icon: NotebookPen, label: 'Notes (contents)', value: x.notes_contents, wide: true },
      { icon: NotebookPen, label: 'Abstracts', value: x.abstracts, wide: true },
      { icon: NotebookPen, label: 'Remarks', value: x.remarks, wide: true },
    ]) },
  ].filter((s) => s.rows.length)
})
const secIdx = ref(0)
const sec = computed(() => detailSecs.value[Math.min(secIdx.value, detailSecs.value.length - 1)])
// "Where is it": the status first, then the dates (issued) or the place (in the library)
const DAY = 86400000
const dayCount = (iso) => Math.round((new Date(iso + 'T00:00:00') - new Date(new Date().toDateString())) / DAY)
const whereTiles = computed(() => {
  const x = b.value
  const status = { icon: STATUS_ICON[x.status] || CircleMinus, label: 'Book status', value: statusLabel(x.status), tone: BOOK_STATUS[x.status]?.cls || 'gray' }
  if (x.status === 'ISSUED') {
    const left = x.due_date ? dayCount(x.due_date) : null
    const out = x.date_borrowed ? -dayCount(x.date_borrowed) : null
    return [
      status,
      { icon: CalendarPlus, label: 'Borrowed on', value: x.date_borrowed ? fmtDate(x.date_borrowed) : '' },
      { icon: CalendarClock, label: 'Due back', value: x.due_date ? fmtDate(x.due_date) : '', tone: left !== null && left < 0 ? 'red' : '' },
      left === null ? { icon: Clock, label: 'Days left', value: '' }
        : left < 0 ? { icon: CircleAlert, label: 'Overdue', value: `${-left} day${left === -1 ? '' : 's'} late`, tone: 'red' }
          : { icon: Clock, label: 'Days left', value: left === 0 ? 'Due today' : `${left} day${left === 1 ? '' : 's'}`, tone: left <= 2 ? 'orange' : '' },
      { icon: History, label: 'With the member for', value: out !== null ? `${out} day${out === 1 ? '' : 's'}` : '' },
    ]
  }
  if (x.status === 'AVAILABLE') {
    return [
      status,
      { icon: Library, label: 'Section', value: x.section },
      { icon: MapPin, label: 'Rack', value: x.rack_no },
      { icon: Layers, label: 'Shelf', value: x.shelf_no },
    ]
  }
  return [
    status,
    { icon: Library, label: 'Section', value: x.section },
    ...(x.withdrawn ? [
      { icon: UserPen, label: 'Withdrawn by', value: x.withdrawn_by },
      { icon: CalendarClock, label: 'Withdrawn on', value: x.withdrawn_date ? fmtDate(x.withdrawn_date) : '' },
    ] : []),
  ]
})
// The parts of the book page. Parts with records show how many; the others show an icon.
const tabs = computed(() => [
  { key: 'details', label: 'Details', icon: ListChecks },
  { key: 'where', label: 'Where is it', icon: MapPin },
  { key: 'history', label: 'Borrowing history', count: loans.value.length },
  { key: 'label', label: 'QR label', icon: QrCode },
])

async function load() {
  const r = await api.get(`/books/${route.params.id}`)
  b.value = r.book
  loans.value = r.loans
}

async function setLabel(done) {
  try {
    b.value = await api.post(`/books/${b.value.id}/label`, { done })
    toast(done ? 'Marked as labelled' : 'Marked as not labelled')
  } catch (e) {
    toast(e.message, 'error')
  }
}

function askStatus(status) {
  reason.value = ''
  newStatus.value = status
}

async function saveStatus() {
  busy.value = true
  try {
    b.value = await api.post(`/books/${b.value.id}/status`, { status: newStatus.value, reason: reason.value })
    newStatus.value = ''
    toast('Status changed')
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>
