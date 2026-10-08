<template>
  <!-- A member's photo; members without one show their initials on a theme-coloured background -->
  <div class="member-photo" :class="size">
    <img v-if="src && !failed" :src="src" :alt="`Photo of ${name || 'member'}`" loading="lazy" @error="failed = true" />
    <div v-else class="photo-blank" :title="name">{{ initials }}</div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  src: String, // picture URL (or a data URL while choosing a new one)
  name: String,
  size: { type: String, default: 'sm' }, // sm (lists, search) | lg (member page, form)
})
const failed = ref(false)
watch(() => props.src, () => { failed.value = false })

// "Perera, Nimal (Mr.)" -> "PN"
const initials = computed(() => {
  const clean = (props.name || '').replace(/^SAMPLE\s*-\s*/i, '').replace(/\(.*?\)/g, '')
  const letters = clean.split(/[\s,.]+/).map((w) => (w.match(/\p{L}/u) || [''])[0]).filter(Boolean)
  return (letters.slice(0, 2).join('') || '?').toUpperCase()
})
</script>
