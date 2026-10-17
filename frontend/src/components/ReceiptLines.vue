<template>
  <!-- The lines of one receipt. A group receipt has a heading and a subtotal for each member. -->
  <table class="table report-table rs-lines">
    <colgroup><col style="width: 190px" /><col style="width: 96px" /><col /><col style="width: 140px" /></colgroup>
    <thead><tr><th>For</th><th>Acc. No.</th><th>Book / details</th><th class="num">Amount</th></tr></thead>
    <tbody v-for="m in receipt.members" :key="m.member_id">
      <tr v-if="receipt.isGroup" class="rs-member">
        <td colspan="3"><UserRound :size="15" /> <strong>{{ m.member_name }}</strong> <span class="code-tag">{{ m.member_no }}</span></td>
        <td class="num"><strong>{{ money(m.total) }}</strong></td>
      </tr>
      <tr v-for="p in m.lines" :key="p.id">
        <td :class="{ 'rs-in': receipt.isGroup }">{{ PAYMENT_TYPES[p.payment_type] || p.payment_type }}</td>
        <td><span v-if="p.book_acc_no" class="code-tag">{{ p.book_acc_no }}</span><span v-else>-</span></td>
        <td :title="[p.book_title, p.notes].filter(Boolean).join(' · ')">{{ [p.book_title, p.payment_type === 'ISSUE_FEE' ? '' : p.notes].filter(Boolean).join(' · ') || '-' }}</td>
        <td class="num">{{ money(p.amount) }}</td>
      </tr>
    </tbody>
    <tbody>
      <tr><td colspan="3" class="totalrow"><strong>Total{{ receipt.isGroup ? ` · ${receipt.members.length} members` : '' }}</strong></td><td class="num totalrow total-big">{{ money(receipt.total) }}</td></tr>
    </tbody>
  </table>
</template>

<script setup>
import { UserRound } from 'lucide-vue-next'
import { PAYMENT_TYPES } from '../constants'
import { money } from '../utils'

defineProps({ receipt: { type: Object, required: true } })
</script>
