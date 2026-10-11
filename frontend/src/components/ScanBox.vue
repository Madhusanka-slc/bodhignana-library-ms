<template>
  <div class="scanbox" :class="{ disabled }">
    <label v-if="label" class="scan-label" :for="id">{{ label }}</label>
    <div class="scan-wrap">
      <div class="scan-row">
        <ScanLine :size="26" class="scan-icon" />
        <input :id="id" ref="inp" v-model="code" :placeholder="placeholder" :disabled="disabled"
          autocomplete="off" spellcheck="false" :aria-expanded="open"
          @keydown.enter.prevent="onEnter" @keydown.down.prevent="move(1)" @keydown.up.prevent="move(-1)"
          @keydown.esc="open = false" @input="onInput" @blur="open = false" @focus="open = sugg.length > 0" />
        <button v-if="live && code" type="button" class="btn" title="Clear" :disabled="disabled" @click="clear"><X :size="18" /></button>
        <button v-if="!live" class="btn primary" :disabled="disabled" @click="submit">{{ buttonText }}</button>
        <button class="btn" title="Scan with camera" :disabled="disabled" @click="showCam = true">
          <Camera :size="20" />
        </button>
      </div>

      <!-- Matches while typing: click one, or use the arrow keys and Enter -->
      <div v-if="open" class="suggest" role="listbox">
        <button v-for="(s, i) in sugg" :key="s.kind + s.id" type="button" role="option" class="suggest-item"
                :class="{ on: i === hi }" :aria-selected="i === hi" @mousedown.prevent="choose(s)" @mouseenter="hi = i">
          <span class="suggest-box" :class="s.kind">{{ s.letter }}</span>
          <span class="suggest-text">
            <strong>{{ s.title }}</strong>
            <small>{{ s.sub }}</small>
          </span>
          <span v-if="s.tag" class="badge" :class="s.tagCls">{{ s.tag }}</span>
        </button>
      </div>
    </div>
    <p v-if="hint" class="hint">{{ hint }}</p>
    <CameraScanner v-if="showCam" @close="showCam = false" @scanned="onCamera" />
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { Camera, ScanLine, X } from 'lucide-vue-next'
import CameraScanner from './CameraScanner.vue'
import { api } from '../api'
import { BOOK_STATUS, typeLabel } from '../constants'
import { fmtDate } from '../utils'
import { latestOnly, useLiveSearch } from '../liveSearch'

const props = defineProps({
  label: String,
  placeholder: { type: String, default: 'Scan or type the code' },
  hint: String,
  buttonText: { type: String, default: 'Find' },
  disabled: Boolean,
  autofocus: { type: Boolean, default: true },
  keep: Boolean, // keep the text after Enter (for search boxes)
  live: Boolean, // search while typing: sends 'type' on every key, no Search button
  // Show matches while typing and let the user pick one (sent as 'pick'):
  // 'member' (members), 'book' (books), 'return' (books out now, then members who have books)
  suggest: String,
})
const emit = defineEmits(['scan', 'type', 'pick'])
const id = 'scan-' + Math.random().toString(36).slice(2, 8)
const code = ref('')
const inp = ref(null)
const showCam = ref(false)
const sugg = ref([])
const open = ref(false)
const hi = ref(-1) // highlighted match

function focus() {
  nextTick(() => inp.value?.focus())
}

function reset() {
  sugg.value = []
  open.value = false
  hi.value = -1
}

function submit() {
  const c = code.value.trim()
  if (!c) return
  reset()
  emit('scan', c)
  if (!props.keep) code.value = ''
  focus()
}

// Enter picks the highlighted match; otherwise the typed or scanned text is used as before
// (a card / label scanner types the code and presses Enter by itself).
function onEnter() {
  if (open.value && hi.value >= 0 && sugg.value[hi.value]) choose(sugg.value[hi.value])
  else submit()
}

function choose(s) {
  reset()
  emit('pick', s)
  if (!props.keep) code.value = ''
  focus()
}

function move(step) {
  if (!sugg.value.length) return
  open.value = true
  hi.value = (hi.value + step + sugg.value.length) % sugg.value.length
}

function clear() {
  code.value = ''
  reset()
  emit('type', '')
  focus()
}

function initials(text, n = 2) {
  const words = (text || '').replace(/^SAMPLE\s*-\s*/i, '').match(/\p{L}+/gu) || ['?']
  return words.slice(0, n).map((w) => w[0]).join('').toUpperCase()
}
const memberRow = (m) => ({
  kind: 'member', id: m.id, code: m.membership_no, item: m,
  letter: initials(m.name), title: m.name,
  sub: `${m.membership_no} · ${typeLabel(m.membership_type)}${m.borrowed_acc_nos ? ' · has ' + m.borrowed_acc_nos : ''}`,
  tag: !m.is_active ? 'Not active' : m.is_expired ? 'Expired' : '', tagCls: !m.is_active ? 'gray' : 'red',
})
const bookRow = (b) => ({
  kind: 'book', id: b.id, code: b.acc_no, item: b,
  letter: initials(b.title, 1), title: b.title,
  sub: b.status === 'ISSUED'
    ? `${b.acc_no} · with ${b.borrower_name} (${b.borrower_no}), due ${fmtDate(b.due_date)}`
    : `${b.acc_no} · ${b.persons || 'Unknown author'}${b.section ? ' · ' + b.section : ''}`,
  tag: BOOK_STATUS[b.status]?.label || b.status, tagCls: BOOK_STATUS[b.status]?.cls || 'gray',
})

const fetchSugg = latestOnly(async (q) => {
  if (props.suggest === 'member') return (await api.get('/members', { q, size: 8 })).items.map(memberRow)
  if (props.suggest === 'book') return (await api.get('/books', { q, size: 8 })).items.map(bookRow)
  const [books, members] = await Promise.all([
    api.get('/books', { q, status: 'ISSUED', size: 6 }),
    api.get('/members', { q, size: 15 }),
  ])
  return [...books.items.map(bookRow), ...members.items.filter((m) => m.borrowed_acc_nos).slice(0, 4).map(memberRow)]
})
const typing = useLiveSearch(async () => {
  const q = code.value.trim()
  if (q.length < 2) return reset()
  try {
    const rows = await fetchSugg(q)
    if (!rows || code.value.trim() !== q) return // typed on, or already submitted
    sugg.value = rows
    hi.value = -1
    open.value = rows.length > 0 && document.activeElement === inp.value
  } catch {
    reset()
  }
})

function onInput() {
  if (props.live) emit('type', code.value)
  if (props.suggest) typing.soon()
}

function onCamera(text) {
  showCam.value = false
  emit('scan', text.trim())
}

defineExpose({ focus })
onMounted(() => props.autofocus && focus())
</script>
