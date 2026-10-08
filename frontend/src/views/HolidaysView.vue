<template>
  <div class="list-page hol-page">
    <!-- Top: stays in place -->
    <div class="page-head">
      <div>
        <h1>Holidays calendar</h1>
        <p class="sub">Click a day to mark it as a holiday, click it again to remove it. Holidays are not counted for late fines.</p>
      </div>
      <div class="actions">
        <button class="btn" @click="changeYear(-1)"><ChevronLeft :size="16" /> {{ year - 1 }}</button>
        <strong class="hol-year">{{ year }}</strong>
        <button class="btn" @click="changeYear(1)">{{ year + 1 }} <ChevronRight :size="16" /></button>
      </div>
    </div>

    <div class="card hol-tools">
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
      <div class="hol-legend">
        <span v-for="t in TYPES" :key="t.key"><i class="day" :class="['hol', t.cls]"></i>{{ t.label }}</span>
        <span><i class="day legend-today"></i>Today</span>
      </div>
    </div>

    <!-- Middle: four months in a row -->
    <div class="hol-body">
      <div class="months4">
        <div v-for="mo in visibleMonths" :key="mo.index" class="month" :class="{ current: mo.index === selMonth }"
             @click="selMonth = mo.index">
          <h3>{{ mo.name }} <small v-if="mo.count">{{ mo.count }} holiday{{ mo.count > 1 ? 's' : '' }}</small></h3>
          <div class="days">
            <span v-for="(d, i) in ['S', 'M', 'T', 'W', 'T', 'F', 'S']" :key="'h' + i" class="dn">{{ d }}</span>
            <span v-for="n in mo.blank" :key="'b' + n"></span>
            <button v-for="day in mo.days" :key="day.iso" class="day" :data-iso="day.iso"
              :class="[{ hol: map[day.iso], today: day.iso === todayIso }, map[day.iso] ? typeOf(map[day.iso].description).cls : '']"
              :title="map[day.iso]?.description || ''" @click="toggle(day.iso)">{{ day.n }}</button>
          </div>
        </div>
      </div>

      <!-- Holidays of the selected month, side by side -->
      <div class="card hol-strip">
        <h2>Holidays in {{ MONTH_NAMES[selMonth] }} {{ year }} <span class="badge blue">{{ monthHolidays.length }}</span></h2>
        <div v-if="!monthHolidays.length" class="muted hol-strip-empty">No holidays marked in {{ MONTH_NAMES[selMonth] }}. Click a day above to add one.</div>
        <div v-else class="hol-strip-row">
          <div v-for="h in monthHolidays" :key="h.id" class="hol-chip">
            <div class="hol-row-date">
              <strong>{{ new Date(h.day + 'T00:00:00').getDate() }}</strong>
              <span>{{ new Date(h.day + 'T00:00:00').toLocaleDateString('en-GB', { month: 'short' }) }}</span>
            </div>
            <div class="hol-row-text">
              <span class="hol-tag" :class="typeOf(h.description).cls">{{ typeOf(h.description).label }}</span>
              <span class="muted small">{{ new Date(h.day + 'T00:00:00').toLocaleDateString('en-GB', { weekday: 'long' }) }} · {{ typeOf(h.description).key === 'other' ? h.description : (nameOf(h.description) || typeOf(h.description).label) }}</span>
            </div>
            <button class="icon-btn" title="Remove" @click="askRemove(h)"><Trash2 :size="17" /></button>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom: move four months at a time -->
    <div class="card hol-nav">
      <button class="btn" @click="shift(-1)"><ChevronLeft :size="16" /> Previous months</button>
      <div class="hol-nav-label">
        <strong>{{ MONTH_NAMES[startMonth] }} – {{ MONTH_NAMES[startMonth + 3] }} {{ year }}</strong>
        <span class="muted small">{{ windowCount }} holiday(s) in these months · {{ list.length }} in {{ year }}</span>
      </div>
      <div class="actions">
        <button class="btn" @click="goToday"><CalendarDays :size="16" /> Today</button>
        <button class="btn" @click="shift(1)">Next months <ChevronRight :size="16" /></button>
      </div>
    </div>

    <!-- Add a holiday -->
    <Modal v-if="adding" title="Mark as holiday" @close="adding = null">
      <div class="hol-date">
        <CalendarDays :size="22" />
        <div><strong>{{ longDate(adding.day) }}</strong><span>The library is closed on this day</span></div>
      </div>
      <label>Type of holiday</label>
      <div class="hol-types" role="radiogroup">
        <button v-for="t in TYPES" :key="t.key" type="button" role="radio" :aria-checked="adding.type === t.key"
                class="hol-type" :class="[t.cls, { on: adding.type === t.key }]" @click="adding.type = t.key">
          <span class="dot"></span>
          <span><strong>{{ t.label }}</strong><small>{{ t.hint }}</small></span>
        </button>
      </div>
      <div class="field mt">
        <label>{{ adding.type === 'other' ? 'Holiday name' : 'Name (optional)' }}</label>
        <input ref="nameInput" v-model="adding.name" :placeholder="currentType.example" @keyup.enter="saveHoliday" />
      </div>
      <template #footer>
        <button class="btn" @click="adding = null">Cancel</button>
        <button class="btn primary" :disabled="busy" @click="saveHoliday"><Check :size="16" /> Mark holiday</button>
      </template>
    </Modal>

    <!-- Remove a holiday -->
    <Modal v-if="removing" title="Remove holiday?" @close="removing = null">
      <div class="hol-date">
        <CalendarX :size="22" />
        <div><strong>{{ longDate(removing.day) }}</strong><span>{{ removing.description }}</span></div>
      </div>
      <p class="muted" style="margin: 12px 0 0">This day will be counted as an open day again for due dates and late fines.</p>
      <template #footer>
        <button class="btn" @click="removing = null">Keep it</button>
        <button class="btn danger" :disabled="busy" @click="confirmRemove"><Trash2 :size="16" /> Remove holiday</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { CalendarDays, CalendarX, Check, ChevronLeft, ChevronRight, Trash2 } from 'lucide-vue-next'
