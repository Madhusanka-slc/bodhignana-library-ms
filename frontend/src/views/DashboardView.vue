<template>
  <div class="home">
    <div class="page-head">
      <div>
        <h1>Good {{ greeting }}, {{ auth.user?.full_name || auth.user?.username }}</h1>
        <p class="sub">{{ todayText }}</p>
      </div>
    </div>

    <!-- 1. The counter work -->
    <div class="home-actions">
      <router-link to="/issue" class="action-card">
        <span class="action-icon"><ArrowUpRight :size="28" /></span>
        <span class="action-text"><strong>Issue book</strong><small>Member takes books out</small></span>
      </router-link>
      <router-link to="/return" class="action-card">
        <span class="action-icon"><ArrowDownLeft :size="28" /></span>
        <span class="action-text"><strong>Return book</strong><small>Member brings books back</small></span>
      </router-link>
      <router-link to="/search" class="action-card">
        <span class="action-icon"><Search :size="28" /></span>
        <span class="action-text"><strong>Search</strong><small>Find a book or member</small></span>
      </router-link>
      <router-link to="/members/new" class="action-card">
        <span class="action-icon"><UserPlus :size="28" /></span>
        <span class="action-text"><strong>New member</strong><small>Register a reader</small></span>
      </router-link>
      <router-link to="/books/new" class="action-card">
        <span class="action-icon"><BookPlus :size="28" /></span>
        <span class="action-text"><strong>New book</strong><small>Add a book to the library</small></span>
      </router-link>
    </div>

    <template v-if="s">
      <!-- 2. Today at the counter -->
      <h2 class="section-title">Today</h2>
      <div class="status-row">
        <div class="status-box neutral"><span class="v">{{ s.issued_today }}</span><span class="l">Books issued</span></div>
        <div class="status-box neutral"><span class="v">{{ s.returned_today }}</span><span class="l">Books returned</span></div>
        <div class="status-box neutral"><span class="v">{{ money(s.collected_today) }}</span><span class="l">Fines &amp; fees collected</span></div>
      </div>

      <!-- 3. Where the books are -->
      <h2 class="section-title">Books &amp; members</h2>
      <div class="status-row">
        <div class="status-box tint-1"><CircleCheck :size="20" /><span class="v">{{ n(s.books_available) }}</span><span class="l">In the library</span></div>
        <div class="status-box tint-2"><Clock :size="20" /><span class="v">{{ n(s.books_issued) }}</span><span class="l">With members</span></div>
        <div class="status-box tint-3">
          <CircleAlert :size="20" />
          <span class="v">{{ n(s.overdue) }}</span><span class="l">Overdue</span>
        </div>
        <div class="status-box tint-4"><Users :size="20" /><span class="v">{{ n(s.members_active) }}</span><span class="l">Active members</span></div>
      </div>
    </template>

    <!-- 4. Overdue list -->
    <div class="card overdue-card">
      <div class="card-head">
        <h2>Overdue books</h2>
        <router-link to="/reports?r=overdue" class="btn sm">See all</router-link>
      </div>
      <div v-if="!overdue.length" class="alert blue">No overdue books. Everything is on time.</div>
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
import {
  ArrowDownLeft, ArrowUpRight, BookPlus, CircleAlert, CircleCheck, Clock, Search, UserPlus, Users,
} from 'lucide-vue-next'
import { api } from '../api'
import { auth } from '../store'
import { fmtDate, money } from '../utils'

const s = ref(null)
const overdue = ref([])
const h = new Date().getHours()
const greeting = h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening'
const todayText = new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
const n = (v) => Number(v || 0).toLocaleString('en-US')

onMounted(async () => {
  const [stats, od] = await Promise.all([api.get('/reports/dashboard'), api.get('/reports/overdue')])
  s.value = stats
  overdue.value = od.items
})
</script>
