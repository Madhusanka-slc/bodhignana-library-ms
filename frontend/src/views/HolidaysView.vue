<template>
  <div>
    <div class="page-head">
      <div>
        <h1>Holidays calendar</h1>
        <p class="sub">Click a day to mark it as a holiday. Click again to remove it.</p>
      </div>
      <div class="actions">
        <button class="btn" @click="changeYear(-1)">Previous year</button>
        <strong style="font-size: 20px; padding: 0 6px">{{ year }}</strong>
        <button class="btn" @click="changeYear(1)">Next year</button>
      </div>
    </div>

    <div class="alert blue">
      Holidays are not counted when working out late fines. If a due date falls on a holiday, it moves to the next open day.
    </div>

    <div class="card">
      <div class="filters">
        <div>
          <label>Mark every</label>
          <select v-model.number="bulk.weekday">
            <option v-for="(d, i) in WEEKDAYS" :key="i" :value="i">{{ d }}</option>
          </select>
        </div>
        <div class="grow"><label>As</label><input v-model="bulk.description" placeholder="e.g. Library closed" /></div>
        <button class="btn primary" @click="addBulk">Mark all in {{ year }}</button>
      </div>
    </div>

    <div class="months">
      <div v-for="(mo, mi) in months" :key="mi" class="month">
        <h3>{{ mo.name }}</h3>
        <div class="days">
          <span v-for="(d, i) in ['S', 'M', 'T', 'W', 'T', 'F', 'S']" :key="'h' + i" class="dn">{{ d }}</span>
          <span v-for="n in mo.blank" :key="'b' + n"></span>
          <button v-for="day in mo.days" :key="day.iso" class="day"
            :class="{ hol: map[day.iso], today: day.iso === todayIso }"
            :title="map[day.iso]?.description || ''" @click="toggle(day.iso)">{{ day.n }}</button>
        </div>
      </div>
    </div>

    <div class="card mt">
      <h2>Holidays in {{ year }} ({{ list.length }})</h2>
      <div v-if="!list.length" class="empty">No holidays marked yet.</div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead><tr><th>Date</th><th>Day</th><th>Holiday</th><th></th></tr></thead>
          <tbody>
            <tr v-for="h in list" :key="h.id">
              <td>{{ fmtDate(h.day) }}</td>
              <td>{{ new Date(h.day + 'T00:00:00').toLocaleDateString('en-GB', { weekday: 'long' }) }}</td>
              <td>{{ h.description }}</td>
              <td class="num"><button class="icon-btn" title="Remove" @click="remove(h)"><Trash2 :size="17" /></button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Trash2 } from 'lucide-vue-next'
import { api } from '../api'
import { toast } from '../store'
import { fmtDate, isoDate } from '../utils'

// Python weekday numbers: 0 = Monday ... 6 = Sunday
const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const year = ref(new Date().getFullYear())
const list = ref([])
const bulk = reactive({ weekday: 6, description: 'Library closed' })
const todayIso = isoDate()

const map = computed(() => Object.fromEntries(list.value.map((h) => [h.day, h])))
const months = computed(() =>
  Array.from({ length: 12 }, (_, m) => {
    const first = new Date(year.value, m, 1)
    const count = new Date(year.value, m + 1, 0).getDate()
    return {
      name: first.toLocaleDateString('en-GB', { month: 'long' }),
      blank: first.getDay(),
      days: Array.from({ length: count }, (_, i) => ({ n: i + 1, iso: isoDate(new Date(year.value, m, i + 1)) })),
    }
  }))

async function load() {
  list.value = await api.get('/holidays', { year: year.value })
}

function changeYear(d) {
  year.value += d
  load()
}

async function toggle(iso) {
  const h = map.value[iso]
  if (h) {
    if (confirm(`Remove holiday "${h.description}" on ${fmtDate(iso)}?`)) await remove(h, true)
    return
  }
  const description = prompt(`Holiday name for ${fmtDate(iso)} (e.g. Poya day):`, 'Holiday')
  if (description === null) return
  await api.post('/holidays', { day: iso, description: description || 'Holiday' })
  toast('Holiday added')
  load()
}

async function remove(h, skipConfirm = false) {
  if (!skipConfirm && !confirm(`Remove "${h.description}"?`)) return
  await api.del(`/holidays/${h.id}`)
  toast('Holiday removed')
  load()
}

async function addBulk() {
  const r = await api.post('/holidays/bulk-weekday', { year: year.value, ...bulk })
  toast(`${r.added} day(s) marked`)
  load()
}

onMounted(load)
</script>
