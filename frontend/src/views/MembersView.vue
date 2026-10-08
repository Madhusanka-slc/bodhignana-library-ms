<template>
  <div class="list-page">
    <div class="page-head">
      <h1>Members</h1>
      <router-link to="/members/new" class="btn primary"><UserPlus :size="18" /> New member</router-link>
    </div>

    <div class="card list-card">
      <div class="filters">
        <div class="grow">
          <label for="mq">Search</label>
          <input id="mq" v-model="q" placeholder="Name, membership no., NIC, phone or school" @keydown.enter="load(1)" />
        </div>
        <div>
          <label for="mt">Membership type</label>
          <select id="mt" v-model="type" @change="load(1)">
            <option value="">All types</option>
            <option v-for="t in MEMBERSHIP_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
        <div>
          <label for="ma">Status</label>
          <select id="ma" v-model="active" @change="load(1)">
            <option value="">All</option>
            <option value="true">Active</option>
            <option value="false">Not active</option>
          </select>
        </div>
        <button class="btn primary" @click="load(1)"><Search :size="16" /> Search</button>
      </div>

      <div ref="listBox" class="table-wrap list-scroll list-fit">
        <table class="table fit-table">
          <colgroup>
            <col style="width: 104px" /><col /><col style="width: 92px" /><col style="width: 150px" />
            <col style="width: 116px" /><col style="width: 170px" /><col style="width: 116px" />
          </colgroup>
          <thead>
            <tr><th>Member No.</th><th>Name</th><th>Type</th><th>Telephone</th><th>Expiry date</th><th>Books now (Acc. No/s)</th><th>Status</th></tr>
          </thead>
          <tbody>
            <tr v-for="m in items" :key="m.id" class="click" @click="$router.push('/members/' + m.id)">
              <td><span class="code-tag">{{ m.membership_no }}</span></td>
              <td :title="m.school ? `${m.name} - ${m.school}` : m.name">{{ m.name }}</td>
              <td>{{ typeLabel(m.membership_type) }}</td>
              <td :title="m.telephone">{{ m.telephone || '-' }}</td>
              <td>{{ m.membership_type === 'LIFETIME' ? 'Life time' : fmtDate(m.expiry_date) }}</td>
              <td :title="m.borrowed_acc_nos">{{ m.borrowed_acc_nos || '-' }}</td>
              <td>
                <span v-if="!m.is_active" class="badge gray">Not active</span>
                <span v-else-if="m.is_expired" class="badge red">Expired</span>
                <span v-else class="badge green">Active</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="loaded && !items.length" class="empty">No members found.</div>
      </div>
      <Pager :page="page" :size="size" :total="total" @update:page="load" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Search, UserPlus } from 'lucide-vue-next'
import Pager from '../components/Pager.vue'
import { api } from '../api'
import { MEMBERSHIP_TYPES, typeLabel } from '../constants'
import { fmtDate } from '../utils'
import { useFitPage } from '../fitPage'

const q = ref('')
const type = ref('')
const active = ref('')
const items = ref([])
const total = ref(0)
const page = ref(1)
const listBox = ref(null)
// As many rows as fit on screen; Previous / Next show the next set.
const size = useFitPage(listBox, page, load)
const loaded = ref(false)

async function load(p = page.value) {
  page.value = p
  const r = await api.get('/members', { q: q.value, membership_type: type.value, active: active.value, page: p, size: size.value })
  items.value = r.items
  total.value = r.total
  loaded.value = true
}
</script>
