<template>
  <div class="list-page report-page">
    <div class="page-head">
      <div>
        <h1>Reports</h1>
        <p class="sub">Choose a tab, pick a report, set filters and press Show report. Empty filters include everything.</p>
      </div>
    </div>

    <!-- 1. Report groups as tabs -->
    <div class="report-tabs" role="tablist">
      <button v-for="g in GROUPS" :key="g.key" role="tab" class="report-tab" :class="{ on: current.group === g.key }"
              :aria-selected="current.group === g.key" @click="selectGroup(g)">
        <component :is="g.icon" :size="18" /> {{ g.title }}
        <small>{{ REPORTS.filter((r) => r.group === g.key).length }}</small>
      </button>
    </div>

    <div class="card list-card report-card">
      <!-- 2. Reports in the selected tab -->
      <div class="report-chips">
        <button v-for="r in groupReports" :key="r.key" class="report-chip" :class="{ on: current.key === r.key }" @click="select(r)">
          {{ r.title }}
        </button>
      </div>

      <!-- 3. Title, actions and filters -->
      <div class="report-head">
        <div>
          <h2>{{ current.title }}</h2>
          <p class="muted small">{{ current.desc }}</p>
        </div>
        <div class="actions">
          <button v-if="current.params" class="btn" @click="showFilters = !showFilters">
            <SlidersHorizontal :size="16" /> {{ showFilters ? 'Hide filters' : 'Show filters' }}
          </button>
          <button class="btn" :disabled="!rows.length || exporting" @click="exportAll"><Download :size="16" /> {{ exporting ? 'Preparing...' : 'Excel (CSV)' }}</button>
          <button class="btn primary" :disabled="!rows.length" @click="preview = true"><FileText :size="16" /> Preview &amp; print</button>
        </div>
      </div>

      <div v-if="current.params && showFilters" class="report-filters">
        <div class="filters">
          <div v-for="p in current.params" :key="p.key" :class="{ grow: p.wide || (p.type === 'range' && !p.narrow) }">
            <label>{{ p.label }}</label>
            <!-- A from / to pair sits on one line -->
            <div v-if="p.type === 'range'" class="range-pair">
              <template v-for="(q, qi) in [p.from, p.to]" :key="q.key">
                <span v-if="qi === 1" class="range-sep">to</span>
                <select v-if="q.type === 'select'" v-model="params[q.key]" :aria-label="q.label">
                  <option v-for="o in q.options" :key="o.value" :value="o.value">{{ o.label }}</option>
                </select>
                <DateInput v-else-if="q.type === 'date'" v-model="params[q.key]" @enter="run" />
                <input v-else v-model="params[q.key]" :type="q.type" :placeholder="p.narrow ? (qi ? 'Max' : 'Min') : (qi ? 'To' : 'From')" :aria-label="q.label" @keyup.enter="run" />
              </template>
            </div>
            <select v-else-if="p.type === 'select'" v-model="params[p.key]">
              <option v-for="o in p.options" :key="o.value" :value="o.value">{{ o.label }}</option>
            </select>
            <DateInput v-else-if="p.type === 'date'" v-model="params[p.key]" @enter="run" />
            <input v-else v-model="params[p.key]" :type="p.type" :placeholder="p.placeholder || ''" @keyup.enter="run" />
          </div>
          <div class="filter-actions">
            <button class="btn primary" @click="run"><Play :size="16" /> Show report</button>
            <button class="btn" @click="resetFilters">Clear filters</button>
          </div>
        </div>
      </div>

      <!-- 4. Results: only the rows scroll -->
      <div ref="listBox" class="table-wrap list-scroll">
        <table class="table report-table" :style="{ minWidth: tableMin + 'px' }">
          <colgroup><col v-for="c in columns" :key="c.key" :style="{ width: colWidth(c) }" /></colgroup>
          <thead><tr><th v-for="c in columns" :key="c.key" :class="{ num: isNum(c) }" :title="c.label">{{ c.label }}</th></tr></thead>
          <tbody>
            <tr v-for="(r, i) in rows" :key="i" :class="{ click: !!link(r) }" @click="open(r)">
              <td v-for="c in columns" :key="c.key" :class="{ num: isNum(c), label: c.key === 'group' }" :title="cell(r, c)">
                <span v-if="CODES.has(c.key) && getPath(r, c.key)" class="code-tag">{{ getPath(r, c.key) }}</span>
                <template v-else>{{ cell(r, c) }}</template>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!loaded" class="empty">Loading...</div>
        <div v-else-if="!rows.length" class="empty">Nothing matches these filters.</div>
      </div>

      <div class="pager">
        <span class="pager-info">
          <b>{{ n(count) }}</b> {{ current.unit || 'record(s)' }}
          <template v-if="current.total && loaded"> · {{ current.totalLabel || 'Total' }}: <b>{{ current.total === 'money' ? money(totalValue) : n(totalValue) }}</b></template>
        </span>
        <span v-if="loaded && rows.length < count" class="muted small">
          Showing the first {{ n(rows.length) }}. Narrow the filters, or use Excel (CSV) to get all {{ n(count) }}.
        </span>
      </div>
    </div>

    <!-- 5. Print preview, laid out like a PDF page -->
    <Teleport to="body">
      <div v-if="preview" class="pdf-overlay">
        <div class="pdf-toolbar">
          <strong><FileText :size="18" /> {{ current.title }}</strong>
          <div class="actions">
            <div class="seg">
              <button :class="{ on: orientation === 'portrait' }" @click="orientation = 'portrait'">Portrait</button>
              <button :class="{ on: orientation === 'landscape' }" @click="orientation = 'landscape'">Landscape</button>
            </div>
            <button class="btn primary" @click="printPreview"><Printer :size="16" /> Print / Save as PDF</button>
            <button class="btn" @click="preview = false"><X :size="16" /> Close</button>
          </div>
        </div>
        <div class="pdf-stage">
          <div class="paper" :class="orientation">
            <div class="paper-head">
              <div>
                <div class="paper-lib">{{ appSettings.library_name }}</div>
                <div class="paper-addr">{{ [appSettings.library_address, appSettings.library_phone].filter(Boolean).join(' · ') }}</div>
              </div>
              <div class="paper-date">Printed {{ fmtDate(isoDate()) }}</div>
            </div>
            <h1 class="paper-title">{{ current.title }}</h1>
            <p class="paper-meta">{{ groupOf(current).title }} report<template v-if="filterText"> · {{ filterText }}</template></p>
            <p class="paper-meta">
              <b>{{ n(count) }}</b> {{ current.unit || 'record(s)' }}
              <template v-if="current.total"> · {{ current.totalLabel || 'Total' }}: <b>{{ current.total === 'money' ? money(totalValue) : n(totalValue) }}</b></template>
              <template v-if="rows.length < count"> · first {{ n(rows.length) }} shown</template>
            </p>
            <table class="paper-table">
              <thead><tr><th v-for="c in columns" :key="c.key" :class="{ num: isNum(c) }">{{ c.label }}</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in rows" :key="i">
                  <td v-for="c in columns" :key="c.key" :class="{ num: isNum(c), wrap: WRAP.has(c.key) }">{{ cell(r, c) }}</td>
                </tr>
              </tbody>
            </table>
            <div class="paper-foot">{{ appSettings.library_name }} · {{ current.title }} · {{ fmtDate(isoDate()) }}</div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeftRight, BookOpen, Download, FileText, Play, Printer, SlidersHorizontal, Users, Wallet, X } from 'lucide-vue-next'
