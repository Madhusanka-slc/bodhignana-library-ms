<template>
  <div v-if="d" class="profile3">
    <!-- 1. Always on screen: who this is, the few numbers that matter, and what you can do -->
    <div class="card ph-head">
      <MemberPhoto :src="m.photo_url" :name="m.name" size="lg" />
      <div class="ph-who">
        <h1 :title="m.name">{{ m.name }}</h1>
        <div class="ph-line">
          <span class="ph-no"><small>Membership No.</small><strong>{{ m.membership_no }}</strong></span>
        </div>
        <div class="ph-actions">
          <router-link :to="`/members/${m.id}/edit`" class="btn sm"><Pencil :size="15" /> Edit details</router-link>
          <button class="btn sm" @click="showRenew = true"><RefreshCw :size="15" /> Renew membership</button>
          <button class="btn sm" :class="{ danger: m.is_active }" @click="askActive">
            <UserX v-if="m.is_active" :size="15" /><UserCheck v-else :size="15" /> {{ m.is_active ? 'Make not active' : 'Make active' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 2. Parts of the profile, as steps like Issue book: click one to see it -->
    <div class="steps ph-tabs" role="tablist">
      <button v-for="t in tabs" :key="t.key" role="tab" type="button" class="step" :class="{ on: tab === t.key }"
              :aria-selected="tab === t.key" @click="tab = t.key">
        <b><component :is="t.icon" v-if="t.icon" :size="14" /><template v-else>{{ t.count }}</template></b> {{ t.label }}
      </button>
    </div>

    <!-- 3. The chosen part -->
    <div class="card ph-panel">
      <div class="record-scroll">

        <!-- Details -->
        <template v-if="tab === 'details'">
          <div class="date-line">
            <div v-for="t in dates" :key="t.label" class="date-cell">
              <component :is="t.icon" :size="17" />
              <span><small>{{ t.label }}</small><strong>{{ t.value || '-' }}</strong></span>
            </div>
          </div>
          <!-- Every other detail as a tile, in the same style as the "All reports" grid.
               One group at a time; the bar at the bottom moves between them. -->
          <section v-if="col" class="info-sec">
            <h3>{{ col.title }} <span class="sec-count">{{ secIdx + 1 }} of {{ detailCols.length }}</span></h3>
            <div class="info-grid">
              <div v-for="r in col.rows" :key="r.label" class="num-tile info-tile" :class="[{ wide: r.wide }, r.tone && 'st-' + r.tone]" :title="r.value || ''">
                <span class="num-badge" :class="r.tone ? '' : col.color"><component :is="r.icon" :size="17" /></span>
                <span class="num-text">
                  <small>{{ r.label }}</small>
                  <span v-if="r.phones && phones.length > 1" class="phone-step">
                    <strong>{{ phones[phoneIdx] }}</strong>
                    <small>{{ phoneIdx + 1 }} / {{ phones.length }}</small>
                    <button class="phone-next" :title="phoneDir > 0 ? 'Next number' : 'Previous number'" @click="stepPhone">
                      <ChevronRight v-if="phoneDir > 0" :size="16" /><ChevronLeft v-else :size="16" />
                    </button>
                  </span>
                  <strong v-else :class="{ none: !r.value }">{{ r.value || '-' }}</strong>
                </span>
              </div>
            </div>
          </section>
        </template>

        <!-- Books now -->
        <template v-else-if="tab === 'now'">
          <div v-if="!d.current_loans.length" class="empty">No books with this member now.</div>
          <table v-else class="table report-table">
            <colgroup><col style="width: 104px" /><col /><col style="width: 116px" /><col style="width: 130px" /><col style="width: 100px" /></colgroup>
            <thead><tr><th>Acc. No.</th><th>Title</th><th>Borrowed</th><th>Due date</th><th></th></tr></thead>
            <tbody>
              <tr v-for="l in d.current_loans" :key="l.id" class="click" @click="$router.push('/books/' + l.book.id)">
                <td><span class="code-tag">{{ l.book.acc_no }}</span></td>
                <td :title="l.book.title">{{ l.book.title }}</td>
                <td>{{ fmtDate(l.issue_date) }}</td>
                <td><span :class="l.is_overdue ? 'badge red' : ''">{{ fmtDate(l.due_date) }}</span></td>
                <td class="num" @click.stop><button v-if="!l.is_overdue" class="btn sm" title="Give 14 more days" @click="renewLoan(l)">Extend</button></td>
              </tr>
            </tbody>
          </table>
        </template>

        <!-- History -->
        <template v-else-if="tab === 'history'">
          <div v-if="!d.history.length" class="empty">No returned books yet.</div>
          <table v-else class="table report-table">
            <colgroup><col style="width: 104px" /><col /><col style="width: 116px" /><col style="width: 116px" /><col style="width: 110px" /></colgroup>
            <thead><tr><th>Acc. No.</th><th>Title</th><th>Borrowed</th><th>Returned</th><th class="num">Fine</th></tr></thead>
            <tbody>
              <tr v-for="l in d.history" :key="l.id" class="click" @click="$router.push('/books/' + l.book.id)">
                <td><span class="code-tag">{{ l.book.acc_no }}</span></td>
                <td :title="l.book.title">{{ l.book.title }} <span v-if="l.is_damaged" class="badge red">Damaged</span><span v-else-if="l.late_days" class="badge orange">{{ l.late_days }} day(s) late</span></td>
                <td>{{ fmtDate(l.issue_date) }}</td>
                <td>{{ fmtDate(l.return_date) }}</td>
                <td class="num">{{ l.total_fine ? money(l.total_fine) : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </template>

        <!-- Member card -->
        <template v-else>
          <div class="card-tab">
            <img :src="qrUrl(m.membership_no, 8)" alt="Member QR code" class="zoomable" title="Click to show the code big" @click="showCode = true" />
            <div class="card-tab-info">
              <h2>Member card</h2>
              <p class="muted">Scanned at the counter. Click to enlarge.</p>
              <div class="actions">
                <button class="btn primary" @click="openPrint('/print/member-card/' + m.id)"><Printer :size="16" /> Print card</button>
                <button class="btn" @click="showCode = true"><Maximize2 :size="16" /> Show code big</button>
              </div>
              <div class="done-box" :class="{ done: m.card_done }">
                <span><component :is="m.card_done ? CircleCheck : CircleDashed" :size="17" />
                  <span><strong>{{ m.card_done ? 'Card given to the member' : 'Card not given yet' }}</strong>
                    <small v-if="m.card_done">{{ fmtDate(m.card_done_at) }}<template v-if="m.card_done_by"> · {{ m.card_done_by }}</template></small>
                    <small v-else>Print the card, hand it over, then mark it given</small></span></span>
                <button class="btn sm" :class="{ primary: !m.card_done }" @click="setCard(!m.card_done)">{{ m.card_done ? 'Undo' : 'Mark given' }}</button>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Stays at the bottom of the panel: move between the groups of details -->
      <div v-if="tab === 'details'" class="sec-nav">
        <button class="btn sm" :disabled="secIdx === 0" @click="secIdx--"><ChevronLeft :size="16" /> Previous</button>
        <div class="sec-steps">
          <button v-for="(x, i) in detailCols" :key="x.title" type="button" :class="{ on: i === secIdx }" @click="secIdx = i">{{ x.title }}</button>
        </div>
        <button class="btn sm" :disabled="secIdx === detailCols.length - 1" @click="secIdx++">Next <ChevronRight :size="16" /></button>
      </div>
    </div>

    <!-- The code on its own, big enough to scan from the screen -->
    <Modal v-if="showCode" :title="m.membership_no" @close="showCode = false">
      <div class="code-zoom"><img :src="qrUrl(m.membership_no, 12)" alt="Member QR code" /></div>
    </Modal>

    <!-- Renew membership -->
    <Modal v-if="showRenew" title="Renew membership" @close="showRenew = false">
      <p class="muted">Current expiry date: <strong>{{ m.membership_type === 'LIFETIME' ? 'Life time' : fmtDate(m.expiry_date) }}</strong></p>
      <div class="form-grid">
        <div class="field wide">
          <label>New expiry date</label>
          <div class="renew-new">{{ m.membership_type === 'LIFETIME' ? 'Life time (no expiry)' : fmtDate(renewUntil) }}</div>
          <small class="muted">{{ m.membership_type === 'LIFETIME' ? 'Only the renewal date is recorded.' : `${renewYears} year${renewYears === 1 ? '' : 's'} from today` }}</small>
        </div>
      </div>
      <p class="muted small" style="margin: 12px 0 0">Fee: take it in <router-link to="/pay">Payment</router-link>.</p>
      <template #footer>
        <button class="btn" @click="showRenew = false">Cancel</button>
        <button class="btn primary" @click="doRenew"><RefreshCw :size="16" /> Renew</button>
      </template>
    </Modal>

    <!-- Confirm (instead of the browser's plain pop-up) -->
    <Modal v-if="ask" :title="ask.title" @close="ask = null">
      <p style="margin: 0">{{ ask.text }}</p>
      <template #footer>
        <button class="btn" @click="ask = null">Cancel</button>
        <button class="btn" :class="ask.danger ? 'danger' : 'primary'" :disabled="busy" @click="ask.run()">{{ ask.ok }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  Cake, ChevronLeft, ChevronRight, CalendarClock, CalendarPlus, CircleAlert, CircleCheck, CircleDashed, CircleMinus, History, IdCard, ListChecks, Mail, MapPin, Maximize2, NotebookPen, Pencil, Phone, Printer, QrCode, RefreshCw, School, UserCheck, UserPen, UserX, Users,
} from 'lucide-vue-next'
import Modal from '../components/Modal.vue'
import MemberPhoto from '../components/MemberPhoto.vue'
import { api, qrUrl } from '../api'
import { appSettings, toast } from '../store'
import { typeLabel } from '../constants'
import { fmtDate, money, openPrint } from '../utils'

const route = useRoute()
const d = ref(null)
const m = computed(() => d.value.member)
const tab = ref('now')
const showCode = ref(false)
const showRenew = ref(false)
const ask = ref(null) // { title, text, ok, danger, run }
const busy = ref(false)
const renew = reactive({ fee: 0 })
// The new expiry date is counted from the day of renewal, for the period of the member's type
const renewYears = computed(() => Number(appSettings[`membership_years_${(m.value.membership_type || '').toLowerCase()}`] ?? appSettings.membership_years ?? 3) || 3)
const renewUntil = computed(() => {
  const d = new Date(new Date().toDateString())
  const day = d.getDate()
  d.setFullYear(d.getFullYear() + renewYears.value)
  if (d.getDate() !== day) d.setDate(0)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
})

// A member can have more than one number ("034-2226471, 072-1564487"): the Telephone tile shows one at a
// time. The arrow goes forward to the last number, then turns round and goes back.
const phones = computed(() => (m.value.telephone || '').split(/[,;~/]+/).map((x) => x.trim()).filter(Boolean))
const phoneIdx = ref(0)
const phoneDir = ref(1)
function stepPhone() {
  phoneIdx.value += phoneDir.value
  if (phoneIdx.value >= phones.value.length - 1) phoneDir.value = -1
  if (phoneIdx.value <= 0) phoneDir.value = 1
}
const overdueCount = computed(() => d.value.current_loans.filter((l) => l.is_overdue).length)
const maxBooks = computed(() => Number(appSettings[`max_books_${(m.value.membership_type || '').toLowerCase()}`] ?? appSettings.max_books_default ?? 2))
const validText = computed(() => (m.value.membership_type === 'LIFETIME' ? 'Life time' : m.value.expiry_date ? fmtDate(m.value.expiry_date) : 'Not set'))
// Dates share one line (they are all the same short length) ...
const dates = computed(() => {
  const x = m.value
  return [
    { icon: Cake, label: x.birthday && x.age !== null ? `Birthday · ${x.age} years` : 'Birthday', value: x.birthday ? fmtDate(x.birthday) : '' },
    { icon: CalendarPlus, label: 'Registered', value: x.registered_date ? fmtDate(x.registered_date) : '' },
    { icon: CalendarClock, label: 'Expiry date', value: x.membership_type === 'LIFETIME' ? 'Life time' : x.expiry_date ? fmtDate(x.expiry_date) : '' },
    { icon: RefreshCw, label: 'Renewed', value: x.renewal_date ? fmtDate(x.renewal_date) : '' },
  ]
})
// ... every other detail gets a line of its own.
const detailCols = computed(() => {
  const x = m.value
  const second = [
    { icon: IdCard, label: 'Membership type', value: typeLabel(x.membership_type) },
    // Status: the whole tile takes the colour (green active, red expired, grey not active)
    !x.is_active ? { icon: CircleMinus, label: 'Member status', value: 'Not active', tone: 'gray' }
      : x.is_expired ? { icon: CircleAlert, label: 'Member status', value: 'Membership expired', tone: 'red' }
        : { icon: CircleCheck, label: 'Member status', value: 'Active', tone: 'green' },
    { icon: UserPen, label: 'Registered by', value: x.created_by },
    { icon: Users, label: 'Guarantor', value: x.guarantor_name },
    { icon: MapPin, label: 'Guarantor address', value: x.guarantor_address, wide: true },
  ]
  if (x.notes) second.push({ icon: NotebookPen, label: 'Notes', value: x.notes, wide: true })
  return [
    { title: 'Personal', color: 'g-members', rows: [
      { icon: IdCard, label: 'NIC No.', value: x.nic_no },
      { icon: Phone, label: 'Telephone', value: x.telephone, phones: true },
      { icon: Mail, label: 'Email', value: x.email },
      { icon: School, label: 'School', value: x.school },
      { icon: MapPin, label: 'Address', value: x.address, wide: true },
    ] },
    { title: 'Membership & guarantor', color: 'g-books', rows: second },
  ]
})
const secIdx = ref(0)
const col = computed(() => detailCols.value[secIdx.value])
// The parts of the profile. Parts with records show how many; the others show an icon.
const tabs = computed(() => [
  { key: 'details', label: 'Details', icon: ListChecks },
  { key: 'now', label: 'Books now', count: d.value.current_loans.length },
  { key: 'history', label: 'History', count: d.value.history.length },
  { key: 'card', label: 'Member card', icon: QrCode },
])

async function load(first = false) {
  d.value = await api.get(`/members/${route.params.id}`)
  // Open the part that matters most: books out, otherwise the details. (Fines and payments are in Payments.)
  if (first) tab.value = d.value.current_loans.length ? 'now' : 'details'
}

async function run(fn, done) {
  busy.value = true
  try {
    await fn()
    ask.value = null
    if (done) toast(done)
    await load()
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    busy.value = false
  }
}

async function setCard(done) {
  try {
    d.value.member = await api.post(`/members/${m.value.id}/card`, { done })
    toast(done ? 'Marked: card given' : 'Marked: card not given')
  } catch (e) {
    toast(e.message, 'error')
  }
}

function askActive() {
  const active = m.value.is_active
  ask.value = {
    title: active ? 'Make not active?' : 'Make active again?',
    text: active ? `${m.value.name} will not be able to borrow books until made active again.` : `${m.value.name} will be able to borrow books again.`,
    ok: active ? 'Make not active' : 'Make active',
    danger: active,
    run: () => run(() => api.put(`/members/${m.value.id}`, { ...m.value, is_active: !active }), 'Saved'),
  }
}

async function doRenew() {
  try {
    const r = await api.post(`/members/${m.value.id}/renew`, renew)
    showRenew.value = false
    toast(r.member.membership_type === 'LIFETIME' ? 'Membership renewed' : `Membership renewed until ${fmtDate(r.member.expiry_date)}`)
    if (r.payment) openPrint('/print/receipt/' + r.payment.id)
    load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

async function renewLoan(l) {
  try {
    const r = await api.post(`/circulation/renew/${l.id}`)
    toast(`New due date: ${fmtDate(r.due_date)}`)
    load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

onMounted(() => load(true))
</script>
