<template>
  <span class="badge" :class="info.cls">{{ info.label }}</span>
</template>

<script setup>
import { computed } from 'vue'
import { BOOK_STATUS } from '../constants'
const props = defineProps({ status: String })
const info = computed(() => BOOK_STATUS[props.status] || { label: props.status, cls: 'gray' })
</script>