import DateInput from '../components/DateInput.vue'
import { api } from '../api'
import { appSettings } from '../store'
import { BOOK_STATUS, MEMBERSHIP_TYPES, PAYMENT_TYPES, SECTIONS } from '../constants'
import { exportCsv, fmtDate, formatCell, getPath, isoDate, money } from '../utils'

// ---------- building blocks ----------
const col = (key, label, kind, num) => ({ key, label, kind, num })
const csvOnly = (c) => ({ ...c, csv: true })
// Long text columns may wrap; everything else stays on one line.
// Acc. No. and Membership No. are shown in a small bordered box.
const CODES = new Set(['acc_no', 'book.acc_no', 'membership_no', 'member.membership_no', 'member_no'])
const WRAP = new Set(['title', 'book.title', 'books', 'address', 'member.address', 'persons', 'name', 'member.name', 'school', 'group', 'call_no', 'telephone', 'member.telephone'])
const all = (label) => [{ value: '', label }]
const opt = (list) => list.map((v) => (typeof v === 'string' ? { value: v, label: v } : v))
const now = new Date()
const monthStart = isoDate(new Date(now.getFullYear(), now.getMonth(), 1))
const yearStart = isoDate(new Date(now.getFullYear(), 0, 1))
const today = isoDate()

const YEAR_OPTS = [...all('Any year'), ...Array.from({ length: now.getFullYear() - 1899 }, (_, i) => String(now.getFullYear() - i)).map((y) => ({ value: y, label: y }))]
// Staff names for the "Staff" filter (filled in when the page opens) and the kinds of action.
const STAFF_OPTS = reactive([{ value: '', label: 'All staff' }])
api.get('/reports/staff-list').then((list) => STAFF_OPTS.push(...list.map((u) => ({ value: String(u.id), label: u.name }))))
const ACTION_LABELS = {
  issue: 'Issued a book', return: 'Returned a book', renew_loan: 'Gave more time', payment: 'Took a payment',
  member_add: 'Registered a member', member_edit: 'Edited a member', member_photo: 'Member photo', member_renew: 'Renewed membership',
  book_add: 'Added a book', book_edit: 'Edited a book', book_cover: 'Book cover', book_status: 'Book status',
  holiday: 'Holidays', settings: 'Settings', user: 'Staff account', login: 'Signed in',
}
const ACTION_OPTS = [{ value: '', label: 'All actions' }, ...[
  ['issue', 'Issued books'], ['return', 'Returned books'], ['renew_loan', 'Gave more time'], ['payment', 'Payments'],
  ['member_add', 'New members'], ['member_change', 'Member changes'], ['book_add', 'New books'], ['book_change', 'Book changes'],
  ['holiday', 'Holidays'], ['settings', 'Settings & staff accounts'], ['login', 'Sign-ins'],
].map(([value, label]) => ({ value, label }))]

