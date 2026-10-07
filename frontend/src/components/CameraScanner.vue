<template>
  <Modal title="Scan with camera" @close="close">
    <p class="muted">Hold the QR code or barcode in front of the camera.</p>
    <div id="camera-reader" class="camera-box"></div>
    <p v-if="error" class="alert red">{{ error }}</p>
  </Modal>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Html5Qrcode } from 'html5-qrcode'
import Modal from './Modal.vue'

const emit = defineEmits(['scanned', 'close'])
const error = ref('')
let scanner = null
let done = false

onMounted(async () => {
  try {
    scanner = new Html5Qrcode('camera-reader')
    await scanner.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 260, height: 180 } },
      async (text) => {
        if (done) return
        done = true
        await stop()
        emit('scanned', text)
      },
      () => {},
    )
  } catch (e) {
    error.value = 'The camera could not start. Check that a camera is connected and allowed in the browser. ' + (e?.message || e)
  }
})

async function stop() {
  try {
    if (scanner && scanner.isScanning) await scanner.stop()
  } catch {
    /* ignore */
  }
}

onBeforeUnmount(stop)

async function close() {
  await stop()
  emit('close')
}
</script>
