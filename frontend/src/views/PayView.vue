<template>
  <div>
    <div class="page-head">
      <div>
        <h1>Payment</h1>
        <p class="sub">Collect book fines, a membership fee or any other payment from a member.</p>
      </div>
      <button v-if="memberId" class="btn" @click="startAgain"><RotateCcw :size="16" /> Start again</button>
    </div>

    <!-- Find the member -->
    <div v-if="!memberId" class="card">
      <ScanBox label="Scan the member card" placeholder="Scan card, or start typing a name or membership no."
        hint="Matching members show while you type: click one, or use the arrow keys and Enter." suggest="member"
        @scan="onScan" @pick="(s) => (memberId = s.id)" />
      <p v-if="error" class="alert red">{{ error }}</p>
    </div>

    <PaymentPanel v-else :key="memberId" :member-id="memberId" @done="startAgain" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { RotateCcw } from 'lucide-vue-next'
import PaymentPanel from '../components/PaymentPanel.vue'
import ScanBox from '../components/ScanBox.vue'
import { api } from '../api'

const route = useRoute()
const router = useRouter()
// Opened with a member already chosen: /pay?member=ID
const memberId = ref(route.query.member || null)
const error = ref('')

async function onScan(code) {
  error.value = ''
  try {
    const r = await api.get('/circulation/scan', { code })
    if (r.type === 'member') memberId.value = r.member.id
    else error.value = 'That is not a member card.'
  } catch {
    const res = await api.get('/members', { q: code, size: 2 })
    if (res.items.length === 1) memberId.value = res.items[0].id
    else error.value = res.items.length ? 'More than one member matches. Pick one from the list while typing.' : `No member found for "${code}".`
  }
}

function startAgain() {
  memberId.value = null
  error.value = ''
  if (route.fullPath !== '/pay') router.replace('/pay')
}
</script>