const SECTION_OPTS = [...all('All sections'), ...opt(SECTIONS)]
const TYPE_OPTS = [...all('All types'), ...MEMBERSHIP_TYPES]
const STATUS_OPTS = [...all('Any status'), ...Object.entries(BOOK_STATUS).map(([value, s]) => ({ value, label: s.label }))]
const SUBJECT_OPTS = [...all('All subjects'), ...[
  ['0', '000 General works & computers'], ['1', '100 Philosophy & psychology'], ['2', '200 Religion'],
  ['3', '300 Social sciences'], ['4', '400 Language'], ['5', '500 Science'], ['6', '600 Technology'],
  ['7', '700 Arts & recreation'], ['8', '800 Literature'], ['9', '900 History & geography'],
].map(([value, label]) => ({ value, label }))]

const P = {
  section: { key: 'section', label: 'Section', type: 'select', default: '', options: SECTION_OPTS },
  membership_type: { key: 'membership_type', label: 'Membership type', type: 'select', default: '', options: TYPE_OPTS },
  from: (d = '') => ({ key: 'from_date', label: 'From date', type: 'date', default: d }),
  to: (d = '') => ({ key: 'to_date', label: 'To date', type: 'date', default: d }),
  top: { key: 'top', label: 'How many', type: 'number', default: 50 },
}

const bookCols = [
  col('acc_no', 'Acc. No.'), col('title', 'Title'), col('persons', 'Author'), csvOnly(col('publisher', 'Publisher')),
  csvOnly(col('year_of_publication', 'Year')), col('section', 'Section'), col('call_no', 'Call No.'),
  csvOnly(col('price', 'Price', 'money')), col('status', 'Status', 'status'), csvOnly(col('date_entered', 'Date entered', 'date')),
  csvOnly(col('isbn', 'ISBN')),
]
const memberCols = [
  col('membership_no', 'Member No.'), col('name', 'Name'), col('membership_type', 'Type', 'type'), col('age', 'Age', null, true),
  col('telephone', 'Telephone'), csvOnly(col('address', 'Address')), col('school', 'School'),
  col('registered_date', 'Registered', 'date'), col('expiry_date', 'Expiry', 'date'), csvOnly(col('nic_no', 'NIC No.')),
]
const loanCols = [
  col('book.acc_no', 'Acc. No.'), col('book.title', 'Title'), col('book.section', 'Section'),
  col('member.membership_no', 'Member No.'), col('member.name', 'Member'), col('member.telephone', 'Telephone'),
  col('issue_date', 'Borrowed', 'date'), col('due_date', 'Due date', 'date'),
]

