<template>
  <!-- Our own print preview: the receipt / card / labels shown in a popup, with Print and Cancel.
       Nothing is sent to the printer until Print is pressed. -->
  <div v-if="printJob.path" class="modal-backdrop" @mousedown.self="close">
    <div class="modal print-pop" role="dialog" aria-modal="true" :aria-label="printJob.title">
      <div class="modal-head">
        <h3>{{ printJob.title }}</h3>
        <button class="icon-btn" aria-label="Close" @click="close"><X :size="20" /></button>
      </div>
      <div class="print-pop-body">
        <p v-if="!ready" class="muted print-pop-wait">Preparing the preview…</p>
        <iframe ref="frame" :key="printJob.path" :src="src" title="Print preview" :class="{ ready }" @load="onLoad"></iframe>
      </div>
      <div class="modal-foot">
        <button class="btn" @click="close">{{ printed ? 'Close' : 'Cancel' }}</button>
        <button class="btn primary" :disabled="!ready" @click="print"><Printer :size="16" /> {{ printed ? 'Print again' : 'Print' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Printer, X } from 'lucide-vue-next'
import { printJob } from '../store'

const frame = ref(null)
const ready = ref(false)
const printed = ref(false)
// embed=1 tells the print page it is inside this popup: no buttons of its own, no printing by itself
const src = computed(() => printJob.path + (printJob.path.includes('?') ? '&' : '?') + 'embed=1')

watch(() => printJob.path, () => {
  ready.value = false
  printed.value = false
})

function onLoad() {
  // the page inside still has to fetch its data and pictures; give it a moment
  setTimeout(() => { ready.value = true }, 700)
}

function print() {
  const w = frame.value?.contentWindow
  if (!w) return
  w.focus()
  w.print()
  printed.value = true
}

function close() {
  printJob.path = ''
}
</script>
