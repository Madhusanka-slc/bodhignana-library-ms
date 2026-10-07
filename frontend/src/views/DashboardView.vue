<template>
  <div>
    <div class="page-head">
      <div>
        <h1>Good {{ greeting }}, {{ auth.user?.full_name || auth.user?.username }}</h1>
        <p class="sub">{{ todayText }}</p>
      </div>
    </div>

    <div class="tiles">
      <router-link to="/issue" class="tile main"><ArrowUpRight :size="30" />Issue book<small>Member takes books out</small></router-link>
      <router-link to="/return" class="tile main"><ArrowDownLeft :size="30" />Return book<small>Member brings books back</small></router-link>
      <router-link to="/search" class="tile"><Search :size="30" />Search<small>Find a book or member</small></router-link>
      <router-link to="/members/new" class="tile"><UserPlus :size="30" />New member<small>Register a reader</small></router-link>
      <router-link to="/books/new" class="tile"><BookPlus :size="30" />New book<small>Add a book to the library</small></router-link>
    </div>

    <div v-if="s" class="stats">
      <div class="stat"><div class="v">{{ s.books_available }}</div><div class="l">Books in the library</div></div>
      <div class="stat"><div class="v">{{ s.books_issued }}</div><div class="l">Books with members</div></div>
      <div class="stat" :class="{ warn: s.overdue }"><div class="v">{{ s.overdue }}</div><div class="l">Overdue books</div></div>
      <div class="stat"><div class="v">{{ s.members_active }}</div><div class="l">Active members</div></div>
      <div class="stat"><div class="v">{{ s.issued_today }} / {{ s.returned_today }}</div><div class="l">Issued / returned today</div></div>
      <div class="stat"><div class="v">{{ money(s.collected_today) }}</div><div class="l">Collected today</div></div>
    </div>

    <div class="card">
      <div class="card-head">
        <h2>Overdue books</h2>
        <router-link to="/reports?r=overdue" class="btn sm">See all</router-link>
      </div>
      <div v-if="!overdue.length" class="empty">No overdue books. Everything is on time.</div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead><tr><th>Book</th><th>Member</th><th>Telephone</th><th>Due date</th><th class="num">Days late</th></tr></thead>
          <tbody>
            <tr v-for="l in overdue.slice(0, 8)" :key="l.id" class="click" @click="$router.push('/members/' + l.member.id)">
              <td>{{ l.book.acc_no }} · {{ l.book.title }}</td>
              <td>{{ l.member.name }} ({{ l.member.membership_no }})</td>
              <td>{{ l.member.telephone || '-' }}</td>
              <td>{{ fmtDate(l.due_date) }}</td>
              <td class="num"><span class="badge red">{{ l.days_overdue }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ArrowDownLeft, ArrowUpRight, BookPlus, Search, UserPlus } from 'lucide-vue-next'
import { api } from '../api'
import { auth } from '../store'
import { fmtDate, money } from '../utils'

const s = ref(null)
const overdue = ref([])
const h = new Date().getHours()
const greeting = h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening'
const todayText = new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

onMounted(async () => {
  const [stats, od] = await Promise.all([api.get('/reports/dashboard'), api.get('/reports/overdue')])
  s.value = stats
  overdue.value = od.items
})
</script>
