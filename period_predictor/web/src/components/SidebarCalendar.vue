<template>
  <aside class="sidebar" tabindex="0">
    <div class="calendar" aria-label="Period calendar">
      <div class="calendar-header">
        <button @click="prevMonth" aria-label="Previous month">&#x2039;</button>
        <span>{{ monthYear }}</span>
        <button @click="nextMonth" aria-label="Next month">&#x203a;</button>
      </div>
      <table class="calendar-grid">
        <thead>
          <tr>
            <th v-for="day in days" :key="day">{{ day }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(week, wi) in weeks" :key="wi">
            <td
              v-for="day in week"
              :key="day.date || wi + '-' + day.text"
              :class="{ today: day.isToday, period: day.isPeriod }"
            >
              {{ day.text }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="controls">
      <button @click="startPeriod" aria-label="Start period" tabindex="1">
        I got my period
      </button>
      <button @click="endPeriod" aria-label="End period" tabindex="2">
        I have finished my period
      </button>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const current = ref(new Date())
const events = ref([])

const monthYear = computed(() =>
  current.value.toLocaleString('default', { month: 'long', year: 'numeric' })
)

function buildWeeks() {
  const start = new Date(current.value.getFullYear(), current.value.getMonth(), 1)
  const end = new Date(current.value.getFullYear(), current.value.getMonth() + 1, 0)
  const weeks = []
  let week = []

  for (let i = 0; i < start.getDay(); i++) {
    week.push({ text: '', date: null, isToday: false, isPeriod: false })
  }

  for (let day = 1; day <= end.getDate(); day++) {
    const date = new Date(current.value.getFullYear(), current.value.getMonth(), day)
    const dateStr = date.toISOString().split('T')[0]
    const isPeriod = events.value.includes(dateStr)
    const isToday =
      dateStr === new Date().toISOString().split('T')[0]
    week.push({ text: day, date: dateStr, isToday, isPeriod })
    if (week.length === 7) {
      weeks.push(week)
      week = []
    }
  }

  if (week.length) {
    while (week.length < 7) week.push({ text: '', date: null, isToday: false, isPeriod: false })
    weeks.push(week)
  }

  return weeks
}

const weeks = ref(buildWeeks())

function prevMonth() {
  current.value = new Date(
    current.value.getFullYear(),
    current.value.getMonth() - 1,
    1
  )
  weeks.value = buildWeeks()
}

function nextMonth() {
  current.value = new Date(
    current.value.getFullYear(),
    current.value.getMonth() + 1,
    1
  )
  weeks.value = buildWeeks()
}

async function startPeriod() {
  const today = new Date().toISOString().split('T')[0]
  try {
    const res = await fetch('api/periods', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date: today })
    })
    if (!res.ok) throw new Error('Request failed')
    events.value.push(today)
    weeks.value = buildWeeks()
    console.log('Logged period for', today)
    alert('Period logged!')
  } catch (err) {
    console.error('Failed to log period', err)
    alert('Failed to log period')
  }
}

async function endPeriod() {
  console.warn('End period action is not implemented')
}

function handleKey(e) {
  const key = e.key.toLowerCase()
  if (key === 's') {
    startPeriod()
  } else if (key === 'e') {
    endPeriod()
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleKey)
  try {
    const res = await fetch('api/periods')
    if (!res.ok) throw new Error('Request failed')
    events.value = await res.json()
    weeks.value = buildWeeks()
    console.log('Loaded periods', events.value)
  } catch (err) {
    console.error('Failed to load periods', err)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKey)
})
</script>

<style scoped>
@import '../styles/sidebar.css';

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.calendar-grid {
  width: 100%;
  border-collapse: collapse;
}

.calendar-grid th,
.calendar-grid td {
  border: 1px solid #ccc;
  text-align: center;
  width: 14%;
  padding: 0.25rem;
}

.calendar-grid td.today {
  border: 2px solid #1976d2;
}

.calendar-grid td.period {
  background: #ffb3ba;
}
</style>

