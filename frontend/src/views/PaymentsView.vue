<template>
  <div>
    <div class="page-head">
      <h1>Payment records</h1>
      <router-link to="/pay" class="btn primary"><Plus :size="18" /> New payment</router-link>
    </div>

    <div class="card">
      <div class="filters">
        <div><label>From</label><DateInput v-model="from" @change="load" /></div>
        <div><label>To</label><DateInput v-model="to" @change="load" /></div>
        <div>
          <label>Type</label>
          <select v-model="ptype" @change="load">
            <option value="">All types</option>
            <option v-for="(label, k) in PAYMENT_TYPES" :key="k" :value="k">{{ label }}</option>
          </select>
        </div>
        <div style="flex: 0 0 auto">
          <label>Total</label>
          <div class="total-big" style="font-size: 22px">{{ money(total) }}</div>
        </div>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Receipt</th><th>Date</th><th>Member</th><th>For</th><th>Received by</th><th class="num">Amount</th><th></th></tr></thead>
          <tbody>
            <tr v-for="p in items" :key="p.id">
              <td>{{ p.receipt_no }}</td>
              <td>{{ fmtDateTime(p.paid_at) }}</td>
              <td><router-link :to="'/members/' + p.member_id">{{ p.member_name }}</router-link> <span class="muted">({{ p.member_no }})</span></td>
              <td>{{ PAYMENT_TYPES[p.payment_type] || p.payment_type }}<div v-if="p.book_title" class="muted small">{{ p.book_acc_no }} · {{ p.book_title }}</div><div v-if="p.ref" class="muted small">Ref {{ p.ref }}</div></td>
              <td>{{ p.received_by }}</td>
              <td class="num">{{ money(p.amount) }}</td>
              <td class="num"><button class="icon-btn" title="Print receipt" @click="openPrint('/print/receipt/' + p.id)"><Printer :size="17" /></button></td>
            </tr>
          </tbody>
        </table>
        <div v-if="!items.length" class="empty">No payments in these dates.</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Plus, Printer } from 'lucide-vue-next'
import DateInput from '../components/DateInput.vue'
import { api } from '../api'
import { PAYMENT_TYPES } from '../constants'
import { fmtDateTime, isoDate, money, openPrint } from '../utils'

const now = new Date()
const from = ref(isoDate(new Date(now.getFullYear(), now.getMonth(), 1)))
const to = ref(isoDate())
const ptype = ref('')
const items = ref([])
const total = ref(0)

async function load() {
  const r = await api.get('/reports/payments', { from_date: from.value, to_date: to.value, payment_type: ptype.value })
  items.value = [...r.items].reverse()
  total.value = r.total
}

onMounted(load)
</script>
