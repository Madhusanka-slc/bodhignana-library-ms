<template>
  <div v-if="pages > 1" class="pager">
    <button class="btn" :disabled="page <= 1" @click="$emit('update:page', page - 1)">Previous</button>
    <span>Page {{ page }} of {{ pages }} ({{ total }} records)</span>
    <button class="btn" :disabled="page >= pages" @click="$emit('update:page', page + 1)">Next</button>
  </div>
  <div v-else class="pager"><span>{{ total }} record(s)</span></div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ page: Number, size: Number, total: Number })
defineEmits(['update:page'])
const pages = computed(() => Math.max(1, Math.ceil((props.total || 0) / (props.size || 25))))
</script>
