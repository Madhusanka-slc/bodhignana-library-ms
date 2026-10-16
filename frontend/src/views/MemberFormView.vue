<template>
  <div>
    <div class="page-head">
      <div>
        <h1>{{ isEdit ? 'Edit member' : 'New member' }}</h1>
        <p class="sub">{{ isEdit ? 'Change a step, then save.' : 'Only the name is required.' }}</p>
      </div>
    </div>

    <!-- Steps, like Issue book; click a step to go to it -->
    <div class="steps">
      <button v-for="(st, i) in STEPS" :key="st" type="button" class="step" :class="{ on: step === i && !saved, done: saved || i < step }"
              :disabled="!!saved || (!isEdit && i > step && !canLeave(step))" @click="goTo(i)">
        <b>{{ i + 1 }}</b> {{ st }}
      </button>
    </div>

    <!-- Done -->
    <div v-if="saved" class="card done-panel">
      <div class="ok"><Check :size="32" /></div>
      <h2>Member registered</h2>
      <p class="muted">{{ saved.name }} can borrow books now.</p>
      <div class="new-no">Membership No. <span class="code-tag">{{ saved.membership_no }}</span></div>
      <div class="actions" style="justify-content: center">
        <button class="btn primary" @click="openPrint('/print/member-card/' + saved.id)"><Printer :size="16" /> Print member card</button>
        <router-link :to="'/members/' + saved.id" class="btn"><User :size="16" /> Open member</router-link>
        <button class="btn" @click="startAgain"><UserPlus :size="16" /> Register another</button>
      </div>
    </div>

    <template v-else>
      <div class="card wizard-card">
        <!-- 1. Member details -->
        <div v-if="step === 0" class="book-form-top inside">
          <div>
            <h2>Member details</h2>
            <p class="muted step-help">Who is joining? Only the name is required.</p>
            <FormGrid :fields="mainFields" :model="m" />
          </div>
          <PictureUpload v-model="photo" kind="photo" :saved="savedPhoto" :label="m.name" @error="(e) => (error = e)" />
        </div>

        <!-- 2. Membership -->
        <template v-else-if="step === 1">
          <h2>Membership</h2>
          <p class="muted step-help">Choose the kind of membership. The membership number and the expiry date are worked out by the system.</p>
          <label>Membership type <span class="req">*</span></label>
          <div class="choice-grid" role="radiogroup">
            <button v-for="t in TYPE_CHOICES" :key="t.value" type="button" role="radio" :aria-checked="m.membership_type === t.value"
                    class="hol-type" :class="{ on: m.membership_type === t.value }" @click="m.membership_type = t.value">
              <span class="dot"></span>
              <span><strong>{{ t.label }}</strong><small>{{ t.hint }}</small></span>
            </button>
          </div>
          <!-- Worked out by the system: the number (given when saving) and the expiry date -->
          <div class="auto-tiles">
            <div v-if="!isEdit" class="auto-tile">
              <Hash :size="20" />
              <span>
                <small>Membership No.</small>
                <strong>{{ nextNo || '…' }}</strong>
                <small>Next number. It is given when you save.</small>
              </span>
            </div>
            <div class="auto-tile">
              <CalendarClock :size="20" />
              <span>
                <small>Expiry date</small>
                <strong>{{ m.membership_type === 'LIFETIME' ? 'Never' : m.expiry_date ? fmtDate(m.expiry_date) : 'Not set' }}</strong>
                <small>{{ expiryHelp }}</small>
              </span>
            </div>
          </div>
          <FormGrid class="mt" :fields="memberFields" :model="m" />
        </template>

        <!-- 3. Guarantor -->
        <template v-else-if="step === 2">
          <h2>Guarantor</h2>
          <p class="muted step-help">
            {{ m.membership_type === 'CHILD' ? 'A parent or guardian who is responsible for books this child borrows.' : 'Someone who vouches for the member. You can leave this empty.' }}
          </p>
          <p v-if="m.membership_type === 'CHILD' && !m.guarantor_name" class="alert blue">Children usually need a guarantor.</p>
          <FormGrid :fields="guarantorFields" :model="m" />
        </template>

        <!-- 4. Check & save -->
        <template v-else>
          <h2>Check &amp; save</h2>
          <p class="muted step-help">Look over the details. Press Edit to change a part.</p>
          <div class="review review-book">
            <div class="review-part review-cover">
              <MemberPhoto :src="photoShown" :name="m.name" size="lg" />
              <span class="muted small mt">{{ photoShown ? 'Photo' : 'No photo' }}</span>
              <button class="btn sm mt" @click="goTo(0)"><Pencil :size="14" /> Edit</button>
            </div>
            <div v-for="(part, i) in review" :key="part.title" class="review-part">
              <div class="review-head"><h3>{{ part.title }}</h3><button class="btn sm" @click="goTo(i)"><Pencil :size="14" /> Edit</button></div>
              <dl class="info">
                <template v-for="row in part.rows" :key="row[0]">
                  <dt>{{ row[0] }}</dt><dd>{{ row[1] || '-' }}</dd>
                </template>
              </dl>
            </div>
          </div>
        </template>
      </div>

      <p v-if="error" class="alert red">{{ error }}</p>

      <div class="card wizard-nav">
        <button v-if="step > 0" class="btn" @click="goTo(step - 1)"><ChevronLeft :size="16" /> Back</button>
        <button v-else class="btn" @click="$router.back()">Cancel</button>
        <span class="muted small">Step {{ step + 1 }} of {{ STEPS.length }}</span>
        <div class="actions">
          <button v-if="isEdit && step < STEPS.length - 1" class="btn" :disabled="busy || !m.name.trim()" @click="save"><Save :size="16" /> Save now</button>
          <button v-if="step < STEPS.length - 1" class="btn primary" :disabled="!canLeave(step)" @click="goTo(step + 1)">Next <ChevronRight :size="16" /></button>
          <button v-else class="btn primary" :disabled="busy" @click="save"><Save :size="16" /> {{ isEdit ? 'Save changes' : 'Save member' }}</button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CalendarClock, Check, ChevronLeft, ChevronRight, Hash, Pencil, Printer, Save, User, UserPlus } from 'lucide-vue-next'
