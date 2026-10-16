<template>
  <div class="list-page">
    <div class="page-head">
      <h1>Members</h1>
      <div class="actions">
        <button class="btn" :disabled="!selected.length" @click="printCards">
          <Printer :size="16" /> Print cards ({{ selected.length }})
        </button>
        <button class="btn" :disabled="!selected.length" title="The ticked members have their cards" @click="markCards(true)">
          <CircleCheck :size="16" /> Mark card given ({{ selected.length }})
        </button>
        <button v-if="selected.length" class="btn" title="Undo: the ticked members have no card yet" @click="markCards(false)">Not given</button>
        <router-link to="/members/new" class="btn primary"><UserPlus :size="18" /> New member</router-link>
      </div>
    </div>

    <div class="card list-card">
      <div class="filters">
        <div class="grow">
          <label for="mq">Search</label>
          <div class="live-search">
            <Search :size="17" />
            <input id="mq" v-model="q" placeholder="Name, member no., NIC, phone or school" autocomplete="off"
                   @input="search.soon" @keydown.enter="search.now" />
            <button v-if="q" type="button" class="live-clear" title="Clear" @click="q = ''; search.now()"><X :size="16" /></button>
          </div>
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
        <div>
          <label for="mc">Member card</label>
          <select id="mc" v-model="card" @change="load(1)">
            <option value="">All</option>
            <option value="yes">Card given</option>
            <option value="no">Card not given</option>
          </select>
        </div>
      </div>

      <div ref="listBox" class="table-wrap list-scroll list-fit">
        <table class="table fit-table">
          <colgroup>
            <col style="width: 52px" /><col style="width: 104px" /><col /><col style="width: 92px" /><col style="width: 150px" />
            <col style="width: 116px" /><col style="width: 150px" /><col style="width: 110px" /><col style="width: 64px" />
          </colgroup>
          <thead>
            <tr><th><input type="checkbox" :checked="allChecked" title="Select all on this page" @change="toggleAll" /></th><th>Member No.</th><th>Name</th><th>Type</th><th>Telephone</th><th>Expiry date</th><th>Books now (Acc. No/s)</th><th>Status</th><th class="icon-col">Card</th></tr>
          </thead>
          <tbody>
            <tr v-for="m in items" :key="m.id" class="click" @click="$router.push('/members/' + m.id)">
              <td @click.stop><input v-model="selected" type="checkbox" :value="m.id" /></td>
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
              <td class="icon-col"><span class="done-mark" :class="{ done: m.card_done }" role="img"
                    :title="m.card_done ? 'Member card given' : 'Member card not given yet'" :aria-label="m.card_done ? 'Member card given' : 'Member card not given yet'">
                <component :is="m.card_done ? CircleCheck : CircleDashed" :size="19" /></span></td>
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
import { computed, ref } from 'vue'
import { CircleCheck, CircleDashed, Printer, Search, UserPlus, X } from 'lucide-vue-next'
import Pager from '../components/Pager.vue'
import { api } from '../api'
import { MEMBERSHIP_TYPES, typeLabel } from '../constants'
import { fmtDate, openPrint } from '../utils'
import { toast } from '../store'
import { useFitPage } from '../fitPage'
import { latestOnly, useLiveSearch } from '../liveSearch'

const q = ref('')
const type = ref('')
const active = ref('')
const card = ref('')
const items = ref([])
const total = ref(0)
const page = ref(1)
const listBox = ref(null)
// As many rows as fit on screen; Previous / Next show the next set.
const size = useFitPage(listBox, page, load)
const loaded = ref(false)

// Ticked members (kept while moving between pages), for printing cards or marking them given
const selected = ref([])
const allChecked = computed(() => items.value.length > 0 && items.value.every((m) => selected.value.includes(m.id)))
function toggleAll() {
  if (allChecked.value) selected.value = selected.value.filter((id) => !items.value.some((m) => m.id === id))
  else selected.value = [...new Set([...selected.value, ...items.value.map((m) => m.id)])]
}
async function markCards(done) {
  try {
    const r = await api.post('/members/cards', { ids: selected.value, done })
    toast(`${r.changed} member card(s) marked as ${done ? 'given' : 'not given'}`)
    selected.value = []
    load()
  } catch (e) {
    toast(e.message, 'error')
  }
}
function printCards() {
  openPrint('/print/member-cards?ids=' + selected.value.join(','))
}
// The list updates while you type (a moment after the last key), starting again from page 1.
const search = useLiveSearch(() => load(1))

const fetchMembers = latestOnly((params) => api.get('/members', params))
async function load(p = page.value) {
  page.value = p
  const r = await fetchMembers({ q: q.value, membership_type: type.value, active: active.value, card: card.value, page: p, size: size.value })
  if (!r) return // a newer search has already answered
  items.value = r.items
  total.value = r.total
  loaded.value = true
}
</script>
