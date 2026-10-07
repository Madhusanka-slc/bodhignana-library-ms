<template>
  <div class="modal-backdrop" @mousedown.self="$emit('close')">
    <div class="modal" :class="{ wide }" role="dialog" aria-modal="true">
      <div class="modal-head">
        <h3>{{ title }}</h3>
        <button class="icon-btn" aria-label="Close" @click="$emit('close')"><X :size="20" /></button>
      </div>
      <div class="modal-body"><slot /></div>
      <div v-if="$slots.footer" class="modal-foot"><slot name="footer" /></div>
    </div>
  </div>
</template>

<script setup>
import { X } from 'lucide-vue-next'
defineProps({ title: String, wide: Boolean })
defineEmits(['close'])
</script>