import FormGrid from '../components/FormGrid.vue'
import MemberPhoto from '../components/MemberPhoto.vue'
import PictureUpload from '../components/PictureUpload.vue'
import { api } from '../api'
import { appSettings, toast } from '../store'
import { MEMBERSHIP_TYPES, typeLabel } from '../constants'
import { fmtDate, isoDate, openPrint } from '../utils'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const busy = ref(false)
const error = ref('')
const step = ref(0)
const saved = ref(null) // the new member, once registered

const STEPS = ['Member details', 'Membership', 'Guarantor', 'Check & save']
const HINTS = { CHILD: 'Under 18', STUDENT: 'School or university', ADULT: '18 and over', LIFETIME: 'Never expires' }
const TYPE_CHOICES = MEMBERSHIP_TYPES.map((t) => ({ ...t, hint: HINTS[t.value] || '' }))

const blank = () => ({
  membership_no: '', name: '', address: '', nic_no: '', birthday: '', membership_type: 'ADULT',
  email: '', telephone: '', registered_date: isoDate(), expiry_date: '', renewal_date: '',
  guarantor_name: '', guarantor_address: '', school: '', notes: '', is_active: true,
})
const m = reactive(blank())

// Optional photo
const savedPhoto = ref(null)
const photo = ref({ image: null, removed: false })
const photoShown = computed(() => photo.value.image || (photo.value.removed ? null : savedPhoto.value))
async function savePhoto(id) {
  if (photo.value.image) await api.post(`/members/${id}/photo`, { image: photo.value.image })
  else if (photo.value.removed && savedPhoto.value) await api.del(`/members/${id}/photo`)
}

const mainFields = [
  { key: 'name', label: 'Member name', required: true, wide: true, placeholder: 'e.g. Perera, A. B. (Mr.)' },
  { key: 'nic_no', label: 'NIC No.' },
  { key: 'birthday', label: 'Birthday', type: 'date' },
  { key: 'telephone', label: 'Telephone No.', type: 'tel' },
  { key: 'email', label: 'Email', type: 'email' },
  { key: 'school', label: 'School' },
  { key: 'address', label: 'Address', type: 'textarea', wide: true },
]
// A new member has no number to type and no renewal yet; both can be corrected later on Edit.
const memberFields = computed(() => [
  ...(isEdit.value ? [{ key: 'membership_no', label: 'Membership No.' }] : []),
  { key: 'registered_date', label: 'Registered on', type: 'date' },
  ...(isEdit.value ? [
    { key: 'renewal_date', label: 'Last renewed on', type: 'date', help: 'The day the member renewed. The expiry date is counted from it.' },
    { key: 'expiry_date', label: 'Expiry date', type: 'date', help: 'Worked out when you change the type or a date above. You can correct it.' },
  ] : []),
  { key: 'notes', label: 'Notes', type: 'textarea', wide: true },
])