// ---------- the reports ----------
const GROUPS = [
  { key: 'books', title: 'Books', icon: BookOpen },
  { key: 'members', title: 'Members', icon: Users },
  { key: 'loans', title: 'Books & members', icon: ArrowLeftRight },
  { key: 'other', title: 'Other', icon: Wallet },
]

const REPORTS = [
  // Books
  { group: 'books', key: 'book-list', title: 'Book list', url: '/reports/books', limited: true,
    desc: 'Any list of books: combine section, status, subject, date entered and year published.',
    total: 'money', totalLabel: 'Total value', unit: 'book(s)',
    params: [
      { key: 'q', label: 'Title, author, publisher, keyword', type: 'text', default: '', wide: true },
      P.section,
      { key: 'status', label: 'Status', type: 'select', default: '', options: STATUS_OPTS },
      { key: 'subject', label: 'Subject (class No.)', type: 'select', default: '', options: SUBJECT_OPTS },
      { key: 'sort', label: 'Order by', type: 'select', default: 'acc_no', options: opt([{ value: 'acc_no', label: 'Acc. No.' }, { value: 'title', label: 'Title' }, { value: 'newest', label: 'Newest first' }]) },
      { key: 'entered_from', label: 'Entered from', type: 'date', default: '' },
      { key: 'entered_to', label: 'Entered to', type: 'date', default: '' },
      { key: 'year_from', label: 'Published from (year)', type: 'select', default: '', options: YEAR_OPTS },
      { key: 'year_to', label: 'Published to (year)', type: 'select', default: '', options: YEAR_OPTS },
    ],
    columns: bookCols },
  { group: 'books', key: 'new-books', title: 'New books added', url: '/reports/books', limited: true,
    desc: 'Books entered between two dates (this month by default).',
    total: 'money', totalLabel: 'Total value', unit: 'book(s)',
    params: [
      { key: 'entered_from', label: 'Entered from', type: 'date', default: monthStart },
      { key: 'entered_to', label: 'Entered to', type: 'date', default: today },
      P.section, { key: 'sort', type: 'hidden', default: 'newest' },
    ],
    columns: bookCols },
  { group: 'books', key: 'book-problems', title: 'Damaged, lost & withdrawn', url: '/reports/books', limited: true,
    desc: 'Books that are not usable, by status and section.',
    total: 'money', totalLabel: 'Total value', unit: 'book(s)',
    params: [
      { key: 'status', label: 'Status', type: 'select', default: 'DAMAGED', options: opt([{ value: 'DAMAGED', label: 'Damaged' }, { value: 'LOST', label: 'Lost' }, { value: 'WITHDRAWN', label: 'Withdrawn' }]) },
      P.section,
    ],
    columns: bookCols },
  { group: 'books', key: 'book-summary', title: 'Book counts (summary)', url: '/reports/book-summary',
    desc: 'How many books there are, grouped the way you choose.', total: 'number', totalLabel: 'Total books', unit: 'group(s)',
    params: [
      { key: 'group_by', label: 'Group by', type: 'select', default: 'section', options: opt([
        { value: 'section', label: 'Section' }, { value: 'subject', label: 'Subject (class No.)' }, { value: 'status', label: 'Status' },
        { value: 'year_entered', label: 'Year entered' }, { value: 'year_published', label: 'Year published' }]) },
      P.section,
    ],
    columns: [col('group', 'Group'), col('total', 'Total', null, true), col('available', 'In library', null, true),
      col('issued', 'With members', null, true), col('other', 'Damaged / lost', null, true), col('value', 'Value', 'money')] },
  { group: 'books', key: 'popular', title: 'Most borrowed books', url: '/reports/popular-books',
    desc: 'Books borrowed most often in a period.', unit: 'book(s)',
    params: [P.from(yearStart), P.to(today), P.section, P.top],
    columns: [col('times', 'Times borrowed', null, true), ...bookCols.slice(0, 3), col('section', 'Section'), col('status', 'Status', 'status')] },
  { group: 'books', key: 'never', title: 'Books never borrowed', url: '/reports/never-borrowed', limited: true,
    desc: 'Books nobody has borrowed yet, useful for weeding or promoting.', unit: 'book(s)',
    params: [P.section, { key: 'subject', label: 'Subject (class No.)', type: 'select', default: '', options: SUBJECT_OPTS },
      { key: 'entered_before', label: 'Entered before', type: 'date', default: '' }],
    columns: bookCols },

  // Members
  { group: 'members', key: 'member-list', title: 'Member list', url: '/reports/members', limited: true,
    desc: 'Any list of members: combine type, age, registration date, expiry and school.', unit: 'member(s)',
    params: [
      { key: 'q', label: 'Name, No., NIC, phone, address', type: 'text', default: '', wide: true },
      P.membership_type,
      { key: 'active', label: 'Active', type: 'select', default: 'yes', options: opt([{ value: 'yes', label: 'Active only' }, { value: 'no', label: 'Not active only' }, { value: 'all', label: 'All' }]) },
      { key: 'expiry', label: 'Membership', type: 'select', default: '', options: opt([{ value: '', label: 'Any' }, { value: 'valid', label: 'Valid' },
        { value: 'expiring', label: 'Expiring in 30 days' }, { value: 'expired', label: 'Expired' }, { value: 'none', label: 'No expiry date' }]) },
      { key: 'school', label: 'School', type: 'text', default: '' },
      { key: 'min_age', label: 'Age from', type: 'number', default: '' },
      { key: 'max_age', label: 'Age to', type: 'number', default: '' },
      { key: 'registered_from', label: 'Registered from', type: 'date', default: '' },
      { key: 'registered_to', label: 'Registered to', type: 'date', default: '' },
      { key: 'sort', label: 'Order by', type: 'select', default: 'name', options: opt([{ value: 'name', label: 'Name' }, { value: 'membership_no', label: 'Member No.' },
        { value: 'newest', label: 'Newest first' }, { value: 'age', label: 'Youngest first' }]) },
    ],
    columns: memberCols },
  { group: 'members', key: 'age', title: 'Members by age', url: '/reports/members', limited: true,
    desc: 'Members in an age range, e.g. children aged 10 to 11.', unit: 'member(s)',
    params: [
      { key: 'min_age', label: 'Age from', type: 'number', default: 10 },
      { key: 'max_age', label: 'Age to', type: 'number', default: 11 },
      P.membership_type, { key: 'sort', type: 'hidden', default: 'age' },
    ],
    columns: [...memberCols.slice(0, 3), col('birthday', 'Birthday', 'date'), ...memberCols.slice(3, 7)] },
  { group: 'members', key: 'new-members', title: 'New members', url: '/reports/members', limited: true,
    desc: 'Members registered between two dates (this month by default).', unit: 'member(s)',
    params: [
      { key: 'registered_from', label: 'Registered from', type: 'date', default: monthStart },
      { key: 'registered_to', label: 'Registered to', type: 'date', default: today },
      P.membership_type, { key: 'sort', type: 'hidden', default: 'newest' }, { key: 'active', type: 'hidden', default: 'all' },
    ],
    columns: memberCols },
  { group: 'members', key: 'expiring', title: 'Memberships expiring or expired', url: '/reports/expiring-members',
    desc: 'Members who need to renew.', unit: 'member(s)',
    params: [{ key: 'days', label: 'Expiring within (days)', type: 'number', default: 30 }],
    columns: [...memberCols.slice(0, 3), col('telephone', 'Telephone'), col('expiry_date', 'Expiry date', 'date')] },
  { group: 'members', key: 'inactive', title: 'Non-active members', url: '/reports/inactive-members', limited: true,
    desc: 'Members who have not borrowed for a while, or are marked not active.', unit: 'member(s)',
    params: [
      { key: 'mode', label: 'Show', type: 'select', default: 'no_borrow', options: [{ value: 'no_borrow', label: 'Not borrowing recently' }, { value: 'status', label: 'Marked as not active' }] },
      { key: 'months', label: 'No borrowing for (months)', type: 'number', default: 6 },
    ],
    columns: [...memberCols.slice(0, 3), col('telephone', 'Telephone'), col('school', 'School'), col('last_borrowed', 'Last borrowed', 'date')] },
  { group: 'members', key: 'member-summary', title: 'Member counts (summary)', url: '/reports/member-summary',
    desc: 'How many members there are, grouped the way you choose.', total: 'number', totalLabel: 'Total members', unit: 'group(s)',
    params: [{ key: 'group_by', label: 'Group by', type: 'select', default: 'type', options: opt([
      { value: 'type', label: 'Membership type' }, { value: 'age', label: 'Age group' }, { value: 'year_registered', label: 'Year registered' },
      { value: 'school', label: 'School' }, { value: 'status', label: 'Active / not active' }]) }],
    columns: [col('group', 'Group', 'type'), col('total', 'Total', null, true), col('active', 'Active', null, true), col('expired', 'Expired', null, true)] },

  // Books & members
  { group: 'loans', key: 'loans', title: 'Borrowing records', url: '/reports/loans', limited: true,
    desc: 'Who took which book and when: filter by date, state, section, member or book.',
    total: 'money', totalLabel: 'Fines charged', unit: 'loan(s)',
    params: [
      P.from(monthStart), P.to(today),
      { key: 'state', label: 'State', type: 'select', default: '', options: opt([{ value: '', label: 'All' }, { value: 'out', label: 'Not returned yet' },
        { value: 'overdue', label: 'Overdue' }, { value: 'returned', label: 'Returned' }, { value: 'late', label: 'Returned late' }, { value: 'damaged', label: 'Returned damaged' }]) },
      P.section, P.membership_type,
      { key: 'member_no', label: 'Member No.', type: 'text', default: '' },
      { key: 'acc_no', label: 'Acc. No.', type: 'text', default: '' },
    ],
    columns: [...loanCols, col('return_date', 'Returned', 'date'), col('late_days', 'Days late', null, true), col('total_fine', 'Fine', 'money')] },
  { group: 'loans', key: 'overdue', title: 'Overdue books', url: '/reports/overdue', total: 'money', totalLabel: 'Fines so far', unit: 'book(s)',
    desc: 'Books past their due date, with the fine so far.',
    columns: [...loanCols, col('days_overdue', 'Days late', null, true), col('estimated_fine', 'Fine now', 'money')] },
  { group: 'loans', key: 'pending', title: 'Books out now (pending returns)', url: '/reports/pending-returns', unit: 'book(s)',
    desc: 'Every book that is with a member right now.',
    params: [P.section], columns: loanCols },
  { group: 'loans', key: 'not-returning', title: 'Members not returning books', url: '/reports/members-with-overdue', unit: 'member(s)',
    desc: 'Members to contact about overdue books.',
    columns: [col('member.membership_no', 'Member No.'), col('member.name', 'Name'), col('member.telephone', 'Telephone'),
      col('member.address', 'Address'), col('count', 'Books', null, true), col('books', 'Book details'), col('oldest_due', 'Oldest due date', 'date')] },
  { group: 'loans', key: 'top-borrowers', title: 'Most active members', url: '/reports/top-borrowers', unit: 'member(s)',
    desc: 'Members who borrowed the most in a period.',
    params: [P.from(yearStart), P.to(today), P.membership_type, P.top],
    columns: [col('times', 'Books borrowed', null, true), ...memberCols.slice(0, 3), col('telephone', 'Telephone'), col('school', 'School')] },
  { group: 'other', key: 'circulation', title: 'Issues & returns (summary)', url: '/reports/circulation-summary',
    desc: 'Number of books issued and returned, per day, month, section or member type.', total: 'number', totalLabel: 'Total issued', unit: 'row(s)',
    params: [P.from(yearStart), P.to(today), { key: 'group_by', label: 'Group by', type: 'select', default: 'month', options: opt([
      { value: 'month', label: 'Month' }, { value: 'day', label: 'Day' }, { value: 'section', label: 'Section' }, { value: 'membership_type', label: 'Membership type' }]) }],
    columns: [col('group', 'Group', 'type'), col('issued', 'Issued', null, true), col('returned', 'Returned', null, true),
      col('late', 'Returned late', null, true), col('fines', 'Fines charged', 'money')] },
  { group: 'other', key: 'staff-activity', title: 'Staff activity', url: '/reports/staff-activity', limited: true,
    desc: 'Who did what and when: issues, returns, new members and books, changes, payments and sign-ins.', unit: 'action(s)',
    params: [
      { key: 'user_id', label: 'Staff', type: 'select', default: '', options: STAFF_OPTS },
      { key: 'action', label: 'Action', type: 'select', default: '', options: ACTION_OPTS },
      P.from(today), P.to(today),
      { key: 'q', label: 'Acc. No., Member No. or word', type: 'text', default: '' },
    ],
    columns: [col('at', 'Date & time', 'datetime'), col('user_name', 'Staff'), col('action', 'Action', 'action'),
      col('ref', 'Number'), col('summary', 'What was done')] },
  { group: 'other', key: 'staff-summary', title: 'Work by staff', url: '/reports/staff-summary',
    desc: 'How much each staff member did in a period.', total: 'number', totalLabel: 'Total actions', unit: 'staff',
    params: [P.from(monthStart), P.to(today)],
    columns: [col('group', 'Staff'), col('issue', 'Issued', null, true), col('return', 'Returned', null, true),
      col('member_add', 'New members', null, true), col('book_add', 'New books', null, true), col('changes', 'Other changes', null, true),
      col('payments', 'Payments', null, true), col('amount', 'Money taken', 'money'), col('login', 'Sign-ins', null, true)] },
  { group: 'other', key: 'unpaid', title: 'Unpaid fines', url: '/reports/unpaid-fines', total: 'money', totalLabel: 'To collect', unit: 'fine(s)',
    desc: 'Fines that members still have to pay.',
    columns: [...loanCols.slice(0, 6), col('return_date', 'Returned', 'date'), col('total_fine', 'Fine', 'money'), col('paid_amount', 'Paid', 'money'), col('balance', 'To pay', 'money')] },
  { group: 'other', key: 'payments', title: 'Payments collected', url: '/reports/payments', total: 'money', totalLabel: 'Collected', unit: 'payment(s)',
    desc: 'Money received between two dates.',
    params: [
      { key: 'from_date', label: 'From', type: 'date', default: monthStart },
      { key: 'to_date', label: 'To', type: 'date', default: today },
      { key: 'payment_type', label: 'Type', type: 'select', default: '', options: [...all('All types'), ...Object.entries(PAYMENT_TYPES).map(([value, label]) => ({ value, label }))] },
    ],
    columns: [col('receipt_no', 'Receipt'), col('paid_at', 'Date', 'datetime'), col('member_no', 'Member No.'), col('member_name', 'Member'),
      col('payment_type', 'For', 'ptype'), col('book_title', 'Book'), col('received_by', 'Received by'), col('amount', 'Amount', 'money')] },
]
// From / to filters that are shown together on one line, with one label.
const PAIRS = [
  ['entered_from', 'entered_to', 'Entered'], ['year_from', 'year_to', 'Published (year)'],
  ['min_age', 'max_age', 'Age'],
  ['registered_from', 'registered_to', 'Registered'], ['from_date', 'to_date', 'Date'],
]
const DATE_LABEL = { loans: 'Borrowed', popular: 'Borrowed', 'top-borrowers': 'Borrowed', payments: 'Paid' }

