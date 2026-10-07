<template>
  <div>
    <div class="page-head">
      <h1>Payments</h1>
      <button class="btn primary" @click="openNew"><Plus :size="18" /> New payment</button>
    </div>

    <div class="card">
      <div class="filters">
        <div><label>From</label><input v-model="from" type="date" @change="load" /></div>
        <div><label>To</label><input v-model="to" type="date" @change="load" /></div>
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
              <td>{{ PAYMENT_TYPES[p.payment_type] || p.payment_type }}<div v-if="p.book_title" class="muted small">{{ p.book_acc_no }} · {{ p.book_title }}</div></td>
              <td>{{ p.received_by }}</td>
              <td class="num">{{ money(p.amount) }}</td>
              <td class="num"><button class="icon-btn" title="Print receipt" @click="openPrint('/print/receipt/' + p.id)"><Printer :size="17" /></button></td>
            </tr>
          </tbody>
        </table>
        <div v-if="!items.length" class="empty">No payments in these dates.</div>
      </div>
    </div>

    <Modal v-if="show" title="New payment" @close="show = false">
      <ScanBox label="Member" placeholder="Scan member card or type membership no." button-text="Find" @scan="findMember" />
      <p v-if="memberError" class="alert red">{{ memberError }}</p>
      <p v-if="member" class="alert blue">{{ member.name }} ({{ member.membership_no }})</p>
      <div class="form-grid mt">
        <div class="field">
          <label>Payment for</label>
          <select v-model="form.payment_type">
            <option v-for="(label, k) in PAYMENT_TYPES" :key="k" :value="k">{{ label }}</option>
          </select>
        </div>
        <div class="field"><label>Amount (Rs.)</label><input v-model.number="form.amount" type="number" min="0" /></div>
        <div class="field wide"><label>Notes</label><input v-model="form.notes" /></div>
      </div>
      <template #footer>
        <button class="btn" @click="show = false">Cancel</button>
        <button class="btn primary" :disabled="!member" @click="save"><Printer :size="16" /> Save and print receipt</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Plus, Printer } from 'lucide-vue-next'
import Modal from '../components/Modal.vue'
import ScanBox from '../components/ScanBox.vue'
import { api } from '../api'
import { toast } from '../store'
import { PAYMENT_TYPES } from '../constants'
import { fmtDateTime, isoDate, money, openPrint } from '../utils'

const now = new Date()
const from = ref(isoDate(new Date(now.getFullYear(), now.getMonth(), 1)))
const to = ref(isoDate())
const ptype = ref('')
const items = ref([])
const total = ref(0)
const show = ref(false)
const member = ref(null)
const memberError = ref('')
const form = reactive({ payment_type: 'MEMBERSHIP', amount: 0, notes: '' })

async function load() {
  const r = await api.get('/reports/payments', { from_date: from.value, to_date: to.value, payment_type: ptype.value })
  items.value = [...r.items].reverse()
  total.value = r.total
}

function openNew() {
  member.value = null
  memberError.value = ''
  Object.assign(form, { payment_type: 'MEMBERSHIP', amount: 0, notes: '' })
  show.value = true
}

async function findMember(code) {
  memberError.value = ''
  member.value = null
  try {
    const r = await api.get('/circulation/scan', { code })
    if (r.type === 'member') member.value = r.member
    else memberError.value = 'That is not a member card.'
  } catch (e) {
    memberError.value = e.message
  }
}

async function save() {
  try {
    const p = await api.post('/payments', { member_id: member.value.id, ...form })
    show.value = false
    toast(`Payment saved. Receipt ${p.receipt_no}`)
    openPrint('/print/receipt/' + p.id)
    load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

onMounted(load)
</script>
