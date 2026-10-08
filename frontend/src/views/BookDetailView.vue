<template>
  <div v-if="b">
    <div class="page-head">
      <div>
        <h1>{{ b.title }}</h1>
        <p class="sub">Acc. No. {{ b.acc_no }} · {{ b.section || 'No section' }} <StatusBadge :status="b.status" /></p>
      </div>
      <div class="actions">
        <router-link :to="`/books/${b.id}/edit`" class="btn"><Pencil :size="16" /> Edit</router-link>
        <router-link :to="`/books/new?copy=${b.id}`" class="btn"><Copy :size="16" /> Add another copy</router-link>
        <button class="btn" @click="openPrint('/print/book-labels?ids=' + b.id)"><Printer :size="16" /> Print label</button>
      </div>
    </div>

    <div class="grid-side">
      <div>
        <div class="card center detail-cover">
          <BookCover :src="b.cover_url" :title="b.title" size="lg" />
          <router-link :to="`/books/${b.id}/edit`" class="btn sm mt"><ImagePlus :size="15" /> {{ b.cover_url ? 'Change cover' : 'Add cover picture' }}</router-link>
        </div>

        <div class="card center">
          <img :src="qrUrl(b.acc_no, 6)" alt="Book QR code" style="width: 160px; height: 160px" />
          <img :src="barcodeUrl(b.acc_no)" alt="Book barcode" style="width: 100%; max-width: 260px; height: 60px; object-fit: fill; display: block; margin: 8px auto 0" />
          <div class="muted small">{{ b.acc_no }}</div>
        </div>

        <div class="card">
          <h2>Where is it?</h2>
          <div v-if="b.status === 'ISSUED'" class="where orange" style="max-width: none">
            <strong>With {{ b.borrower_name }} ({{ b.borrower_no }})</strong>
            Borrowed {{ fmtDate(b.date_borrowed) }}. Due back {{ fmtDate(b.due_date) }}.
            <div class="mt"><router-link :to="'/members/' + b.borrower_id">Open member profile</router-link></div>
          </div>
          <div v-else-if="b.status === 'AVAILABLE'" class="where green" style="max-width: none">
            <strong>In the library</strong>{{ b.location || 'Rack / shelf not set' }}
          </div>
          <div v-else class="where gray" style="max-width: none">
            <strong>{{ statusLabel(b.status) }}</strong>
            <span v-if="b.withdrawn">Withdrawn by {{ b.withdrawn_by }} on {{ fmtDate(b.withdrawn_date) }}</span>
          </div>

          <div v-if="b.status !== 'ISSUED'" class="mt">
            <label>Change status</label>
            <div class="actions">
              <button v-if="b.status !== 'AVAILABLE'" class="btn sm" @click="setStatus('AVAILABLE')">Back in library</button>
              <button v-if="b.status !== 'DAMAGED'" class="btn sm" @click="setStatus('DAMAGED')">Damaged</button>
              <button v-if="b.status !== 'LOST'" class="btn sm" @click="setStatus('LOST')">Lost</button>
              <button v-if="b.status !== 'WITHDRAWN'" class="btn sm danger" @click="setStatus('WITHDRAWN')">Withdraw</button>
            </div>
          </div>
        </div>
      </div>

      <div>
        <div class="card">
          <h2>Details</h2>
          <dl class="info">
            <template v-for="f in shown" :key="f[0]">
              <dt>{{ f[1] }}</dt><dd>{{ f[2] }}</dd>
            </template>
          </dl>
        </div>

        <div class="card">
          <h2>Borrowing history</h2>
          <div v-if="!loans.length" class="empty">This book has not been borrowed yet.</div>
          <div v-else class="table-wrap">
            <table class="table">
              <thead><tr><th>Member</th><th>Borrowed</th><th>Due</th><th>Returned</th><th class="num">Fine</th></tr></thead>
              <tbody>
                <tr v-for="l in loans" :key="l.id" class="click" @click="$router.push('/members/' + l.member.id)">
                  <td>{{ l.member.name }} ({{ l.member.membership_no }})</td>
                  <td>{{ fmtDate(l.issue_date) }}</td>
                  <td>{{ fmtDate(l.due_date) }}</td>
                  <td>{{ l.return_date ? fmtDate(l.return_date) : 'Not yet' }}</td>
                  <td class="num">{{ l.total_fine ? money(l.total_fine) : '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Copy, ImagePlus, Pencil, Printer } from 'lucide-vue-next'
import BookCover from '../components/BookCover.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api, barcodeUrl, qrUrl } from '../api'
import { toast } from '../store'
import { statusLabel } from '../constants'
import { fmtDate, money, openPrint } from '../utils'

const route = useRoute()
const b = ref(null)
const loans = ref([])

const LABELS = [
  ['sinhala_title', 'Sinhala title'], ['tamil_title', 'Tamil title'], ['sinhala_title_formal', 'Sinhala title (formal)'],
  ['persons', 'Person(s)'], ['corporate_body', 'Corporate body'], ['meeting', 'Meeting'],
  ['parent_title', 'Parent title'], ['parent_title_2', 'Parent title (2)'], ['publisher', 'Publisher'],
  ['year_of_publication', 'Year of publication'], ['edition', 'Edition'], ['physical_description', 'Physical description'],
  ['series', 'Series'], ['isbn', 'ISBN'], ['issn', 'ISSN'], ['medium', 'Medium'], ['material_type', 'Type of material'],
  ['record_type', 'Record type'], ['bibliographic_level', 'Bibliographic level'], ['item_identifier', 'Item identifier'],
  ['heading_identifier', 'Heading identifier'], ['heading', 'Heading'], ['citation', 'Citation'],
  ['class_no_scheme', 'Class. No. & scheme'], ['call_no', 'Call No.'], ['location', 'Rack / shelf'],
  ['price', 'Price'], ['keyword_1', 'Keyword'], ['keyword_2', 'Keyword'], ['keyword_3', 'Keyword'], ['keyword_4', 'Keyword'],
  ['broad_headings', 'Broad heading(s)'], ['geographical_code', 'Geographical code'], ['notes_bib', 'Notes (bib. re.)'],
  ['notes_contents', 'Notes (contents)'], ['abstracts', 'Abstracts'], ['remarks', 'Remarks'],
  ['date_entered', 'Date entered'], ['entered_by', 'Entered by'], ['user_code', 'User code'],
]

const shown = computed(() =>
  LABELS.filter(([k]) => b.value[k] !== '' && b.value[k] !== null && b.value[k] !== 0)
    .map(([k, label]) => [k, label, k === 'price' ? money(b.value[k]) : k === 'date_entered' ? fmtDate(b.value[k]) : b.value[k]]))

async function load() {
  const r = await api.get(`/books/${route.params.id}`)
  b.value = r.book
  loans.value = r.loans
}

async function setStatus(status) {
  const reason = prompt(`Reason for marking as ${statusLabel(status).toLowerCase()} (optional):`, '')
  if (reason === null) return
  try {
    b.value = await api.post(`/books/${b.value.id}/status`, { status, reason })
    toast('Status changed')
  } catch (e) {
    toast(e.message, 'error')
  }
}

onMounted(load)
</script>
