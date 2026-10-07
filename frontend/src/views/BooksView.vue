<template>
  <div>
    <div class="page-head">
      <h1>Books</h1>
      <div class="actions">
        <button class="btn" :disabled="!selected.length" @click="printLabels">
          <Printer :size="16" /> Print labels ({{ selected.length }})
        </button>
        <router-link to="/books/new" class="btn primary"><BookPlus :size="18" /> New book</router-link>
      </div>
    </div>

    <div class="card">
      <div class="filters">
        <div class="grow">
          <label for="bq">Search</label>
          <input id="bq" v-model="q" placeholder="Title, author, Acc. No., ISBN, keyword" @keydown.enter="load(1)" />
        </div>
        <div>
          <label for="bs">Section</label>
          <select id="bs" v-model="section" @change="load(1)">
            <option value="">All sections</option>
            <option v-for="s in SECTIONS" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
        <div>
          <label for="bst">Status</label>
          <select id="bst" v-model="status" @change="load(1)">
            <option value="">All</option>
            <option v-for="(v, k) in BOOK_STATUS" :key="k" :value="k">{{ v.label }}</option>
          </select>
        </div>
        <button class="btn primary" @click="load(1)"><Search :size="16" /> Search</button>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th><input type="checkbox" :checked="allChecked" title="Select all on this page" @change="toggleAll" /></th>
              <th>Acc. No.</th><th>Title</th><th>Author</th><th>Section</th><th>Rack / shelf</th><th>Status</th><th>Due date</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in items" :key="b.id" class="click" @click="$router.push('/books/' + b.id)">
              <td @click.stop><input v-model="selected" type="checkbox" :value="b.id" /></td>
              <td><strong>{{ b.acc_no }}</strong></td>
              <td>{{ b.title }}<div v-if="b.sinhala_title" class="muted small">{{ b.sinhala_title }}</div></td>
              <td>{{ b.persons || '-' }}</td>
              <td>{{ b.section || '-' }}</td>
              <td>{{ b.location || '-' }}</td>
              <td><StatusBadge :status="b.status" /></td>
              <td>{{ b.due_date ? fmtDate(b.due_date) : '-' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="loaded && !items.length" class="empty">No books found.</div>
      </div>
      <Pager :page="page" :size="size" :total="total" @update:page="load" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { BookPlus, Printer, Search } from 'lucide-vue-next'
import Pager from '../components/Pager.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api } from '../api'
import { BOOK_STATUS, SECTIONS } from '../constants'
import { fmtDate, openPrint } from '../utils'

const q = ref('')
const section = ref('')
const status = ref('')
const items = ref([])
const total = ref(0)
const page = ref(1)
const size = 25
const loaded = ref(false)
const selected = ref([])

const allChecked = computed(() => items.value.length > 0 && items.value.every((b) => selected.value.includes(b.id)))

function toggleAll() {
  if (allChecked.value) selected.value = selected.value.filter((id) => !items.value.some((b) => b.id === id))
  else selected.value = [...new Set([...selected.value, ...items.value.map((b) => b.id)])]
}

function printLabels() {
  openPrint('/print/book-labels?ids=' + selected.value.join(','))
}

async function load(p = page.value) {
  page.value = p
  const r = await api.get('/books', { q: q.value, section: section.value, status: status.value, page: p, size })
  items.value = r.items
  total.value = r.total
  loaded.value = true
}

onMounted(load)
</script>
