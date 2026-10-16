<template>
  <div class="print-wrap">
    <div v-if="!embed" class="no-print bar">
      <button class="btn primary" @click="print">Print</button>
      <button class="btn" @click="close">Close</button>
    </div>
    <div :class="{ sheet: many }">
      <div v-for="m in members" :key="m.id" class="id-card">
        <div class="head">{{ printName(s) }}<template v-if="s.library_place">, {{ s.library_place }}</template><span>Membership card</span></div>
        <div class="body">
          <img v-if="m.photo_url" :src="m.photo_url" class="photo" alt="Photo" />
          <div class="txt">
            <div class="name">{{ m.name }}</div>
            <div><b>No:</b> {{ m.membership_no }}</div>
            <div><b>Type:</b> {{ typeLabel(m.membership_type) }}</div>
            <div><b>Valid until:</b> {{ m.membership_type === 'LIFETIME' ? 'Life time' : fmtDate(m.expiry_date) }}</div>
          </div>
          <img :src="qrUrl(m.membership_no, 6)" alt="QR" @load="loadedOne" />
        </div>
        <div class="foot">Please bring this card when borrowing books.</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, qrUrl } from '../api'
import { typeLabel } from '../constants'
import { fmtDate, printName } from '../utils'

const route = useRoute()
// /print/member-card/5 prints one card; /print/member-cards?ids=5,6,7 prints them all on A4 sheets
const ids = route.params.id ? [route.params.id] : String(route.query.ids || '').split(',').filter(Boolean)
const many = ids.length > 1
const members = ref([])
const s = ref({})
const print = () => window.print()
const close = () => window.close()
const embed = route.query.embed === '1' // shown inside the app's print preview popup
// print once every QR code has loaded
let done = 0
const loadedOne = () => { if (++done === members.value.length && !embed) setTimeout(print, 200) }

onMounted(async () => {
  const [list, st] = await Promise.all([api.get('/members/cards', { ids: ids.join(',') }), api.get('/settings')])
  members.value = list
  s.value = st
})
</script>

<style scoped>
.print-wrap { background: #fff; min-height: 100vh; padding: 16px; }
.bar { display: flex; gap: 8px; justify-content: center; margin-bottom: 16px; }
/* Standard ID card size: 85.6 x 54 mm */
.id-card { width: 85.6mm; height: 54mm; border: 1px solid #3f4f86; border-radius: 3mm; overflow: hidden; margin: 0 auto; display: flex; flex-direction: column; color: #000; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.head { background: #5a6db0; color: #fff; padding: 2mm 3mm; font-weight: 700; font-size: 11pt; display: flex; justify-content: space-between; align-items: baseline; }
.head span { font-weight: 400; font-size: 7pt; }
.body { flex: 1; display: flex; align-items: center; gap: 2mm; padding: 2mm 3mm; font-size: 8pt; }
.txt { flex: 1; min-width: 0; }
.name { font-size: 11pt; font-weight: 700; margin-bottom: 1mm; }
img { width: 27mm; height: 27mm; }
.photo { width: 20mm; height: 25mm; object-fit: cover; border: 1px solid #b1b8cd; border-radius: 1.5mm; }
/* many cards: two columns on A4, 10 per sheet, with a dashed cut line around each */
.sheet { display: grid; grid-template-columns: repeat(2, 85.6mm); gap: 4mm 6mm; justify-content: center; }
.sheet .id-card { margin: 0; break-inside: avoid; outline: 0.3mm dashed #b1b8cd; outline-offset: 1.5mm; }
@media print {
  .print-wrap { padding: 0; min-height: 0; }
  .sheet { padding-top: 2mm; }
}
@page { size: A4 portrait; margin: 10mm; }
.foot { font-size: 6.5pt; text-align: center; padding: 1mm; border-top: 1px solid #dde3f4; color: #333; }
</style>