import Modal from '../components/Modal.vue'
import { api } from '../api'
import { toast } from '../store'
import { fmtDate, isoDate } from '../utils'

// Python weekday numbers: 0 = Monday ... 6 = Sunday
const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const year = ref(new Date().getFullYear())
const list = ref([])
const bulk = reactive({ weekday: 6, description: 'Library closed' })
const todayIso = isoDate()
const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
const selMonth = ref(new Date().getMonth())
// The four months on screen: Jan-Apr, May-Aug or Sep-Dec.
const startMonth = ref(Math.floor(new Date().getMonth() / 4) * 4)
const monthOf = (iso) => Number(iso.slice(5, 7)) - 1
const adding = ref(null) // { day, type, name }
const removing = ref(null) // holiday row
const busy = ref(false)
const nameInput = ref(null)

// Holiday types. The type is saved as the start of the description, e.g. "Poya day - Vesak".
const TYPES = [
  { key: 'poya', label: 'Poya day', hint: 'Full moon day', example: 'e.g. Vesak, Poson', cls: 't-poya' },
  { key: 'mercantile', label: 'Mercantile holiday', hint: 'Public / bank holiday', example: 'e.g. Sinhala & Tamil New Year', cls: 't-merc' },
  { key: 'other', label: 'Other', hint: 'Any other closed day', example: 'e.g. Library closed for stock check', cls: 't-other' },
]
const currentType = computed(() => TYPES.find((t) => t.key === adding.value?.type) || TYPES[0])

function typeOf(description = '') {
  const d = description.toLowerCase()
  if (d.includes('poya')) return TYPES[0]
  if (d.includes('mercantile')) return TYPES[1]
  return TYPES[2]
}

// The name after the type, e.g. "Poya day - Vesak" -> "Vesak"
function nameOf(description = '') {
  const t = typeOf(description)
  if (t.key === 'other' || !description.toLowerCase().startsWith(t.label.toLowerCase())) return description
  return description.slice(t.label.length).replace(/^\s*-\s*/, '')
}

const longDate = (iso) => new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

const map = computed(() => Object.fromEntries(list.value.map((h) => [h.day, h])))
const visibleMonths = computed(() => months.value.slice(startMonth.value, startMonth.value + 4))
const monthHolidays = computed(() => list.value.filter((h) => monthOf(h.day) === selMonth.value))
const windowCount = computed(() => visibleMonths.value.reduce((n, m) => n + m.count, 0))
const months = computed(() =>
  Array.from({ length: 12 }, (_, m) => {
    const first = new Date(year.value, m, 1)
    const count = new Date(year.value, m + 1, 0).getDate()
    return {
      index: m,
      name: first.toLocaleDateString('en-GB', { month: 'long' }),
      blank: first.getDay(),
      days: Array.from({ length: count }, (_, i) => ({ n: i + 1, iso: isoDate(new Date(year.value, m, i + 1)) })),
      count: list.value.filter((h) => monthOf(h.day) === m).length,
    }
  }))

async function load() {
  list.value = await api.get('/holidays', { year: year.value })
}

async function changeYear(d) {
  year.value += d
  await load()
}

// Previous / next four months; going past December or January changes the year.
async function shift(dir) {
  let start = startMonth.value + dir * 4
  if (start < 0) {
    start = 8
    await changeYear(-1)
  } else if (start > 8) {
    start = 0
    await changeYear(1)
  }
  startMonth.value = start
  selMonth.value = start
}

async function goToday() {
  const now = new Date()
  if (year.value !== now.getFullYear()) {
    year.value = now.getFullYear()
    await load()
  }
  selMonth.value = now.getMonth()
  startMonth.value = Math.floor(now.getMonth() / 4) * 4
  await nextTick()
  focusToday()
}

function focusToday() {
  document.querySelector(`.day[data-iso="${todayIso}"]`)?.focus({ preventScroll: true })
}

async function toggle(iso) {
  const h = map.value[iso]
  if (h) {
    askRemove(h)
    return
  }
  adding.value = { day: iso, type: 'poya', name: '' }
  await nextTick()
  nameInput.value?.focus()
}

async function saveHoliday() {
  const { day, type, name } = adding.value
  const n = name.trim()
  const description = type === 'other' ? n || 'Holiday' : n ? `${currentType.value.label} - ${n}` : currentType.value.label
  busy.value = true
  try {
    await api.post('/holidays', { day, description })
    toast('Holiday added')
    adding.value = null
    load()
  } finally {
    busy.value = false
  }
}

function askRemove(h) {
  removing.value = h
}

async function confirmRemove() {
  busy.value = true
  try {
    await api.del(`/holidays/${removing.value.id}`)
    toast('Holiday removed')
    removing.value = null
    load()
  } finally {
    busy.value = false
  }
}

async function addBulk() {
  const r = await api.post('/holidays/bulk-weekday', { year: year.value, ...bulk })
  toast(`${r.added} day(s) marked`)
  load()
}

onMounted(async () => {
  await load()
  await nextTick()
  focusToday()
})
</script>
