<template>
  <!-- Everything about paying for one member: what is owed (issue fees, late / damaged / missing charges),
       extra charges staff can add, other payments, and the receipts of this visit.
       Used on the Payment screen and as the Payment step of Issue book. -->
  <div v-if="st" class="card pay-step">
    <!-- Who and how much: stays in view while the list below scrolls (inside Issue book) -->
    <div class="pay-top">
      <div class="ret-head">
        <div>
          <h2 style="margin: 0">{{ st.member.name }}</h2>
          <div class="muted small">{{ st.member.membership_no }} · {{ typeLabel(st.member.membership_type) }}
            · {{ st.member.membership_type === 'LIFETIME' ? 'Life time member' : st.member.expiry_date ? (st.member.is_expired ? 'membership expired ' : 'membership until ') + fmtDate(st.member.expiry_date) : 'no expiry date' }}</div>
        </div>
        <router-link v-if="!flow" :to="'/members/' + st.member.id" class="btn sm"><UserRound :size="15" /> Open profile</router-link>
      </div>

      <div class="pay-sum">
        <div class="pay-sum-tile" :class="unpaid > 0 ? 'owe' : 'ok'">
          <component :is="unpaid > 0 ? CircleAlert : Check" :size="20" />
          <span><small>To pay now</small><strong>{{ money(unpaid) }}</strong>
            <small>{{ unpaid > 0 ? st.fines.length + ' book(s) with charges' : 'Nothing owed' }}</small></span>
        </div>
        <div class="pay-sum-tile">
          <Wallet :size="20" />
          <span><small>Paid in this visit</small><strong>{{ money(paidTotal) }}</strong>
            <small>{{ paid.length ? paid.length + ' receipt(s)' : 'No payment yet' }}</small></span>
        </div>
        <div class="pay-sum-tile">
          <BookOpen :size="20" />
          <span><small>Books with the member</small><strong>{{ st.loans.length }} of {{ st.max_books }}</strong>
            <small>{{ st.can_borrow }} card(s) free</small></span>
        </div>
      </div>
    </div>

    <!-- Worked out by the system: issue fees and penalties not paid yet -->
    <h3 class="pay-h">To pay (worked out automatically, paid all together)</h3>
    <p v-if="!st.fines.length" class="pay-none"><Check :size="16" /> Nothing to pay.</p>
    <table v-else class="table report-table">
      <colgroup><col style="width: 124px" /><col style="width: 108px" /><col /><col style="width: 30%" /><col style="width: 150px" /></colgroup>
      <thead><tr><th>Reference</th><th>Acc. No.</th><th>Book</th><th>For</th><th class="num">To pay</th></tr></thead>
      <tbody>
        <tr v-for="l in st.fines" :key="l.id">
          <td><span class="ref-tag">{{ l.ref || '-' }}</span></td>
          <td><span class="code-tag">{{ l.book.acc_no }}</span></td>
          <td :title="l.book.title">{{ l.book.title }}</td>
          <td :title="dueText(l)">{{ dueText(l) }}</td>
          <td class="num"><strong>{{ money(l.balance) }}</strong></td>
        </tr>
        <tr><td colspan="4" class="totalrow"><strong>Total to pay</strong></td><td class="num totalrow total-big">{{ money(unpaid) }}</td></tr>
      </tbody>
    </table>

    <!-- Only when a book of this member was marked damaged or missing at a return:
         staff can add a further charge; the amount comes from the book's price -->
    <template v-if="hasMarks">
    <h3 class="pay-h">Add a charge (damaged or missing book) <span class="pay-opt">optional</span></h3>
    <div v-if="!chargeBooks.length && !st.loans.length" class="muted small">This member has no books now and none returned in the last 60 days.</div>
    <div v-else class="other-pay-row">
      <div class="field">
        <label :for="id + 'k'">Charge for</label>
        <select :id="id + 'k'" v-model="charge.kind" @change="charge.loan_id = ''">
          <option value="damage">Damaged book</option>
          <option value="lost">Missing book</option>
        </select>
      </div>
      <div class="field grow">
        <label :for="id + 'b'">Book</label>
        <select :id="id + 'b'" v-model="charge.loan_id">
          <option value="">Choose the book</option>
          <option v-for="l in chargeBooks" :key="l.id" :value="l.id">
            {{ l.book.acc_no }} · {{ l.book.title }}{{ l.return_date ? ' (returned ' + fmtDate(l.return_date) + ')' : ' (with the member)' }}
          </option>
        </select>
      </div>
      <div class="field">
        <label :for="id + 'm'">Amount (Rs.)</label>
        <input :id="id + 'm'" v-model.number="charge.amount" type="number" min="0" :disabled="!charge.loan_id" />
      </div>
      <button class="btn" :disabled="busy || !charge.loan_id || !(charge.amount > 0)" @click="addCharge"><Plus :size="16" /> Add charge</button>
    </div>
    <p v-if="chargeHelp" class="muted small" style="margin: 6px 0 0">{{ chargeHelp }}</p>
    </template>

    <!-- Not in the Issue book flow: there only the book charges are paid -->
    <template v-if="!flow">
      <h3 class="pay-h">Other payment (membership fee or other)</h3>
      <OtherPayment :member-id="st.member.id" :member-type="st.member.membership_type" hide-list @paid="(p) => paid.push(p)" />
    </template>

    <template v-if="paid.length">
      <h3 class="pay-h">Paid in this visit</h3>
      <div v-for="r in receipts" :key="r.receipt_no" class="other-pay-done">
        <CircleCheck :size="16" />
        <span>Receipt {{ r.receipt_no }} · <strong>{{ money(r.total) }}</strong> · {{ r.what }}</span>
        <button class="icon-btn" title="Print receipt again" @click="openPrint('/print/receipt/' + r.id)"><Printer :size="16" /></button>
      </div>
    </template>

    <!-- One button pays everything owed. (Inside Issue book the buttons are in the bar at the bottom of the page.) -->
    <div v-if="!flow" class="pay-actions">
      <router-link v-if="st.loans.length" :to="'/return?member=' + st.member.id" class="btn"><ArrowDownLeft :size="17" /> Return books</router-link>
      <router-link v-if="st.can_borrow > 0 && !st.blocks.length" :to="'/issue?member=' + st.member.id" class="btn"><ArrowUpRight :size="17" /> Issue books</router-link>
      <button v-if="unpaid > 0" class="btn success big" :disabled="busy" @click="collectAll"><Printer :size="20" /> Collect all · {{ money(unpaid) }}</button>
      <button class="btn big" :class="{ primary: !(unpaid > 0) }" @click="emit('done')"><Check :size="20" /> {{ doneLabel }}</button>
    </div>
  </div>
  <p v-else-if="error" class="alert red">{{ error }}</p>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ArrowDownLeft, ArrowUpRight, BookOpen, Check, CircleAlert, CircleCheck, Plus, Printer, UserRound, Wallet } from 'lucide-vue-next'
