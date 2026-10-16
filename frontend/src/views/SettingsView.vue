<template>
  <div class="settings-page">
    <div class="page-head">
      <div>
        <h1>Settings</h1>
        <p class="sub">{{ admin ? 'Change a part, then press Save settings.' : 'Only an administrator can change these settings.' }}</p>
      </div>
    </div>

    <!-- The parts of the settings, as tabs -->
    <div class="report-tabs set-tabs" role="tablist">
      <button v-for="t in tabs" :key="t.key" role="tab" class="report-tab" :class="{ on: tab === t.key }" :aria-selected="tab === t.key" @click="tab = t.key">
        <component :is="t.icon" :size="18" /> {{ t.title }}
      </button>
    </div>

    <div class="card set-card">
      <fieldset v-if="tab !== 'staff'" :disabled="!admin" class="set-fields">
        <!-- 1. Library -->
        <template v-if="tab === 'library'">
          <h2>Library</h2>
          <p class="muted small set-help">The menu name shows at the top left. The name on receipts and reports is printed on paper (receipts, cards, labels, reports).</p>
          <!-- the fields on the left, how the top of a receipt will look on the right -->
          <div class="set-split">
            <div class="set-grid">
              <div class="field"><label>Name in the menu</label><input v-model="s.library_name" /></div>
              <div class="field"><label>Name on receipts and reports</label><input v-model="s.print_name" :placeholder="s.library_name || 'Same as the menu'" /></div>
              <div class="field"><label>Town (printed under that name)</label><input v-model="s.library_place" placeholder="e.g. Kalutara" /></div>
              <div class="field"><label>Address</label><input v-model="s.library_address" /></div>
              <div class="field"><label>Telephone</label><input v-model="s.library_phone" /></div>
              <div class="field"><label>Receipt footer text</label><input v-model="s.receipt_footer" /></div>
              <div class="field"><label>Membership No. starts with</label><input v-model="s.membership_prefix" placeholder="Empty = plain numbers" />
                <small class="muted">Empty gives 10256. "M" gives M10256.</small></div>
              <div class="field"><label>Sections that cannot be taken home</label><input v-model="s.non_lending_sections" />
                <small class="muted">Separate with commas, e.g. Reference</small></div>
            </div>
            <div class="set-preview">
              <small>Receipt top</small>
              <strong>{{ s.print_name || s.library_name || 'Library name' }}</strong>
              <span v-if="s.library_place">{{ s.library_place }}</span>
              <span v-if="s.library_address">{{ s.library_address }}</span>
              <span v-if="s.library_phone">Tel: {{ s.library_phone }}</span>
              <span class="dash"></span>
              <em>{{ s.receipt_footer }}</em>
            </div>
          </div>
        </template>

        <!-- 2. Loans and fines -->
        <template v-else-if="tab === 'loans'">
          <h2>Loans and fines</h2>
          <p class="muted small set-help">How long a book can be kept, and what is charged when it comes back late, damaged or not at all.</p>
          <div class="set-tiles">
            <div class="set-tile"><CalendarClock :size="20" /><label>Days a member can keep a book<input v-model.number="s.loan_days" type="number" min="1" /></label></div>
            <div class="set-tile"><Clock :size="20" /><label>Free days after the due date<input v-model.number="s.grace_days" type="number" min="0" /></label></div>
            <div class="set-tile"><Banknote :size="20" /><label>Late fine per day (Rs.)<input v-model.number="s.fine_per_day" type="number" min="0" /></label></div>
            <div class="set-tile"><CircleHelp :size="20" /><label>Once past the free days, charge them too?
              <select v-model="s.charge_grace_days"><option value="no">No, only later days</option><option value="yes">Yes, every late day</option></select></label></div>
            <div class="set-tile"><BookX :size="20" /><label>Damaged book = book price ×<input v-model.number="s.damage_multiplier" type="number" min="0" step="0.5" /></label></div>
            <div class="set-tile"><CircleAlert :size="20" /><label>Missing book = book price ×<input v-model.number="s.lost_multiplier" type="number" min="0" step="0.5" /></label></div>
          </div>
          <div class="set-example">
            <Info :size="18" />
            <span>With these rules: a book returned <b>{{ exampleDays }} working days late</b> pays <b>Rs. {{ exampleFine }}</b>.
              A book worth Rs. 500 pays <b>Rs. {{ (500 * Number(s.damage_multiplier || 0)).toFixed(2) }}</b> if damaged and
              <b>Rs. {{ (500 * Number(s.lost_multiplier || 0)).toFixed(2) }}</b> if missing.</span>
          </div>
        </template>

        <!-- 3. Member types: one row per type, one column per rule -->
        <template v-else-if="tab === 'types'">
          <h2>Member types</h2>
          <p class="muted small set-help">The rules for each kind of member. Each value can be changed in its box.</p>
          <table class="table report-table set-matrix">
            <colgroup><col style="width: 22%" /><col /><col /><col /><col /></colgroup>
            <thead><tr><th>Member type</th><th>Books at a time</th><th>Fee per book issued (Rs.)</th><th>Membership fee (Rs.)</th><th>Membership lasts (years)</th></tr></thead>
            <tbody>
              <tr v-for="t in TYPES" :key="t.key">
                <td><span class="group-tag">{{ t.label }}</span></td>
                <td><input v-model.number="s[t.books]" type="number" min="0" :aria-label="t.label + ' books at a time'" /></td>
                <td><input v-model.number="s[t.fee]" type="number" min="0" :aria-label="t.label + ' fee per book'" /></td>
                <td><input v-if="t.member" v-model.number="s[t.member]" type="number" min="0" :aria-label="t.label + ' membership fee'" /><span v-else class="muted">-</span></td>
                <td><input v-if="t.years" v-model.number="s[t.years]" type="number" min="1" :aria-label="t.label + ' membership years'" /><span v-else class="muted">Never expires</span></td>
              </tr>
            </tbody>
          </table>
          <div class="set-example">
            <Info :size="18" />
            <span>Example: an Adult borrowing 2 books pays an issue fee of <b>Rs. {{ (2 * Number(s.issue_fee_adult || 0)).toFixed(2) }}</b>,
              and a new Adult membership lasts <b>{{ s.membership_years_adult || 0 }} year(s)</b>. 0 means no fee.</span>
          </div>
        </template>
      </fieldset>

      <!-- 4. Staff accounts -->
      <template v-if="tab === 'staff'">
        <div class="card-head">
          <div>
            <h2 style="margin: 0">Staff accounts</h2>
            <p class="muted small set-help">Who can sign in. Administrators can also change settings.</p>
          </div>
          <button class="btn primary" @click="openUser()"><UserPlus :size="16" /> Add staff</button>
        </div>
        <div class="set-staff">
          <div v-for="u in users" :key="u.id" class="num-tile set-user" :class="{ off: !u.is_active }">
            <span class="num-badge" :class="u.role === 'admin' ? 'g-members' : 'g-books'"><ShieldCheck v-if="u.role === 'admin'" :size="17" /><UserRound v-else :size="17" /></span>
            <span class="num-text"><strong>{{ u.full_name || u.username }}</strong><small>Signs in as {{ u.username }}</small></span>
            <span class="set-user-role">{{ u.role === 'admin' ? 'Administrator · can change settings' : 'Staff' }}</span>
            <span :class="u.is_active ? 'badge green' : 'badge gray'">{{ u.is_active ? 'Active' : 'Disabled' }}</span>
            <button class="btn sm" @click="openUser(u)"><Pencil :size="14" /> Edit</button>
          </div>
        </div>
      </template>

      <!-- Save, at the bottom of the settings parts -->
      <div v-if="admin && tab !== 'staff'" class="set-foot">
        <span class="muted small">{{ changed ? 'You have changes that are not saved yet.' : 'All changes are saved.' }}</span>
        <button class="btn" :disabled="!changed" @click="undo">Undo changes</button>
        <button class="btn primary" :disabled="!changed" @click="saveSettings"><Save :size="16" /> Save settings</button>
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
import {
  Banknote, BookX, Building2, CalendarClock, CircleAlert, CircleHelp, Clock, IdCard, Info, Pencil, Save, ShieldCheck, UserPlus, UserRound, Users,
} from 'lucide-vue-next'
import Modal from '../components/Modal.vue'
import { api } from '../api'
import { appSettings, isAdmin, loadSettings, toast } from '../store'

