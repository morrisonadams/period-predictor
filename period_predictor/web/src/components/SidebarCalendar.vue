<template>
  <aside class="sidebar" tabindex="0">
    <div class="user-select" v-if="users.length">
      <label for="userSelect">User:</label>
      <select id="userSelect" v-model="selectedUser">
        <option v-for="u in users" :key="u.id" :value="u.id">{{ u.name }}</option>
      </select>
    </div>
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
              :class="{
                today: day.isToday,
                period: day.isPeriod && !day.isPrediction,
                'period-start': day.isStart && !day.isPrediction,
                prediction: day.isPrediction,
                'prediction-start': day.isPrediction && day.isStart,
                pms: day.isPms,
                clickable: day.date
              }"
              @click="openMenu(day.date, $event)"
              @contextmenu.prevent="openMenu(day.date, $event)"
              :tabindex="day.date ? 0 : -1"
              :role="day.date ? 'button' : null"
            >
              {{ day.text }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="controls">
      <button @click="clearAll" aria-label="Clear all records" tabindex="1">
        Clear all records
      </button>
      <button @click="testDb" aria-label="Test database" tabindex="2">
        Test database
      </button>
      <button @click="predictNext" aria-label="Predict next period" tabindex="3">
        Predict next period
      </button>
    </div>
    <div v-if="prediction" class="prediction-summary">
      Next: {{ prediction.next_start }} ({{ prediction.period_length }} days)
    </div>
    <ul
      v-if="menu.visible"
      class="context-menu"
      :style="{ top: menu.y + 'px', left: menu.x + 'px' }"
    >
      <li @click="addStart(menu.date)">Add start period</li>
      <li @click="removeStart(menu.date)">Remove start period</li>
      <li @click="addEnd(menu.date)">Add period end</li>
      <li @click="removeEnd(menu.date)">Remove period end</li>
    </ul>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'

const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const current = ref(new Date())
const users = ref([])
const selectedUser = ref('')
const periods = ref([]) // {start_date, end_date}
const events = ref({}) // date -> type
const prediction = ref(null)
const menu = ref({ visible: false, x: 0, y: 0, date: null })

const monthYear = computed(() =>
  current.value.toLocaleString('default', { month: 'long', year: 'numeric' })
)

function computeEvents() {
  const map = {}
  for (const p of periods.value) {
    const start = new Date(p.start_date)
    const startStr = start.toISOString().split('T')[0]
    if (!p.end_date) {
      map[startStr] = 'start'
      continue
    }
    const end = new Date(p.end_date)
    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      const dateStr = new Date(d).toISOString().split('T')[0]
      map[dateStr] = d.getTime() === start.getTime() ? 'start' : 'period'
    }
  }
  if (prediction.value) {
    const start = new Date(prediction.value.next_start)
    for (let i = 0; i < prediction.value.period_length; i++) {
      const d = new Date(start)
      d.setDate(start.getDate() + i)
      const dateStr = d.toISOString().split('T')[0]
      if (!map[dateStr]) map[dateStr] = i === 0 ? 'prediction-start' : 'prediction'
    }
    const pmsStart = new Date(prediction.value.pms_start)
    const pmsEnd = new Date(prediction.value.pms_end)
    for (let d = new Date(pmsStart); d <= pmsEnd; d.setDate(d.getDate() + 1)) {
      const dateStr = d.toISOString().split('T')[0]
      if (!map[dateStr]) map[dateStr] = 'pms'
    }
  }
  events.value = map
}