import OtherPayment from './OtherPayment.vue'
import { api } from '../api'
import { appSettings, toast } from '../store'
import { PAYMENT_TYPES, typeLabel } from '../constants'
import { dueText, fmtDate, money, openPrint } from '../utils'

const props = defineProps({
  memberId: { type: [Number, String], required: true },
  flow: Boolean, // a step inside Issue book: only the Done button, no links to other screens
  doneLabel: { type: String, default: 'Done' },
})
const emit = defineEmits(['done', 'back'])
const id = 'pp-' + Math.random().toString(36).slice(2, 7)
const st = ref(null) // the member, their books now, books returned lately, and what they owe
const error = ref('')
const busy = ref(false)
const paid = ref([]) // every payment taken in this visit
const unpaid = computed(() => (st.value?.fines || []).reduce((s, l) => s + l.balance, 0))
// A book of this member was marked damaged or missing (at a return, or by a charge already added)
const hasMarks = computed(() => [...(st.value?.loans || []), ...(st.value?.recent_returns || []), ...(st.value?.fines || [])]
  .some((l) => l.is_damaged || l.is_lost))
// Payments of this visit, one line per receipt
const receipts = computed(() => {
  const byNo = new Map()
  for (const p of paid.value) {
    const r = byNo.get(p.receipt_no) || { receipt_no: p.receipt_no, id: p.id, total: 0, kinds: new Set(), books: 0 }
    r.total += Number(p.amount)
    r.kinds.add(PAYMENT_TYPES[p.payment_type] || p.payment_type)
    if (p.book_acc_no) r.books += 1
    byNo.set(p.receipt_no, r)
  }
  return [...byNo.values()].map((r) => ({ ...r, what: [...r.kinds].join(', ') + (r.books ? ` · ${r.books} book(s)` : '') }))
})
const paidTotal = computed(() => paid.value.reduce((t, p) => t + Number(p.amount), 0))

// ---- extra charge: damaged (a book they have, or returned lately) or missing (a book they still have) ----
const charge = reactive({ kind: 'damage', loan_id: '', amount: 0 })
const chargeBooks = computed(() => (charge.kind === 'lost' ? st.value.loans : [...st.value.loans, ...(st.value.recent_returns || [])]))
const chargeLoan = computed(() => chargeBooks.value.find((l) => l.id === charge.loan_id))
const multiplier = computed(() => Number(appSettings[charge.kind === 'lost' ? 'lost_multiplier' : 'damage_multiplier'] ?? 2) || 0)
// The amount is worked out from the book's price as soon as the book is chosen (staff can still change it)
watch(() => [charge.kind, charge.loan_id], () => {
  charge.amount = chargeLoan.value ? Math.round(Number(chargeLoan.value.book.price || 0) * multiplier.value * 100) / 100 : 0
})
const chargeHelp = computed(() => {
  if (!chargeLoan.value) return `${charge.kind === 'lost' ? 'Missing' : 'Damaged'} book charge = ${multiplier.value} × the book's price (set in Settings).`
  const price = Number(chargeLoan.value.book.price || 0)
  if (!price) return 'This book has no price saved, so type the amount.'
  return `${multiplier.value} × book price ${money(price)} = ${money(price * multiplier.value)}.`
    + (charge.kind === 'lost' ? ' The book is marked Lost and taken off the member.' : '')
})

async function load() {
  try {
    st.value = await api.get(`/circulation/member-status/${props.memberId}`)
  } catch (e) {
    error.value = e.message
  }
}

async function addCharge() {
  busy.value = true
  try {
    await api.post('/circulation/charge', { loan_id: charge.loan_id, kind: charge.kind, amount: charge.amount })
    toast('Charge added')
    Object.assign(charge, { loan_id: '', amount: 0 })
    await load()
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    busy.value = false
  }
}

// Collect what is owed for one or more books (linked to the book and its reference), then print
async function collect(fines) {
  busy.value = true
  try {
    // everything owed, paid together on ONE receipt (one line per book inside it)
    const ps = await api.post('/payments/collect', { member_id: st.value.member.id, loan_ids: fines.map((l) => l.id) })
    paid.value.push(...ps)
    toast(`Payment saved. Receipt ${ps[0].receipt_no}`)
    openPrint('/print/receipt/' + ps[0].id)
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    await load()
    busy.value = false
  }
}

const collectAll = () => collect(st.value.fines)
// For Issue book, which shows the buttons itself
defineExpose({ unpaid, busy, collectAll, loaded: computed(() => !!st.value) })

onMounted(load)
</script>