function pairUp(r, list) {
  const out = []
  for (const p of list) {
    const pair = PAIRS.find(([a]) => a === p.key)
    const partner = pair && list.find((x) => x.key === pair[1])
    if (pair && partner) {
      const label = p.key === 'from_date' ? DATE_LABEL[r.key] || 'Date' : pair[2]
      out.push({ type: 'range', key: `${pair[0]}~${pair[1]}`, label, from: p, to: partner, narrow: p.key === 'min_age' })
    } else if (!PAIRS.some(([a, b]) => b === p.key && list.some((x) => x.key === a))) {
      out.push(p)
    }
  }
  return out
}

// Hidden params only carry a fixed value; they are not shown as filters.
REPORTS.forEach((r) => {
  r.hidden = (r.params || []).filter((p) => p.type === 'hidden')
  r.params = pairUp(r, (r.params || []).filter((p) => p.type !== 'hidden'))
  if (!r.params.length) r.params = null
})
// Every single filter, with from / to pairs opened up again.
const flatParams = (r) => (r.params || []).flatMap((p) => (p.type === 'range' ? [p.from, p.to] : [p]))

// ---------- state ----------
const route = useRoute()
const router = useRouter()
const current = ref(REPORTS.find((r) => r.key === route.query.r) || REPORTS[0])
const params = reactive({})
const rows = ref([])
const count = ref(0)
const totalValue = ref(0)
const loaded = ref(false)
const exporting = ref(false)
const showFilters = ref(true)
const preview = ref(false)
const orientation = ref('portrait')
const listBox = ref(null)

