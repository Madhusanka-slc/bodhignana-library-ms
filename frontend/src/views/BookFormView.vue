<template>
  <div>
    <div class="page-head">
      <div>
        <h1>{{ isEdit ? 'Edit book' : copyOf ? 'Add another copy' : 'New book' }}</h1>
        <p class="sub">Only the title is required. Leave Acc. No. empty to create one automatically.</p>
      </div>
    </div>

    <div class="card">
      <h2>Main details</h2>
      <FormGrid :fields="mainFields" :model="b" />
    </div>
    <div class="card">
      <h2>Publication</h2>
      <FormGrid :fields="pubFields" :model="b" />
    </div>
    <div class="card">
      <details class="more" :open="isEdit">
        <summary>More cataloguing details (optional)</summary>
        <FormGrid :fields="catFields" :model="b" />
      </details>
    </div>

    <p v-if="error" class="alert red">{{ error }}</p>
    <div class="actions">
      <button class="btn primary big" :disabled="busy" @click="save(false)"><Save :size="18" /> Save book</button>
      <button v-if="!isEdit" class="btn big" :disabled="busy" @click="save(true)">Save and add another copy</button>
      <button class="btn big" @click="$router.back()">Cancel</button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Save } from 'lucide-vue-next'
import FormGrid from '../components/FormGrid.vue'
import { api } from '../api'
import { toast } from '../store'
import { SECTIONS } from '../constants'
import { isoDate } from '../utils'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const copyOf = route.query.copy
const busy = ref(false)
const error = ref('')

const mainFields = [
  { key: 'acc_no', label: 'Acc. No.', help: 'Accession number of this copy' },
  { key: 'title', label: 'Title', required: true, wide: true },
  { key: 'sinhala_title', label: 'Sinhala title' },
  { key: 'tamil_title', label: 'Tamil title' },
  { key: 'persons', label: 'Person(s) / author' },
  { key: 'section', label: 'Section', type: 'select', options: SECTIONS },
  { key: 'rack_no', label: 'Rack No.' },
  { key: 'shelf_no', label: 'Shelf No.' },
  { key: 'call_no', label: 'Call No.' },
  { key: 'price', label: 'Price (Rs.)', type: 'number' },
  { key: 'isbn', label: 'ISBN' },
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

const allKeys = [...mainFields, ...pubFields, ...catFields].map((f) => f.key)
const b = reactive(Object.fromEntries(allKeys.map((k) => [k, ''])))
b.date_entered = isoDate()
b.medium = 'Sinhala'
b.material_type = 'Book'
b.section = 'Lending'

function fill(src) {
  allKeys.forEach((k) => { b[k] = src[k] ?? '' })
}

onMounted(async () => {
  const id = route.params.id || copyOf
  if (!id) return
  const r = await api.get(`/books/${id}`)
  fill(r.book)
  if (copyOf) {
    b.acc_no = ''
    b.date_entered = isoDate()
    b.entered_by = ''
  }
})

async function save(addAnother) {
  error.value = ''
  busy.value = true
  try {
    const saved = isEdit.value ? await api.put(`/books/${route.params.id}`, b) : await api.post('/books', b)
    toast(`Book saved. Acc. No. ${saved.acc_no}`)
    if (addAnother) router.push('/books/new?copy=' + saved.id)
    else router.push('/books/' + saved.id)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>
