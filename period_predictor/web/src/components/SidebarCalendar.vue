<template>
  <aside class="sidebar" tabindex="0">
    <FullCalendar
      defaultView="dayGridMonth"
      :plugins="calendarPlugins"
      :events="events"
      aria-label="Period calendar"
    />
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

async function startPeriod() {
  await fetch('/api/period/start', { method: 'POST' })
}

async function endPeriod() {
  await fetch('/api/period/end', { method: 'POST' })
}

function handleKey(e) {
  const key = e.key.toLowerCase()
  if (key === 's') {
    startPeriod()
  } else if (key === 'e') {
    endPeriod()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKey)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKey)
})
</script>

<style scoped>
@import '../styles/sidebar.css';
</style>
