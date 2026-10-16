<template>
  <div class="list-page">
    <div class="page-head">
      <h1>Books</h1>
      <div class="actions">
        <button class="btn" :disabled="!selected.length" @click="printLabels">
          <Printer :size="16" /> Print labels ({{ selected.length }})
        </button>
        <button class="btn" :disabled="!selected.length" title="The QR labels of the ticked books are stuck on" @click="markLabels(true)">
          <CircleCheck :size="16" /> Mark labelled ({{ selected.length }})
        </button>
        <button v-if="selected.length" class="btn" title="Undo: the ticked books have no label yet" @click="markLabels(false)">Not labelled</button>
        <router-link to="/books/new" class="btn primary"><BookPlus :size="18" /> New book</router-link>
      </div>
    </div>

    <div class="card list-card">
      <div class="filters">
        <div class="grow">
          <label for="bq">Search</label>
          <div class="live-search">
            <Search :size="17" />
            <input id="bq" v-model="q" placeholder="Title, author, Acc. No., ISBN or keyword" autocomplete="off"
                   @input="search.soon" @keydown.enter="search.now" />
            <button v-if="q" type="button" class="live-clear" title="Clear" @click="q = ''; search.now()"><X :size="16" /></button>
          </div>
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
        <div>
          <label for="bl">QR label</label>
          <select id="bl" v-model="label" @change="load(1)">
            <option value="">All</option>
            <option value="yes">Labelled</option>
            <option value="no">Not labelled</option>
          </select>
        </div>
      </div>

      <div ref="listBox" class="table-wrap list-scroll list-fit">
        <table class="table fit-table">
          <colgroup>
            <col style="width: 52px" /><col style="width: 104px" /><col /><col style="width: 18%" />
            <col style="width: 104px" /><col style="width: 104px" /><col style="width: 116px" /><col style="width: 104px" />
            <col style="width: 86px" />
          </colgroup>
          <thead>
            <tr>
              <th><input type="checkbox" :checked="allChecked" title="Select all on this page" @change="toggleAll" /></th>
              <th>Acc. No.</th><th>Title</th><th>Author</th><th>Section</th><th>Rack / shelf</th><th>Status</th><th>Due date</th><th class="icon-col">QR label</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in items" :key="b.id" class="click" @click="$router.push('/books/' + b.id)">
              <td @click.stop><input v-model="selected" type="checkbox" :value="b.id" /></td>
              <td><span class="code-tag">{{ b.acc_no }}</span></td>
              <td :title="b.title">{{ b.title }}</td>
              <td :title="b.persons">{{ b.persons || '-' }}</td>
              <td>{{ b.section || '-' }}</td>
              <td>{{ b.location || '-' }}</td>
              <td><StatusBadge :status="b.status" /></td>
              <td>{{ b.due_date ? fmtDate(b.due_date) : '-' }}</td>
              <td class="icon-col"><span class="done-mark" :class="{ done: b.label_done }" role="img"
                    :title="b.label_done ? 'QR label is on the book' : 'No QR label yet'" :aria-label="b.label_done ? 'QR label is on the book' : 'No QR label yet'">
                <component :is="b.label_done ? CircleCheck : CircleDashed" :size="19" /></span></td>
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
import { computed, ref } from 'vue'
import { BookPlus, CircleCheck, CircleDashed, Printer, Search, X } from 'lucide-vue-next'
import Pager from '../components/Pager.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api } from '../api'
import { toast } from '../store'
import { BOOK_STATUS, SECTIONS } from '../constants'
import { fmtDate, openPrint } from '../utils'
import { useFitPage } from '../fitPage'
import { latestOnly, useLiveSearch } from '../liveSearch'

const q = ref('')
const section = ref('')
const status = ref('')
const label = ref('')
const items = ref([])
const total = ref(0)
const page = ref(1)
const listBox = ref(null)
// As many rows as fit on screen; Previous / Next show the next set.
const size = useFitPage(listBox, page, load)
const loaded = ref(false)
const selected = ref([])

const allChecked = computed(() => items.value.length > 0 && items.value.every((b) => selected.value.includes(b.id)))

function toggleAll() {
  if (allChecked.value) selected.value = selected.value.filter((id) => !items.value.some((b) => b.id === id))
  else selected.value = [...new Set([...selected.value, ...items.value.map((b) => b.id)])]
}

// The labels of the ticked books are stuck on (or not): saved for all of them at once.
async function markLabels(done) {
  try {
    const r = await api.post('/books/labels', { ids: selected.value, done })
    toast(`${r.changed} book(s) marked as ${done ? 'labelled' : 'not labelled'}`)
    selected.value = []
    load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

function printLabels() {
  openPrint('/print/book-labels?ids=' + selected.value.join(','))
}

// The list updates while you type (a moment after the last key), starting again from page 1.
const search = useLiveSearch(() => load(1))
const fetchBooks = latestOnly((params) => api.get('/books', params))
async function load(p = page.value) {
  page.value = p
  const r = await fetchBooks({ q: q.value, section: section.value, status: status.value, label: label.value, page: p, size: size.value })
  if (!r) return // a newer search has already answered
  items.value = r.items
  total.value = r.total
  loaded.value = true
}
</script>