const admin = isAdmin()
const s = reactive({})
const saved = ref({}) // the settings as last saved, to see what changed
const users = ref([])
const editUser = ref(null)
const tab = ref('library')
const tabs = [
  { key: 'library', title: 'Library', icon: Building2 },
  { key: 'loans', title: 'Loans and fines', icon: CalendarClock },
  { key: 'types', title: 'Member types', icon: IdCard },
  ...(admin ? [{ key: 'staff', title: 'Staff accounts', icon: Users }] : []),
]
// One row per member type in the "Member types" tab, with the setting behind each box
const TYPES = [
  { key: 'child', label: 'Child', books: 'max_books_child', fee: 'issue_fee_child', member: 'membership_fee_child', years: 'membership_years_child' },
  { key: 'student', label: 'Student', books: 'max_books_student', fee: 'issue_fee_student', member: 'membership_fee_student', years: 'membership_years_student' },
  { key: 'adult', label: 'Adult', books: 'max_books_adult', fee: 'issue_fee_adult', member: 'membership_fee_adult', years: 'membership_years_adult' },
  { key: 'lifetime', label: 'Life Time', books: 'max_books_lifetime', fee: 'issue_fee_lifetime', member: 'membership_fee_lifetime', years: '' },
  { key: 'other', label: 'Other types', books: 'max_books_default', fee: 'issue_fee_default', member: '', years: 'membership_years' },
]

const changed = computed(() => Object.keys(s).some((k) => String(s[k] ?? '') !== String(saved.value[k] ?? '')))
const exampleDays = computed(() => Number(s.grace_days || 0) + 3)
const exampleFine = computed(() => {
  const late = exampleDays.value
  const grace = Number(s.grace_days || 0)
  const days = late <= grace ? 0 : s.charge_grace_days === 'yes' ? late : late - grace
  return (days * Number(s.fine_per_day || 0)).toFixed(2)
})

async function load() {
  const st = await api.get('/settings')
  Object.assign(s, st)
  saved.value = { ...st }
  if (admin) users.value = await api.get('/users')
}

function undo() {
  Object.assign(s, saved.value)
}

async function saveSettings() {
  try {
    const st = await api.put('/settings', s)
    Object.assign(appSettings, st)
    saved.value = { ...s }
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
