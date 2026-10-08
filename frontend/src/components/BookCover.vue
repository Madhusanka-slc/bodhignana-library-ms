<template>
  <!-- A book's front cover; books without a picture get a plain theme-coloured cover with the first letter -->
  <div class="book-cover" :class="size">
    <img v-if="src && !failed" :src="src" :alt="`Cover of ${title || 'book'}`" loading="lazy" @error="failed = true" />
    <div v-else class="cover-blank" :title="title">
      <span class="cover-letter">{{ letter }}</span>
      <BookOpen :size="size === 'lg' ? 26 : 12" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { BookOpen } from 'lucide-vue-next'

const props = defineProps({
  src: String, // picture URL (or a data URL while choosing a new one)
  title: String,
  size: { type: String, default: 'sm' }, // sm (search icon) | md | lg (book page, form)
})
const failed = ref(false)
watch(() => props.src, () => { failed.value = false })
// First real letter of the title (skips "SAMPLE - ", brackets, numbers)
const letter = computed(() => ((props.title || '').replace(/^SAMPLE\s*-\s*/i, '').match(/\p{L}/u) || ['?'])[0].toUpperCase())
</script>
