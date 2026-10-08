<template>
  <div>
    <div class="page-head">
      <div>
        <h1>{{ isEdit ? 'Edit book' : copyOf ? 'Add another copy' : 'New book' }}</h1>
        <p class="sub">
          {{ isEdit ? 'Click a step to change that part, then save.'
            : copyOf ? 'The details are copied from the other copy. Check them, then save. A new Acc. No. is given if you leave it empty.'
            : 'Fill in each step and press Next. Only the title is required.' }}
        </p>
      </div>
    </div>

    <!-- Steps, like Issue book; click a step to go to it -->
    <div class="steps">
      <button v-for="(st, i) in STEPS" :key="st" type="button" class="step" :class="{ on: step === i && !saved, done: saved || i < step }"
              :disabled="!!saved || (!isEdit && i > step && !canLeave(step))" @click="goTo(i)">
        <b>{{ i + 1 }}</b> {{ st }}
      </button>
    </div>

    <!-- Done -->
    <div v-if="saved" class="card done-panel">
      <div class="ok"><Check :size="32" /></div>
      <h2>Book saved</h2>
      <p class="muted">{{ saved.title }}</p>
      <div class="new-no">Acc. No. <span class="code-tag">{{ saved.acc_no }}</span></div>
      <div class="actions" style="justify-content: center">
        <button class="btn primary" @click="openPrint('/print/book-labels?ids=' + saved.id)"><Printer :size="16" /> Print label</button>
        <router-link :to="'/books/new?copy=' + saved.id" class="btn"><Copy :size="16" /> Add another copy</router-link>
        <router-link :to="'/books/' + saved.id" class="btn"><BookOpen :size="16" /> Open book</router-link>
        <button class="btn" @click="startAgain"><BookPlus :size="16" /> Add another book</button>
      </div>
    </div>

    <template v-else>
      <!-- 1. Book details, with the front cover beside them -->
      <div v-if="step === 0" class="card wizard-card">
        <div class="book-form-top inside">
          <div>
            <h2>Book details</h2>
            <p class="muted step-help">What is the book? Only the title is required. Leave Acc. No. empty to create one automatically.</p>
            <FormGrid :fields="mainFields" :model="b" />
          </div>
          <PictureUpload v-model="cover" kind="cover" :saved="savedCover" :label="b.title" @error="(e) => (error = e)" />
        </div>
      </div>

      <div v-if="step > 0" class="card wizard-card">
        <!-- 2. Shelf & price -->
        <template v-if="step === 1">
          <h2>Shelf &amp; price</h2>
          <p class="muted step-help">Where does the book go, and what does it cost? The price is used for the damaged-book fine.</p>
          <label>Section</label>
          <div class="choice-grid" role="radiogroup">
            <button v-for="s in SECTION_CHOICES" :key="s.value" type="button" role="radio" :aria-checked="b.section === s.value"
                    class="hol-type" :class="{ on: b.section === s.value }" @click="b.section = s.value">
              <span class="dot"></span>
              <span><strong>{{ s.value }}</strong><small>{{ s.hint }}</small></span>
            </button>
          </div>
          <FormGrid class="mt" :fields="shelfFields" :model="b" />
        </template>

        <!-- 3. Publication -->
        <template v-else-if="step === 2">
          <h2>Publication</h2>
          <p class="muted step-help">Who published it and when. All optional.</p>
          <FormGrid :fields="pubFields" :model="b" />
        </template>

        <!-- 4. More details -->
        <template v-else-if="step === 3">
          <h2>More details</h2>
          <p class="muted step-help">Cataloguing details used by the library. All optional - skip this step if you do not need them.</p>
          <FormGrid :fields="catFields" :model="b" />
        </template>

        <!-- 5. Check & save -->
        <template v-else>
          <h2>Check &amp; save</h2>
          <p class="muted step-help">Look over the details. Press Edit to change a part.</p>
          <div class="review review-book">
            <div class="review-part review-cover">
              <BookCover :src="coverShown" :title="b.title" size="lg" />
              <button class="btn sm mt" @click="goTo(0)"><Pencil :size="14" /> Edit</button>
            </div>
            <div v-for="part in review" :key="part.title" class="review-part">
              <div class="review-head"><h3>{{ part.title }}</h3><button class="btn sm" @click="goTo(part.step)"><Pencil :size="14" /> Edit</button></div>
              <dl class="info">
                <template v-for="row in part.rows" :key="row[0]">
                  <dt>{{ row[0] }}</dt><dd>{{ row[1] || '-' }}</dd>
                </template>
              </dl>
            </div>
          </div>
        </template>
      </div>

      <p v-if="error" class="alert red">{{ error }}</p>

      <div class="card wizard-nav">
        <button v-if="step > 0" class="btn" @click="goTo(step - 1)"><ChevronLeft :size="16" /> Back</button>
        <button v-else class="btn" @click="$router.back()">Cancel</button>
        <span class="muted small">Step {{ step + 1 }} of {{ STEPS.length }}</span>
        <div class="actions">
          <button v-if="isEdit && step < STEPS.length - 1" class="btn" :disabled="busy || !b.title.trim()" @click="save"><Save :size="16" /> Save now</button>
          <button v-if="step === 3" class="btn" @click="goTo(4)">Skip</button>
          <button v-if="step < STEPS.length - 1" class="btn primary" :disabled="!canLeave(step)" @click="goTo(step + 1)">Next <ChevronRight :size="16" /></button>
          <button v-else class="btn primary" :disabled="busy" @click="save"><Save :size="16" /> {{ isEdit ? 'Save changes' : 'Save book' }}</button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BookOpen, BookPlus, Check, ChevronLeft, ChevronRight, Copy, Pencil, Printer, Save,
} from 'lucide-vue-next'
import BookCover from '../components/BookCover.vue'
import FormGrid from '../components/FormGrid.vue'
import PictureUpload from '../components/PictureUpload.vue'
import { api } from '../api'
import { toast } from '../store'
import { SECTIONS } from '../constants'
import { fmtDate, isoDate, money, openPrint } from '../utils'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const copyOf = route.query.copy
const busy = ref(false)
const error = ref('')
const step = ref(0)
const saved = ref(null) // the book, once saved (new books only)