// Expiry date = last renewal (or, if never renewed, the registration date) + the period for the type.
const nextNo = ref('')
const years = computed(() => Number(appSettings[`membership_years_${(m.membership_type || '').toLowerCase()}`] ?? appSettings.membership_years ?? 3) || 3)
function workOutExpiry() {
  const start = m.renewal_date || m.registered_date
  if (m.membership_type === 'LIFETIME' || !start) return ''
  const d = new Date(start + 'T00:00:00')
  const day = d.getDate()
  d.setFullYear(d.getFullYear() + years.value)
  if (d.getDate() !== day) d.setDate(0) // 29 Feb -> 28 Feb
  return isoDate(d)
}
const expiryHelp = computed(() => {
  if (m.membership_type === 'LIFETIME') return 'Life Time membership does not expire.'
  if (!m.expiry_date) return (m.renewal_date || m.registered_date) ? 'Not set for this member. Change the type or a date below to work it out.' : 'No registration date, so no expiry date.'
  return `${years.value} year${years.value === 1 ? '' : 's'} for ${typeLabel(m.membership_type)}, from the ${m.renewal_date ? 'last renewal' : 'registration'} date`
})
const guarantorFields = [
  { key: 'guarantor_name', label: 'Guarantor name', wide: true },
  { key: 'guarantor_address', label: 'Guarantor address', type: 'textarea', wide: true },
]

// What is shown on the "Check & save" step, one part per earlier step.
const review = computed(() => [
  { title: 'Member details', rows: [['Name', m.name], ['NIC No.', m.nic_no], ['Birthday', m.birthday && fmtDate(m.birthday)],
    ['Telephone', m.telephone], ['Email', m.email], ['School', m.school], ['Address', m.address]] },
  { title: 'Membership', rows: [['Type', typeLabel(m.membership_type)], ['Membership No.', m.membership_no || (nextNo.value ? `${nextNo.value} (next number, given when you save)` : 'Given when you save')],
    ['Registered on', m.registered_date && fmtDate(m.registered_date)],
    ['Expiry date', m.membership_type === 'LIFETIME' ? 'Never' : (m.expiry_date ? fmtDate(m.expiry_date) : 'Not set')],
    ['Notes', m.notes]] },
  { title: 'Guarantor', rows: [['Name', m.guarantor_name], ['Address', m.guarantor_address]] },
])

// A step can be left once its required fields are filled.
function canLeave(i) {
  if (i === 0) return !!m.name.trim()
  if (i === 1) return !!m.membership_type
  return true
}

function goTo(i) {
  if (i < 0 || i >= STEPS.length) return
  if (!isEdit.value && i > step.value) {
    for (let k = step.value; k < i; k++) if (!canLeave(k)) return
  }
  error.value = ''
  step.value = i
}

function startAgain() {
  Object.assign(m, blank())
  loadNextNo()
  photo.value = { image: null, removed: false }
  savedPhoto.value = null
  saved.value = null
  step.value = 0
}

async function loadNextNo() {
  try {
    nextNo.value = (await api.get('/members/next-no')).membership_no
  } catch {
    nextNo.value = ''
  }
}

onMounted(async () => {
  if (isEdit.value) {
    const r = await api.get(`/members/${route.params.id}`)
    Object.keys(m).forEach((k) => { m[k] = r.member[k] ?? '' })
    savedPhoto.value = r.member.photo_url
    await nextTick()
  } else {
    m.expiry_date = workOutExpiry()
    loadNextNo()
  }
  ready = true
})

// Changing the type or one of the dates works the expiry date out again.
// (Just opening an old member for another edit leaves their expiry date as it is.)
let ready = false
watch(() => [m.membership_type, m.registered_date, m.renewal_date], () => { if (ready) m.expiry_date = workOutExpiry() })

async function save() {
  error.value = ''
  if (!m.name.trim()) {
    step.value = 0
    error.value = 'Please enter the member name.'
    return
  }
  busy.value = true
  try {
    if (isEdit.value) {
      await api.put(`/members/${route.params.id}`, m)
      await savePhoto(route.params.id)
      toast('Member saved')
      router.push('/members/' + route.params.id)
    } else {
      const created = await api.post('/members', m)
      await savePhoto(created.id)
      saved.value = created
      toast(`Member registered: ${saved.value.membership_no}`)
    }
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>
