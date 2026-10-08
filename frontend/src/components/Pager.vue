<template>
  <div class="pager">
    <span class="pager-info">
      <template v-if="total">Showing <b>{{ n(from) }}–{{ n(to) }}</b> of <b>{{ n(total) }}</b></template>
      <template v-else>No records</template>
    </span>
    <div v-if="pages > 1" class="pager-buttons">
      <button class="btn sm" :disabled="page <= 1" title="First page" @click="go(1)"><ChevronsLeft :size="16" /></button>
      <button class="btn sm" :disabled="page <= 1" @click="go(page - 1)"><ChevronLeft :size="16" /> Previous</button>
      <span class="pager-page">Page {{ n(page) }} of {{ n(pages) }}</span>
      <button class="btn sm" :disabled="page >= pages" @click="go(page + 1)">Next <ChevronRight :size="16" /></button>
      <button class="btn sm" :disabled="page >= pages" title="Last page" @click="go(pages)"><ChevronsRight :size="16" /></button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-vue-next'

const props = defineProps({ page: Number, size: Number, total: Number })
const emit = defineEmits(['update:page'])
const pages = computed(() => Math.max(1, Math.ceil((props.total || 0) / (props.size || 25))))
const from = computed(() => (props.page - 1) * props.size + 1)
const to = computed(() => Math.min(props.page * props.size, props.total || 0))
const n = (v) => Number(v || 0).toLocaleString('en-US')
const go = (p) => emit('update:page', p)
</script>
