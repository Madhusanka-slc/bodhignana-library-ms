<template>
  <div>
    <div class="page-head"><h1>Settings</h1></div>

    <div class="card">
      <h2>Library and rules</h2>
      <p v-if="!admin" class="alert blue">Only an administrator can change these settings.</p>
      <fieldset :disabled="!admin" style="border: 0; padding: 0; margin: 0">
        <FormGrid :fields="fields" :model="s" />
      </fieldset>
      <div class="alert blue mt">
        Example with these rules: a book returned {{ exampleDays }} working days late pays
        Rs. {{ exampleFine }}. A damaged book worth Rs. 500 pays Rs. {{ (500 * Number(s.damage_multiplier || 0)).toFixed(2) }};
        a missing one pays Rs. {{ (500 * Number(s.lost_multiplier || 0)).toFixed(2) }}.
        An Adult borrowing 2 books pays an issue fee of Rs. {{ (2 * Number(s.issue_fee_adult || 0)).toFixed(2) }}.
      </div>
      <button v-if="admin" class="btn primary mt" @click="saveSettings"><Save :size="16" /> Save settings</button>
    </div>

    <div v-if="admin" class="card">
      <div class="card-head">
        <h2>Staff accounts</h2>
        <button class="btn" @click="openUser()"><UserPlus :size="16" /> Add staff</button>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Username</th><th>Name</th><th>Role</th><th>Status</th><th></th></tr></thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>{{ u.username }}</td>
              <td>{{ u.full_name }}</td>
              <td>{{ u.role === 'admin' ? 'Administrator' : 'Staff' }}</td>
              <td><span :class="u.is_active ? 'badge green' : 'badge gray'">{{ u.is_active ? 'Active' : 'Disabled' }}</span></td>
              <td class="num"><button class="btn sm" @click="openUser(u)">Edit</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Modal v-if="editUser" :title="editUser.id ? 'Edit staff account' : 'Add staff account'" @close="editUser = null">
      <div class="form-grid">
        <div class="field"><label>Username</label><input v-model="editUser.username" :disabled="!!editUser.id" /></div>
        <div class="field"><label>Full name</label><input v-model="editUser.full_name" /></div>
        <div class="field">
          <label>Role</label>
          <select v-model="editUser.role"><option value="staff">Staff</option><option value="admin">Administrator</option></select>
        </div>
        <div class="field">
          <label>{{ editUser.id ? 'New password (leave empty to keep)' : 'Password' }}</label>
          <input v-model="editUser.password" type="password" />
        </div>
        <div v-if="editUser.id" class="field wide">
          <label class="check"><input v-model="editUser.is_active" type="checkbox" /> Account is active</label>
        </div>
      </div>
      <template #footer>
        <button class="btn" @click="editUser = null">Cancel</button>
        <button class="btn primary" @click="saveUser">Save</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Save, UserPlus } from 'lucide-vue-next'
import FormGrid from '../components/FormGrid.vue'
import Modal from '../components/Modal.vue'
import { api } from '../api'
import { appSettings, isAdmin, loadSettings, toast } from '../store'

const admin = isAdmin()
const s = reactive({})
const users = ref([])
const editUser = ref(null)

const fields = [
  { key: 'library_name', label: 'Library name', wide: true },
  { key: 'library_address', label: 'Address (printed on receipts)', wide: true },
  { key: 'library_phone', label: 'Telephone' },
  { key: 'receipt_footer', label: 'Receipt footer text' },
  { key: 'loan_days', label: 'Days a member can keep a book', type: 'number' },
  { key: 'grace_days', label: 'Free days after due date', type: 'number' },
  { key: 'fine_per_day', label: 'Late fine per day (Rs.)', type: 'number' },
  { key: 'charge_grace_days', label: 'After the free days, charge them too?', type: 'select', required: true,
    options: [{ value: 'no', label: 'No, charge only days after the free days' }, { value: 'yes', label: 'Yes, charge all late days' }] },
  { key: 'damage_multiplier', label: 'Damaged book charge = book price ×', type: 'number' },
  { key: 'lost_multiplier', label: 'Missing book charge = book price ×', type: 'number' },
  { key: 'issue_fee_child', label: 'Fee per book issued: Child (Rs.)', type: 'number', help: '0 = no fee' },
  { key: 'issue_fee_student', label: 'Fee per book issued: Student (Rs.)', type: 'number' },
  { key: 'issue_fee_adult', label: 'Fee per book issued: Adult (Rs.)', type: 'number' },
  { key: 'issue_fee_lifetime', label: 'Fee per book issued: Life Time (Rs.)', type: 'number' },
  { key: 'issue_fee_default', label: 'Fee per book issued: other types (Rs.)', type: 'number' },
  { key: 'membership_fee_child', label: 'Membership fee: Child (Rs.)', type: 'number', help: 'Filled in when Membership fee is chosen on the Payment screen' },
  { key: 'membership_fee_student', label: 'Membership fee: Student (Rs.)', type: 'number' },
  { key: 'membership_fee_adult', label: 'Membership fee: Adult (Rs.)', type: 'number' },
  { key: 'membership_fee_lifetime', label: 'Membership fee: Life Time (Rs.)', type: 'number' },
  { key: 'membership_years_child', label: 'Membership period: Child (years)', type: 'number' },
  { key: 'membership_years_student', label: 'Membership period: Student (years)', type: 'number' },
  { key: 'membership_years_adult', label: 'Membership period: Adult (years)', type: 'number' },
  { key: 'membership_years', label: 'Membership period: other types (years)', type: 'number' },
  { key: 'membership_prefix', label: 'Membership No. starts with', help: 'Leave empty for plain numbers (10256). M gives M10256.' },
  { key: 'max_books_child', label: 'Max books: Child', type: 'number' },
  { key: 'max_books_student', label: 'Max books: Student', type: 'number' },
  { key: 'max_books_adult', label: 'Max books: Adult', type: 'number' },
  { key: 'max_books_lifetime', label: 'Max books: Life Time', type: 'number' },
  { key: 'max_books_default', label: 'Max books: other types', type: 'number' },
  { key: 'non_lending_sections', label: 'Sections that cannot be taken home', help: 'Separate with commas, e.g. Reference' },
]

const exampleDays = computed(() => Number(s.grace_days || 0) + 3)
const exampleFine = computed(() => {
  const late = exampleDays.value
  const grace = Number(s.grace_days || 0)
  const days = late <= grace ? 0 : s.charge_grace_days === 'yes' ? late : late - grace
  return (days * Number(s.fine_per_day || 0)).toFixed(2)
})

async function load() {
  Object.assign(s, await api.get('/settings'))
  if (admin) users.value = await api.get('/users')
}

async function saveSettings() {
  try {
    Object.assign(appSettings, await api.put('/settings', s))
    toast('Settings saved')
  } catch (e) {
    toast(e.message, 'error')
  }
}

function openUser(u) {
  editUser.value = u ? { ...u, password: '' } : { username: '', full_name: '', role: 'staff', password: '' }
}

async function saveUser() {
  const u = editUser.value
  try {
    if (u.id) await api.put(`/users/${u.id}`, { full_name: u.full_name, role: u.role, is_active: u.is_active, password: u.password || null })
    else await api.post('/users', u)
    editUser.value = null
    toast('Staff account saved')
    users.value = await api.get('/users')
  } catch (e) {
    toast(e.message, 'error')
  }
}

onMounted(async () => {
  await load()
  loadSettings()
})
</script>
