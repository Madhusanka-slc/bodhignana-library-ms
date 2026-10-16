<template>
  <div class="print-wrap" :class="{ embed }">
    <div v-if="!embed" class="no-print bar">
      <button class="btn primary" @click="print">Print</button>
      <button class="btn" @click="close">Close</button>
    </div>
    <!-- One receipt. Payments for several books on it are shown as lines, e.g. "Book issue fee  2 x Rs. 2.00 = Rs. 4.00", then the total. -->
    <div v-for="r in receipts" :key="r.receipt_no" ref="papers" class="receipt">
      <div class="c">
        <strong class="lib">{{ printName(s) }}</strong>
        <div v-if="s.library_place">{{ s.library_place }}</div>
        <div v-if="s.library_address">{{ s.library_address }}</div>
        <div v-if="s.library_phone">Tel: {{ s.library_phone }}</div>
      </div>
      <div class="line"></div>
      <div class="c title">PAYMENT RECEIPT</div>
      <table>
        <tr><td>Receipt No</td><td>{{ r.receipt_no }}</td></tr>
        <tr><td>Date</td><td>{{ fmtDateTime(r.paid_at) }}</td></tr>
        <tr><td>Member No</td><td>{{ r.member_no }}</td></tr>
        <tr><td>Name</td><td>{{ r.member_name }}</td></tr>
        <tr v-if="r.refs"><td>Reference</td><td>{{ r.refs }}</td></tr>
      </table>
      <div class="line"></div>
      <div v-for="(g, i) in r.lines" :key="i" class="item">
        <div class="item-head"><span>{{ g.label }}<span v-if="g.calc" class="calc">&nbsp;({{ g.calc }})</span></span><span>{{ money(g.total) }}</span></div>
        <div v-for="(b, j) in g.books" :key="j" class="item-book">
          <span class="acc">Acc. {{ b.acc }}</span>
          <span class="ttl">{{ b.title }}<template v-if="b.why"> · {{ b.why }}</template></span>
          <span v-if="g.books.length > 1" class="amt">{{ money(b.amount) }}</span>
        </div>
        <div v-if="g.note" class="item-note">{{ g.note }}</div>
      </div>
      <div class="line"></div>
      <div class="amount"><span>TOTAL</span><span>{{ money(r.total) }}</span></div>
      <div class="line"></div>
      <div>Received by: {{ r.received_by }}</div>
      <div class="c foot">{{ s.receipt_footer }}</div>
    </div>
    <p v-if="error" class="alert red">{{ error }}</p>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { PAYMENT_TYPES } from '../constants'
import { fmtDateTime, money, printName } from '../utils'

const route = useRoute()
const list = ref([]) // every payment on the receipt(s) being printed

// One receipt per receipt number. Issue fees are added up into one line ("2 x Rs. 2.00");
// other charges get a line each, with the book and the reason.
const receipts = computed(() => {
  const byNo = new Map()
  for (const p of list.value) {
    if (!byNo.has(p.receipt_no)) byNo.set(p.receipt_no, [])
    byNo.get(p.receipt_no).push(p)
  }
  return [...byNo.entries()].map(([no, ps]) => {
    // One block per kind of charge (issue fees first), and inside it one line per book
    const order = ['ISSUE_FEE', 'LATE_FINE', 'DAMAGE_FINE', 'LOST_FINE', 'FINE', 'MEMBERSHIP', 'OTHER']
    const types = [...new Set(ps.map((p) => p.payment_type))].sort((a, b) => order.indexOf(a) - order.indexOf(b))
    const lines = types.map((type) => {
      const group = ps.filter((p) => p.payment_type === type)
      const withBook = group.filter((p) => p.book_acc_no)
      const each = Number(group[0].amount)
      const same = group.every((p) => Number(p.amount) === each)
      return {
        label: PAYMENT_TYPES[type] || type,
        total: group.reduce((t, p) => t + Number(p.amount), 0),
        // e.g. "2 x Rs. 2.00" for issue fees
        calc: type === 'ISSUE_FEE' && group.length > 1 && same ? `${group.length} x ${money(each)}` : '',
        books: withBook.map((p) => ({
          acc: p.book_acc_no, title: p.book_title, amount: Number(p.amount),
          why: type === 'ISSUE_FEE' ? '' : p.notes,
        })),
        note: group.filter((p) => !p.book_acc_no).map((p) => p.notes).filter(Boolean).join('; '),
      }
    })
    const first = ps[0]
    return {
      receipt_no: no, paid_at: first.paid_at, member_no: first.member_no, member_name: first.member_name, received_by: first.received_by,
      refs: [...new Set(ps.map((p) => p.ref).filter(Boolean))].join(', '),
      total: ps.reduce((t, p) => t + Number(p.amount), 0),
      lines,
    }
  })
})
const s = ref({})
const error = ref('')
const embed = route.query.embed === '1' // shown inside the app's print preview popup
const print = () => window.print()
const papers = ref([])

