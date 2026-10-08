<template>
  <div ref="box" class="date-input" :class="{ open }">
    <input :id="id" v-model="text" type="text" inputmode="numeric" autocomplete="off" :placeholder="placeholder"
           @focus="text = display" @blur="commitText" @keydown.enter.prevent="commitText(); $emit('enter')"
           @keydown.esc="open = false" @keydown.down.prevent="show" />
    <button type="button" class="date-btn" :aria-label="open ? 'Close calendar' : 'Open calendar'" tabindex="-1" @click="toggle">
      <CalendarDays :size="17" />
    </button>
  </div>

  <!-- The calendar is placed on the page body so no scroll area or dialog can cut it off -->
  <Teleport to="body">
    <div v-if="open" ref="pop" class="dp-pop" :style="pos" role="dialog" aria-label="Choose a date" @mousedown.prevent>
      <div class="dp-head">
        <button type="button" class="dp-nav" aria-label="Previous month" @click="step(-1)"><ChevronLeft :size="18" /></button>
        <select v-model.number="viewMonth" aria-label="Month">
          <option v-for="(m, i) in MONTHS" :key="m" :value="i">{{ m }}</option>
        </select>
        <select v-model.number="viewYear" aria-label="Year">
          <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
        </select>
        <button type="button" class="dp-nav" aria-label="Next month" @click="step(1)"><ChevronRight :size="18" /></button>
      </div>
      <div class="dp-grid">
        <span v-for="d in DAYS" :key="d" class="dp-dn">{{ d }}</span>
        <span v-for="n in blanks" :key="'b' + n"></span>
        <button v-for="d in daysInMonth" :key="d" type="button" class="dp-day"
                :class="{ sel: iso(d) === modelValue, today: iso(d) === todayIso }" @click="pick(iso(d))">{{ d }}</button>
      </div>
      <div class="dp-foot">
        <button type="button" class="btn sm" @click="pick(todayIso)">Today</button>
        <button type="button" class="btn sm" @click="pick('')">Clear</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { isoDate } from '../utils'

const props = defineProps({
  modelValue: { type: String, default: '' },
  id: String,
  placeholder: { type: String, default: 'dd/mm/yyyy' },
})
const emit = defineEmits(['update:modelValue', 'change', 'enter'])

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
const DAYS = ['S', 'M', 'T', 'W', 'T', 'F', 'S']
const todayIso = isoDate()
const thisYear = new Date().getFullYear()
const years = Array.from({ length: thisYear + 6 - 1920 }, (_, i) => thisYear + 5 - i)

const box = ref(null)
const pop = ref(null)
const open = ref(false)
const pos = ref({})
const viewYear = ref(thisYear)
const viewMonth = ref(new Date().getMonth())

// Shown as dd/mm/yyyy, stored as yyyy-mm-dd.
const display = computed(() => {
  const v = props.modelValue
  return v && /^\d{4}-\d{2}-\d{2}$/.test(v) ? `${v.slice(8, 10)}/${v.slice(5, 7)}/${v.slice(0, 4)}` : ''
})
const text = ref(display.value)
watch(display, (v) => { text.value = v })

const blanks = computed(() => new Date(viewYear.value, viewMonth.value, 1).getDay())
const daysInMonth = computed(() => new Date(viewYear.value, viewMonth.value + 1, 0).getDate())
const iso = (d) => isoDate(new Date(viewYear.value, viewMonth.value, d))

function setValue(v) {
  if (v !== (props.modelValue || '')) {
    emit('update:modelValue', v)
    emit('change', v)
  }
  text.value = v ? `${v.slice(8, 10)}/${v.slice(5, 7)}/${v.slice(0, 4)}` : ''
}

// Accepts 25/12/2026, 25-12-2026, 25.12.2026, 25122026 or 2026-12-25.
function parse(t) {
  const s = t.trim()
  if (!s) return ''
  let d, m, y
  let r = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/)
  if (r) [, y, m, d] = r
  else if ((r = s.match(/^(\d{1,2})[/.\-\s](\d{1,2})[/.\-\s](\d{2}|\d{4})$/))) [, d, m, y] = r
  else if ((r = s.match(/^(\d{2})(\d{2})(\d{4})$/))) [, d, m, y] = r
  else return null
  y = Number(y.length === 2 ? (Number(y) > (thisYear % 100) + 5 ? '19' + y : '20' + y) : y)
  const dt = new Date(y, Number(m) - 1, Number(d))
  if (dt.getFullYear() !== y || dt.getMonth() !== Number(m) - 1 || dt.getDate() !== Number(d)) return null
  return isoDate(dt)
}

function commitText() {
  const v = parse(text.value)
  if (v === null) text.value = display.value // not a real date: put the old value back
  else setValue(v)
}

function pick(v) {
  setValue(v)
  open.value = false
}

function step(n) {
  const d = new Date(viewYear.value, viewMonth.value + n, 1)
  viewYear.value = d.getFullYear()
  viewMonth.value = d.getMonth()
}

function place() {
  const r = box.value.getBoundingClientRect()
  const h = 340
  const below = window.innerHeight - r.bottom > h + 8
  pos.value = {
    left: Math.max(8, Math.min(r.left, window.innerWidth - 300)) + 'px',
    top: (below ? r.bottom + 6 : Math.max(8, r.top - h - 6)) + 'px',
  }
}

async function show() {
  const v = props.modelValue
  const d = v && /^\d{4}-\d{2}-\d{2}$/.test(v) ? new Date(v + 'T00:00:00') : new Date()
  viewYear.value = d.getFullYear()
  viewMonth.value = d.getMonth()
  place()
  open.value = true
  await nextTick()
}

function toggle() {
  if (open.value) open.value = false
  else show()
}

// Close when clicking elsewhere, pressing Escape, or when the page scrolls under it.
function onDown(e) {
  if (!box.value?.contains(e.target) && !pop.value?.contains(e.target)) open.value = false
}
function onKey(e) {
  if (e.key === 'Escape') open.value = false
}
function onScroll(e) {
  if (!pop.value?.contains(e.target)) open.value = false
}
watch(open, (o) => {
  const fn = o ? 'addEventListener' : 'removeEventListener'
  document[fn]('mousedown', onDown)
  document[fn]('keydown', onKey)
  window[fn]('scroll', onScroll, true)
  window[fn]('resize', onScroll)
})
onBeforeUnmount(() => { open.value = false })
</script>