const groupReports = computed(() => REPORTS.filter((r) => r.group === current.value.group))

const columns = computed(() => current.value.columns.filter((c) => !c.csv))
const groupOf = (r) => GROUPS.find((g) => g.key === r.group)
const n = (v) => Number(v || 0).toLocaleString('en-US')
const isNum = (c) => c.kind === 'money' || c.num

// Same layout for every report: short columns get a fixed width, text columns share the rest.
const FIXED = {
  age: '64px', year_of_publication: '72px', section: '110px', 'book.section': '110px', call_no: '130px',
  telephone: '124px', 'member.telephone': '124px', receipt_no: '130px', received_by: '130px',
  at: '150px', user_name: '150px', action: '160px', ref: '130px',
  times: '120px', count: '80px', late_days: '90px', days_overdue: '90px', member_no: '110px', school: '150px', other: '150px', last_borrowed: '130px',
}
// Text columns need at least 200px; with many columns the table scrolls sideways instead of squeezing them.
const tableMin = computed(() => columns.value.reduce((sum, c) => {
  const w = colWidth(c)
  return sum + (w && w.endsWith('px') ? parseInt(w, 10) : 200)
}, 0))

function colWidth(c) {
  if (CODES.has(c.key)) return '104px'
  if (FIXED[c.key]) return FIXED[c.key]
  if (c.key === 'persons') return '22%'
  if (c.key === 'group') return null
  return { money: '130px', date: '120px', datetime: '160px', status: '108px', type: '92px', ptype: '170px' }[c.kind]
    || (c.num ? '116px' : null)
}
const cell = (r, c) => {
  const v = getPath(r, c.key)
  if (c.kind === 'action') return ACTION_LABELS[v] || v
  return c.num && typeof v === 'number' ? n(v) : formatCell(v, c.kind)
}

