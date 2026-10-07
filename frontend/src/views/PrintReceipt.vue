<template>
  <div class="print-wrap">
    <div class="no-print bar">
      <button class="btn primary" @click="print">Print</button>
      <button class="btn" @click="close">Close</button>
    </div>
    <div v-if="p" class="receipt">
      <div class="c">
        <strong class="lib">{{ s.library_name }}</strong>
        <div v-if="s.library_address">{{ s.library_address }}</div>
        <div v-if="s.library_phone">Tel: {{ s.library_phone }}</div>
      </div>
      <div class="line"></div>
      <div class="c title">PAYMENT RECEIPT</div>
      <table>
        <tr><td>Receipt No</td><td>{{ p.receipt_no }}</td></tr>
        <tr><td>Date</td><td>{{ fmtDateTime(p.paid_at) }}</td></tr>
        <tr><td>Member No</td><td>{{ p.member_no }}</td></tr>
        <tr><td>Name</td><td>{{ p.member_name }}</td></tr>
        <tr><td>Payment for</td><td>{{ PAYMENT_TYPES[p.payment_type] || p.payment_type }}</td></tr>
        <tr v-if="p.book_title"><td>Book</td><td>{{ p.book_acc_no }} - {{ p.book_title }}</td></tr>
        <tr v-if="p.notes"><td>Details</td><td>{{ p.notes }}</td></tr>
      </table>
      <div class="line"></div>
      <div class="amount"><span>AMOUNT</span><span>{{ money(p.amount) }}</span></div>
      <div class="line"></div>
      <div>Received by: {{ p.received_by }}</div>
      <div class="c foot">{{ s.receipt_footer }}</div>
    </div>
    <p v-else-if="error" class="alert red">{{ error }}</p>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { PAYMENT_TYPES } from '../constants'
import { fmtDateTime, money } from '../utils'

const route = useRoute()
const p = ref(null)
const s = ref({})
const error = ref('')
const print = () => window.print()
const close = () => window.close()

onMounted(async () => {
  try {
    ;[p.value, s.value] = await Promise.all([api.get(`/payments/${route.params.id}`), api.get('/settings')])
    await nextTick()
    setTimeout(print, 300)
  } catch (e) {
    error.value = e.message
  }
})
</script>

<style scoped>
.print-wrap { background: #fff; min-height: 100vh; padding: 16px; }
.bar { display: flex; gap: 8px; justify-content: center; margin-bottom: 16px; }
/* 80 mm receipt paper; also fine on A4 */
.receipt { width: 76mm; margin: 0 auto; font-size: 12px; line-height: 1.45; color: #000; }
.c { text-align: center; }
.lib { font-size: 15px; }
.title { font-weight: 700; letter-spacing: 1px; margin: 4px 0; }
.line { border-top: 1px dashed #000; margin: 6px 0; }
table { width: 100%; border-collapse: collapse; }
td { padding: 1px 0; vertical-align: top; }
td:first-child { width: 28mm; }
.amount { display: flex; justify-content: space-between; font-size: 16px; font-weight: 700; }
.foot { margin-top: 8px; }
@page { margin: 4mm; }
</style>
