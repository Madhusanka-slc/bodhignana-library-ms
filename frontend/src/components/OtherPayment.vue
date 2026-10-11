<template>
  <!-- A payment that is not a book fine (membership fee or other), taken during Issue / Return -->
  <div class="other-pay">
    <div class="other-pay-row">
      <div class="field">
        <label :for="id + 't'">Payment for</label>
        <select :id="id + 't'" v-model="form.payment_type" @change="form.amount = usual()">
          <option v-for="k in TYPES" :key="k" :value="k">{{ PAYMENT_TYPES[k] }}</option>
        </select>
      </div>
      <div class="field">
        <label :for="id + 'a'">Amount (Rs.)</label>
        <input :id="id + 'a'" v-model.number="form.amount" type="number" min="0" @keydown.enter="save" />
      </div>
      <div class="field grow">
        <label :for="id + 'n'">Notes</label>
        <input :id="id + 'n'" v-model="form.notes" placeholder="Optional" @keydown.enter="save" />
      </div>
      <button class="btn primary" :disabled="busy || !(form.amount > 0)" @click="save"><Printer :size="16" /> Save and print receipt</button>
    </div>
    <div v-for="p in (hideList ? [] : paid)" :key="p.id" class="other-pay-done">
      <CircleCheck :size="16" />
      <span>{{ PAYMENT_TYPES[p.payment_type] || p.payment_type }} · <strong>{{ money(p.amount) }}</strong> · Receipt {{ p.receipt_no }}</span>
      <button class="icon-btn" title="Print receipt again" @click="openPrint('/print/receipt/' + p.id)"><Printer :size="16" /></button>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { CircleCheck, Printer } from 'lucide-vue-next'
import { api } from '../api'
import { appSettings, toast } from '../store'
import { PAYMENT_TYPES } from '../constants'
import { money, openPrint } from '../utils'

const props = defineProps({
  memberId: { type: Number, required: true },
  hideList: Boolean, // the page lists the receipts itself
  memberType: String, // to fill in the membership fee for this type from Settings
})
const emit = defineEmits(['paid'])
// Book fines are collected from the fines list (so they are marked paid); this is for everything else.
const TYPES = ['MEMBERSHIP', 'OTHER']
const id = 'op-' + Math.random().toString(36).slice(2, 7)
// The usual amount for the chosen kind of payment (staff can change it)
const usual = (type = form.payment_type) =>
  (type === 'MEMBERSHIP' ? Number(appSettings[`membership_fee_${(props.memberType || '').toLowerCase()}`] || 0) : 0)
const form = reactive({ payment_type: 'MEMBERSHIP', amount: usual('MEMBERSHIP'), notes: '' })
const paid = ref([]) // payments taken here in this visit
const busy = ref(false)

async function save() {
  if (busy.value || !(form.amount > 0)) return
  busy.value = true
  try {
    const p = await api.post('/payments', { member_id: props.memberId, ...form })
    paid.value.push(p)
    Object.assign(form, { payment_type: 'OTHER', amount: 0, notes: '' })
    toast(`Payment saved. Receipt ${p.receipt_no}`)
    openPrint('/print/receipt/' + p.id)
    emit('paid', p)
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    busy.value = false
  }
}
</script>
