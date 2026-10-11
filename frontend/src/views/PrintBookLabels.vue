<template>
  <div class="print-wrap">
    <div v-if="!embed" class="no-print bar">
      <button class="btn primary" @click="print">Print</button>
      <button class="btn" @click="close">Close</button>
      <span class="muted">{{ books.length }} label(s)</span>
    </div>
    <div class="sheet">
      <div v-for="b in books" :key="b.id" class="label">
        <div class="top">
          <img class="qr" :src="qrUrl(b.acc_no, 5)" alt="" @load="loaded++" />
          <div class="txt">
            <div class="lib">{{ s.library_name }}</div>
            <div class="acc">{{ b.acc_no }}</div>
            <div v-if="b.call_no" class="call">{{ b.call_no }}</div>
            <div class="ttl">{{ b.title }}</div>
          </div>
        </div>
        <img class="bar-img" :src="barcodeUrl(b.acc_no)" alt="" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api, barcodeUrl, qrUrl } from '../api'

const route = useRoute()
const books = ref([])
const s = ref({})
const loaded = ref(0)
const print = () => window.print()
const close = () => window.close()

const embed = route.query.embed === '1' // shown inside the app's print preview popup
watch(loaded, (n) => { if (!embed && n && n === books.value.length) setTimeout(print, 400) })

onMounted(async () => {
  const ids = String(route.query.ids || '').split(',').filter(Boolean)
  s.value = await api.get('/settings')
  const results = await Promise.all(ids.map((id) => api.get(`/books/${id}`).catch(() => null)))
  books.value = results.filter(Boolean).map((r) => r.book)
})
</script>

<style scoped>
.print-wrap { background: #fff; min-height: 100vh; padding: 16px; }
.bar { display: flex; gap: 8px; justify-content: center; align-items: center; margin-bottom: 16px; }
.sheet { display: flex; flex-wrap: wrap; gap: 3mm; }
/* Each label is 64 x 34 mm; about 3 across on A4 */
.label { width: 64mm; height: 34mm; border: 1px dashed #999; padding: 1.5mm 2mm; display: flex; flex-direction: column; overflow: hidden; break-inside: avoid; color: #000; }
.top { display: flex; gap: 2mm; flex: 1; min-height: 0; }
.qr { width: 20mm; height: 20mm; flex-shrink: 0; }
.txt { min-width: 0; flex: 1; display: flex; flex-direction: column; font-size: 7pt; line-height: 1.25; }
.lib { font-size: 6pt; color: #333; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.acc { font-size: 12pt; font-weight: 700; }
.call { font-weight: 600; }
.ttl { overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.bar-img { height: 8mm; width: 100%; object-fit: fill; display: block; }
@page { margin: 8mm; }
</style>
