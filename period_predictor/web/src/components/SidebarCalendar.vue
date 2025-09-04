<template>
  <aside class="sidebar" tabindex="0">
    <div class="calendar" aria-label="Period calendar">
      <FullCalendar
        initialView="dayGridMonth"
        :plugins="calendarPlugins"
        :events="events"
        :headerToolbar="toolbarOptions"
      />
    </div>
    <div class="controls">
      <button
        @click="startPeriod"
        aria-label="Start period"
        tabindex="1"
      >
        I got my period
      </button>
      <button
        @click="endPeriod"
        aria-label="End period"
        tabindex="2"
      >
        I have finished my period
      </button>
    </div>
  </aside>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'

const events = ref([])
const calendarPlugins = [dayGridPlugin]
const toolbarOptions = {
  left: 'prev,next',
  center: 'title',
  right: ''
}

async function startPeriod() {
  const today = new Date().toISOString().split('T')[0]
  try {
    const res = await fetch('api/periods', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date: today }),
    })
    if (!res.ok) throw new Error('Request failed')
    events.value = [...events.value, { title: 'Period', start: today }]
    alert('Period logged!')
  } catch (err) {
    alert('Failed to log period')
  }
}

async function endPeriod() {
  // Endpoint not yet implemented
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
  const res = await fetch('api/periods')
  const dates = await res.json()
  events.value = dates.map((d) => ({ title: 'Period', start: d }))
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKey)
})
</script>

<style scoped>
@import '../styles/sidebar.css';
</style>
