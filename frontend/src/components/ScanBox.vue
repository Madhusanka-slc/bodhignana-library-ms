<template>
  <div class="scanbox" :class="{ disabled }">
    <label v-if="label" class="scan-label" :for="id">{{ label }}</label>
    <div class="scan-row">
      <ScanLine :size="26" class="scan-icon" />
      <input :id="id" ref="inp" v-model="code" :placeholder="placeholder" :disabled="disabled"
        autocomplete="off" spellcheck="false" @keydown.enter.prevent="submit" />
      <button class="btn primary" :disabled="disabled" @click="submit">{{ buttonText }}</button>
      <button class="btn" title="Scan with camera" :disabled="disabled" @click="showCam = true">
        <Camera :size="20" />
      </button>
    </div>
    <p v-if="hint" class="hint">{{ hint }}</p>
    <CameraScanner v-if="showCam" @close="showCam = false" @scanned="onCamera" />
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { Camera, ScanLine } from 'lucide-vue-next'
import CameraScanner from './CameraScanner.vue'

const props = defineProps({
  label: String,
  placeholder: { type: String, default: 'Scan or type the code' },
  hint: String,
  buttonText: { type: String, default: 'Find' },
  disabled: Boolean,
  autofocus: { type: Boolean, default: true },
  keep: Boolean, // keep the text after Enter (for search boxes)
})
const emit = defineEmits(['scan'])
const id = 'scan-' + Math.random().toString(36).slice(2, 8)
const code = ref('')
const inp = ref(null)
const showCam = ref(false)

function focus() {
  nextTick(() => inp.value?.focus())
}

function submit() {
  const c = code.value.trim()
  if (!c) return
  emit('scan', c)
  if (!props.keep) code.value = ''
  focus()
}

function onCamera(text) {
  showCam.value = false
  emit('scan', text.trim())
}

defineExpose({ focus })
onMounted(() => props.autofocus && focus())
</script>