// A short line of the filters in use, printed under the title.
const filterText = computed(() => flatParams(current.value)
  .filter((p) => params[p.key] !== '' && params[p.key] !== null && params[p.key] !== undefined)
  .map((p) => `${p.label}: ${p.options ? (p.options.find((o) => o.value === params[p.key])?.label ?? params[p.key]) : params[p.key]}`)
  .join(', '))

function query(extra = {}) {
  const q = { ...params }
  current.value.hidden.forEach((p) => { q[p.key] = p.default })
  return { ...q, ...extra }
}

function resetFilters() {
  Object.keys(params).forEach((k) => delete params[k])
  flatParams(current.value).forEach((p) => { params[p.key] = p.default })
}

function select(r) {
  current.value = r
  router.replace({ query: { r: r.key } })
  resetFilters()
  run()
}

async function run() {
  loaded.value = false
  const r = await api.get(current.value.url, query())
  rows.value = r.items
  count.value = r.count
  totalValue.value = r.total ?? 0
  loaded.value = true
  if (listBox.value) listBox.value.scrollTop = 0
}

function selectGroup(g) {
  if (current.value.group !== g.key) select(REPORTS.find((r) => r.group === g.key))
}

// Excel export: when only part of a long list is on screen, fetch every row first.
async function exportAll() {
  let data = rows.value
  if (current.value.limited && rows.value.length < count.value) {
    exporting.value = true
    try {
      data = (await api.get(current.value.url, query({ limit: 0 }))).items
    } finally {
      exporting.value = false
    }
  }
  // Action codes (issue, return ...) are written out in words, as on screen
  if (current.value.columns.some((c) => c.kind === 'action')) data = data.map((r) => ({ ...r, action: ACTION_LABELS[r.action] || r.action }))
  exportCsv(`${current.value.key}-${today}`, current.value.columns, data)
}

function link(r) {
  if (r.member?.id) return `/members/${r.member.id}`
  if (r.membership_no && r.id) return `/members/${r.id}`
  if (r.acc_no && r.id) return `/books/${r.id}`
  return null
}

function open(r) {
  const to = link(r)
  if (to) router.push(to)
}

// Print only the preview page; the browser's print window also offers "Save as PDF".
function printPreview() {
  const style = document.createElement('style')
  style.id = 'report-page-size'
  style.textContent = `@page { size: A4 ${orientation.value}; margin: 12mm; }`
  document.head.appendChild(style)
  document.documentElement.classList.add('print-preview')
  const done = () => {
    document.documentElement.classList.remove('print-preview')
    style.remove()
    window.removeEventListener('afterprint', done)
  }
  window.addEventListener('afterprint', done)
  window.print()
}

// Close the preview with the Escape key.
const onKey = (e) => { if (e.key === 'Escape') preview.value = false }
watch(preview, (open) => (open ? window.addEventListener('keydown', onKey) : window.removeEventListener('keydown', onKey)))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

select(current.value)
</script>