const STEPS = ['Book details', 'Shelf & price', 'Publication', 'More details', 'Check & save']
const HINTS = { Lending: 'Members can take it home', Children: 'Children\'s books', Buddhist: 'Buddhist books', Reference: 'Read in the library only' }
const SECTION_CHOICES = SECTIONS.map((s) => ({ value: s, hint: HINTS[s] || '' }))

const mainFields = [
  { key: 'title', label: 'Title', required: true, wide: true },
  { key: 'sinhala_title', label: 'Sinhala title' },
  { key: 'tamil_title', label: 'Tamil title' },
  { key: 'persons', label: 'Person(s) / author' },
  { key: 'isbn', label: 'ISBN' },
  { key: 'acc_no', label: 'Acc. No.', help: 'Leave empty to create one automatically' },
]
const shelfFields = [
  { key: 'rack_no', label: 'Rack No.' },
  { key: 'shelf_no', label: 'Shelf No.' },
  { key: 'call_no', label: 'Call No.' },
  { key: 'price', label: 'Price (Rs.)', type: 'number' },
  { key: 'remarks', label: 'Remarks', type: 'textarea', wide: true },
]
const pubFields = [
  { key: 'publisher', label: 'Publisher' },
  { key: 'year_of_publication', label: 'Year of publication' },
  { key: 'edition', label: 'Edition' },
  { key: 'physical_description', label: 'Physical description', placeholder: 'e.g. 240 p. ; 21 cm' },
  { key: 'series', label: 'Series' },
  { key: 'medium', label: 'Medium', list: ['Sinhala', 'Tamil', 'English'] },
  { key: 'material_type', label: 'Type of material', list: ['Book', 'Magazine', 'Newspaper', 'CD/DVD', 'Map'] },
  { key: 'date_entered', label: 'Date entered', type: 'date' },
]
const catFields = [
  { key: 'record_type', label: 'Record type' },
  { key: 'bibliographic_level', label: 'Bibliographic level' },
  { key: 'item_identifier', label: 'Item identifier' },
  { key: 'heading_identifier', label: 'Heading identifier' },
  { key: 'heading', label: 'Heading' },
  { key: 'issn', label: 'ISSN' },
  { key: 'parent_title', label: 'Parent title' },
  { key: 'parent_title_2', label: 'Parent title (2)' },
  { key: 'sinhala_title_formal', label: 'Sinhala title (formal)' },
  { key: 'corporate_body', label: 'Corporate body' },
  { key: 'meeting', label: 'Meeting' },
  { key: 'citation', label: 'Citation' },
  { key: 'class_no_scheme', label: 'Class. No. & scheme' },
  { key: 'keyword_1', label: 'Keyword 1' },
  { key: 'keyword_2', label: 'Keyword 2' },
  { key: 'keyword_3', label: 'Keyword 3' },
  { key: 'keyword_4', label: 'Keyword 4' },
  { key: 'broad_headings', label: 'Broad heading(s) / notation' },
  { key: 'geographical_code', label: 'Geographical code' },
  { key: 'user_code', label: 'User code' },
  { key: 'entered_by', label: 'Entered by', help: 'Filled automatically if empty' },
  { key: 'notes_bib', label: 'Notes (bib. re.)', type: 'textarea', wide: true },
  { key: 'notes_contents', label: 'Notes (contents)', type: 'textarea', wide: true },
  { key: 'abstracts', label: 'Abstracts', type: 'textarea', wide: true },
]