// 80 mm receipt roll: each receipt is printed on its own page, 80 mm wide and as long as the receipt
function setPageSizes() {
  const mm = (px) => Math.ceil((px * 25.4) / 96) + 2
  const css = papers.value.map((el, i) => {
    el.style.page = 'receipt' + i
    return `@page receipt${i} { size: 80mm ${mm(el.offsetHeight)}mm; margin: 0; }`
  })
  let tag = document.getElementById('receipt-page-size')
  if (!tag) {
    tag = document.createElement('style')
    tag.id = 'receipt-page-size'
    document.head.appendChild(tag)
  }
  tag.textContent = css.join('\n')
}
const close = () => window.close()

onMounted(async () => {
  try {
    const ids = String(route.params.id).split(',').filter(Boolean)
    const [firsts, settings] = await Promise.all([Promise.all(ids.map((id) => api.get(`/payments/${id}`))), api.get('/settings')])
    s.value = settings
    // bring in every line of each receipt (one receipt can hold several books)
    const numbers = [...new Set(firsts.map((p) => p.receipt_no))]
    list.value = (await Promise.all(numbers.map((no) => api.get('/payments', { receipt_no: no })))).flat()
    await nextTick()
    setPageSizes()
    if (!embed) setTimeout(print, 300)
  } catch (e) {
    error.value = e.message
  }
})
</script>

<style scoped>
.print-wrap { background: #fff; min-height: 100vh; padding: 16px; }
/* inside the app's preview popup: the receipt shows as a strip of roll paper */
.print-wrap.embed { background: #e6e9f1; padding: 18px 0; }
.bar { display: flex; gap: 8px; justify-content: center; margin-bottom: 16px; }
/* 80 mm receipt roll: 72 mm of print in the middle */
.receipt { box-sizing: border-box; width: 80mm; margin: 0 auto; padding: 4mm; background: #fff; font-size: 11.5px; line-height: 1.4; color: #000; }
.embed .receipt { box-shadow: 0 4px 16px rgba(36, 48, 84, .18); }
.receipt + .receipt { margin-top: 8mm; }
.c { text-align: center; }
.lib { font-size: 14px; }
.title { font-weight: 700; letter-spacing: 1px; margin: 4px 0; }
.line { border-top: 1px dashed #000; margin: 5px 0; }
table { width: 100%; border-collapse: collapse; }
td { padding: 1px 0; vertical-align: top; }
td:first-child { width: 24mm; }
.amount { display: flex; justify-content: space-between; font-size: 15px; font-weight: 700; }
.item { margin: 4px 0; }
.item-head { display: flex; justify-content: space-between; gap: 8px; font-weight: 700; }
.item-head .calc { font-weight: 400; }
.item-book { display: flex; gap: 6px; padding-left: 6px; font-size: 10.5px; line-height: 1.35; }
.item-book .acc { flex-shrink: 0; font-weight: 700; }
.item-book .ttl { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.item-book .amt { flex-shrink: 0; }
.item-note { padding-left: 6px; font-size: 10.5px; }
.foot { margin-top: 8px; }
@media print {
  .print-wrap, .print-wrap.embed { padding: 0; min-height: 0; background: #fff; }
  .receipt { box-shadow: none !important; }
  .receipt + .receipt { margin-top: 0; break-before: page; }
}
</style>
