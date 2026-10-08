<template>
  <!-- Optional picture: a book's front cover or a member's photo.
       v-model holds what to do on save: { image: data URL of a new picture, removed: true if taken away } -->
  <div class="card cover-card">
    <h2>{{ heading }} <span class="optional">(optional)</span></h2>
    <div class="cover-drop" :class="{ over: dragOver }" @dragover.prevent="dragOver = true" @dragleave="dragOver = false"
         @drop.prevent="onDrop" @click="input.click()">
      <BookCover v-if="kind === 'cover'" :src="shown" :title="label" size="lg" />
      <MemberPhoto v-else :src="shown" :name="label" size="lg" />
    </div>
    <input ref="input" type="file" accept="image/*" hidden @change="onPick" />
    <div class="cover-actions">
      <button class="btn sm" type="button" @click="input.click()"><ImagePlus :size="15" /> {{ shown ? 'Change picture' : 'Choose picture' }}</button>
      <button v-if="shown" class="btn sm danger" type="button" @click="remove"><Trash2 :size="15" /> Remove</button>
    </div>
    <p class="help center">{{ help }} You can leave this empty and add it later.</p>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ImagePlus, Trash2 } from 'lucide-vue-next'
import BookCover from './BookCover.vue'
import MemberPhoto from './MemberPhoto.vue'
import { shrinkImage } from '../utils'

const props = defineProps({
  kind: { type: String, default: 'cover' }, // cover | photo
  saved: String, // URL of the picture already saved, if any
  label: String, // book title or member name (for the empty picture)
  modelValue: { type: Object, default: () => ({ image: null, removed: false }) },
})
const emit = defineEmits(['update:modelValue', 'error'])

const input = ref(null)
const dragOver = ref(false)
const heading = computed(() => (props.kind === 'cover' ? 'Front cover' : 'Photo'))
const help = computed(() => (props.kind === 'cover'
  ? 'A photo of the front of the book. JPG or PNG; it is made smaller automatically.'
  : 'A clear photo of the member\'s face. JPG or PNG; it is made smaller automatically.'))
const shown = computed(() => props.modelValue.image || (props.modelValue.removed ? null : props.saved))

async function use(file) {
  if (!file) return
  if (!file.type.startsWith('image/')) {
    emit('error', 'Please choose a picture (JPG or PNG).')
    return
  }
  try {
    const max = props.kind === 'cover' ? [600, 900] : [480, 600]
    emit('update:modelValue', { image: await shrinkImage(file, ...max), removed: false })
  } catch (e) {
    emit('error', e.message)
  }
}
const onPick = (e) => { use(e.target.files[0]); e.target.value = '' }
const onDrop = (e) => { dragOver.value = false; use(e.dataTransfer.files[0]) }
const remove = () => emit('update:modelValue', { image: null, removed: true })
</script>