const allKeys = [...mainFields, 'section', ...shelfFields, ...pubFields, ...catFields].map((f) => f.key || f)
function blank() {
  const o = Object.fromEntries(allKeys.map((k) => [k, '']))
  return Object.assign(o, { date_entered: isoDate(), medium: 'Sinhala', material_type: 'Book', section: 'Lending' })
}
const b = reactive(blank())

function fill(src) {
  allKeys.forEach((k) => { b[k] = src[k] ?? '' })
}

// What is shown on the "Check & save" step.
const review = computed(() => [
  { title: 'Book details', step: 0, rows: [['Title', b.title], ['Sinhala title', b.sinhala_title], ['Tamil title', b.tamil_title],
    ['Author', b.persons], ['ISBN', b.isbn], ['Acc. No.', b.acc_no || 'Created automatically']] },
  { title: 'Shelf & price', step: 1, rows: [['Section', b.section], ['Rack / shelf', [b.rack_no, b.shelf_no].filter(Boolean).join(' / ')],
    ['Call No.', b.call_no], ['Price', b.price !== '' && b.price !== null ? money(b.price) : ''], ['Remarks', b.remarks]] },
  { title: 'Publication', step: 2, rows: [['Publisher', b.publisher], ['Year', b.year_of_publication], ['Edition', b.edition],
    ['Medium', b.medium], ['Type', b.material_type], ['Date entered', b.date_entered && fmtDate(b.date_entered)]] },
  { title: 'More details', step: 3, rows: [['Class. No.', b.class_no_scheme],
    ['Keywords', [b.keyword_1, b.keyword_2, b.keyword_3, b.keyword_4].filter(Boolean).join(', ')],
    ['Other fields', `${catFields.filter((f) => b[f.key] && !f.key.startsWith('keyword') && f.key !== 'class_no_scheme').length} filled in`]] },
])

// A step can be left once its required fields are filled.
const canLeave = (i) => (i === 0 ? !!b.title.trim() : true)

function goTo(i) {
  if (i < 0 || i >= STEPS.length) return
  if (!isEdit.value && i > step.value) {
    for (let k = step.value; k < i; k++) if (!canLeave(k)) return
  }
  error.value = ''
  step.value = i
}

// ---------- Front cover (optional) ----------
const savedCover = ref(null) // URL of the cover already saved (or of the copied book)
const cover = ref({ image: null, removed: false }) // what to do with the cover on save
const coverShown = computed(() => cover.value.image || (cover.value.removed ? null : savedCover.value))

// After the book itself is saved, save / copy / remove its cover.
async function saveCover(id) {
  if (cover.value.image) await api.post(`/books/${id}/cover`, { image: cover.value.image })
  else if (cover.value.removed && isEdit.value && savedCover.value) await api.del(`/books/${id}/cover`)
  else if (copyOf && savedCover.value && !cover.value.removed) await api.post(`/books/${id}/cover`, { copy_from: Number(copyOf) })
}

function startAgain() {
  if (copyOf) {
    router.push('/books/new')
    return
  }
  Object.assign(b, blank())
  cover.value = { image: null, removed: false }
  savedCover.value = null
  saved.value = null
  step.value = 0
}

onMounted(async () => {
  const id = route.params.id || copyOf
  if (!id) return
  const r = await api.get(`/books/${id}`)
  fill(r.book)
  savedCover.value = r.book.cover_url
  if (copyOf) {
    b.acc_no = ''
    b.date_entered = isoDate()
    b.entered_by = ''
  }
})

async function save() {
  error.value = ''
  if (!b.title.trim()) {
    step.value = 0
    error.value = 'Please enter the title.'
    return
  }
  busy.value = true
  try {
    const result = isEdit.value ? await api.put(`/books/${route.params.id}`, b) : await api.post('/books', b)
    await saveCover(result.id)
    toast(`Book saved. Acc. No. ${result.acc_no}`)
    if (isEdit.value) router.push('/books/' + result.id)
    else saved.value = result
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>
