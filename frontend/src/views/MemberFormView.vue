<template>
  <div>
    <div class="page-head">
      <div>
        <h1>{{ isEdit ? 'Edit member' : 'New member' }}</h1>
        <p class="sub">Fields marked * are required. Everything else can be added later.</p>
      </div>
    </div>

    <div class="card">
      <h2>Member details</h2>
      <FormGrid :fields="mainFields" :model="m" />
    </div>
    <div class="card">
      <h2>Membership</h2>
      <FormGrid :fields="memberFields" :model="m" />
    </div>
    <div class="card">
      <h2>Guarantor</h2>
      <FormGrid :fields="guarantorFields" :model="m" />
    </div>

    <p v-if="error" class="alert red">{{ error }}</p>
    <div class="actions">
      <button class="btn primary big" :disabled="busy" @click="save"><Save :size="18" /> Save member</button>
      <button class="btn big" @click="$router.back()">Cancel</button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Save } from 'lucide-vue-next'
import FormGrid from '../components/FormGrid.vue'
import { api } from '../api'
import { toast } from '../store'
import { MEMBERSHIP_TYPES } from '../constants'
import { isoDate } from '../utils'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const busy = ref(false)
const error = ref('')

const m = reactive({
  membership_no: '', name: '', address: '', nic_no: '', birthday: '', membership_type: 'STUDENT',
  email: '', telephone: '', registered_date: isoDate(), expiry_date: '', renewal_date: '',
  guarantor_name: '', guarantor_address: '', school: '', notes: '', is_active: true,
})

const mainFields = [
  { key: 'name', label: 'Member name', required: true, wide: true },
  { key: 'nic_no', label: 'NIC No.' },
  { key: 'birthday', label: 'Birthday', type: 'date' },
  { key: 'telephone', label: 'Telephone No.', type: 'tel' },
  { key: 'email', label: 'Email', type: 'email' },
  { key: 'school', label: 'School' },
  { key: 'address', label: 'Address', type: 'textarea', wide: true },
]
const memberFields = [
  { key: 'membership_no', label: 'Membership No.', help: 'Leave empty to create a number automatically' },
  { key: 'membership_type', label: 'Membership type', type: 'select', required: true, options: MEMBERSHIP_TYPES },
  { key: 'registered_date', label: 'Date', type: 'date' },
  { key: 'expiry_date', label: 'Expiry date', type: 'date', help: 'Leave empty to set automatically' },
  { key: 'renewal_date', label: 'Membership renewal date', type: 'date' },
  { key: 'notes', label: 'Notes', type: 'textarea', wide: true },
]
const guarantorFields = [
  { key: 'guarantor_name', label: 'Guarantor name' },
  { key: 'guarantor_address', label: 'Guarantor address', type: 'textarea', wide: true },
]

onMounted(async () => {
  if (isEdit.value) {
    const r = await api.get(`/members/${route.params.id}`)
    Object.keys(m).forEach((k) => { m[k] = r.member[k] ?? '' })
  }
})

async function save() {
  error.value = ''
  busy.value = true
  try {
    const saved = isEdit.value
      ? await api.put(`/members/${route.params.id}`, m)
      : await api.post('/members', m)
    toast(isEdit.value ? 'Member saved' : `Member registered: ${saved.membership_no}`)
    router.push('/members/' + saved.id)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>