function buildWeeks() {
  const start = new Date(current.value.getFullYear(), current.value.getMonth(), 1)
  const end = new Date(current.value.getFullYear(), current.value.getMonth() + 1, 0)
  const weeks = []
  let week = []

  for (let i = 0; i < start.getDay(); i++) {
    week.push({ text: '', date: null, isToday: false, isPeriod: false, isStart: false, isPms: false, isPrediction: false })
  }

  for (let day = 1; day <= end.getDate(); day++) {
    const date = new Date(current.value.getFullYear(), current.value.getMonth(), day)
    const dateStr = date.toISOString().split('T')[0]
    const type = events.value[dateStr]
    const isStart = type === 'start' || type === 'prediction-start'
    const isPrediction = type === 'prediction' || type === 'prediction-start'
    const isPeriod =
      type === 'start' ||
      type === 'period' ||
      type === 'prediction' ||
      type === 'prediction-start'
    const isPms = type === 'pms'
    const isToday = dateStr === new Date().toISOString().split('T')[0]
    week.push({ text: day, date: dateStr, isToday, isPeriod, isStart, isPms, isPrediction })
    if (week.length === 7) {
      weeks.push(week)
      week = []
    }
  }

  if (week.length) {
    while (week.length < 7)
      week.push({ text: '', date: null, isToday: false, isPeriod: false, isStart: false, isPms: false, isPrediction: false })
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

function openMenu(date, evt) {
  if (!date) return
  evt.stopPropagation()
  menu.value = { visible: true, x: evt.clientX, y: evt.clientY, date }
}

function closeMenu() {
  menu.value.visible = false
}

async function fetchUsers() {
  try {
    const res = await fetch('api/users')
    if (!res.ok) throw new Error('Request failed')
    users.value = await res.json()
    if (users.value.length && !selectedUser.value) {
      selectedUser.value = users.value[0].id
    }
  } catch (err) {
    console.error('Failed to load users', err)
  }
}

async function refreshPeriods() {
  if (!selectedUser.value) return
  try {
    const res = await fetch(`api/periods?user=${selectedUser.value}`)
    if (!res.ok) throw new Error('Request failed')
    periods.value = await res.json()
    computeEvents()
    weeks.value = buildWeeks()
  } catch (err) {
    console.error('Failed to load periods', err)
  }
}

async function addStart(date) {
  closeMenu()
  try {
    const res = await fetch('api/periods/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date, user: selectedUser.value })
    })
    if (!res.ok) throw new Error('Request failed')
    await refreshPeriods()
  } catch (err) {
    console.error('Failed to add start', err)
    alert('Failed to add start')
  }
}

async function removeStart(date) {
  closeMenu()
  try {
    const res = await fetch(`api/periods/start/${date}?user=${selectedUser.value}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('Request failed')
    await refreshPeriods()
  } catch (err) {
    console.error('Failed to remove start', err)
    alert('Failed to remove start')
  }
}

async function addEnd(date) {
  closeMenu()
  try {
    const res = await fetch('api/periods/end', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date, user: selectedUser.value })
    })
    if (!res.ok) throw new Error('Request failed')
    await refreshPeriods()
  } catch (err) {
    console.error('Failed to add end', err)
    alert('Failed to add end')
  }
}

async function removeEnd(date) {
  closeMenu()
  try {
    const res = await fetch(`api/periods/end/${date}?user=${selectedUser.value}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('Request failed')
    await refreshPeriods()
  } catch (err) {
    console.error('Failed to remove end', err)
    alert('Failed to remove end')
  }
}

async function clearAll() {
  if (!confirm('Delete all records?')) return
  try {
    const res = await fetch(`api/periods?user=${selectedUser.value}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('Request failed')
    await refreshPeriods()
    prediction.value = null
    computeEvents()
    weeks.value = buildWeeks()
  } catch (err) {
    console.error('Failed to clear records', err)
    alert('Failed to clear records')
  }
}

async function testDb() {
  try {
    const res = await fetch(`api/periods?user=${selectedUser.value}`)
    if (!res.ok) throw new Error('Request failed')
    const data = await res.json()
    alert(JSON.stringify(data))
  } catch (err) {
    console.error('Failed to test DB', err)
    alert('Failed to test DB')
  }
}

async function predictNext() {
  try {
    const res = await fetch(`api/prediction?user=${selectedUser.value}`)
    if (!res.ok) throw new Error('Request failed')
    const data = await res.json()
    prediction.value = data
    computeEvents()
    weeks.value = buildWeeks()
    if (data.next_start) {
      alert(
        `Next period expected on ${data.next_start} lasting ${data.period_length} days`
      )
    } else {
      alert('Not enough data for prediction')
    }
  } catch (err) {
    console.error('Failed to fetch prediction', err)
    alert('Failed to fetch prediction')
  }
}

onMounted(() => {
  window.addEventListener('click', closeMenu)
  fetchUsers()
})

watch(selectedUser, () => {
  prediction.value = null
  refreshPeriods()
})

onBeforeUnmount(() => {
  window.removeEventListener('click', closeMenu)
})
</script>

<style scoped>
@import '../styles/sidebar.css';

.user-select {
  margin-bottom: 0.5rem;
}

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

.calendar-grid td.period-start {
  background: #ff8080;
}

.calendar-grid td.prediction {
  background: #ffd9cc;
}

.calendar-grid td.prediction-start {
  background: #ffb3a7;
}

.calendar-grid td.pms {
  background: #cce5ff;
}

.calendar-grid td.clickable {
  cursor: pointer;
}

.context-menu {
  position: absolute;
  background: white;
  border: 1px solid #ccc;
  list-style: none;
  padding: 0;
  margin: 0;
  z-index: 1000;
}

.context-menu li {
  padding: 0.25rem 0.5rem;
  cursor: pointer;
}

.context-menu li:hover {
  background: #eee;
}
</style>

