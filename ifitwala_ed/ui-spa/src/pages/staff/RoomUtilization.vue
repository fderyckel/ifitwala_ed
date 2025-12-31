<!-- ifitwala_ed/ui-spa/src/pages/staff/RoomUtilization.vue -->
<template>
  <div class="analytics-shell">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="type-h2 text-canopy">Room Utilization</h1>
        <p class="type-caption text-slate-500">
          Find free rooms and understand usage across time and capacity.
        </p>
      </div>
      <button
        class="fui-btn-primary rounded-full px-4 py-1.5 text-sm font-medium transition active:scale-95"
        @click="refreshMetrics"
      >
        Refresh
      </button>
    </header>

    <FiltersBar class="analytics-filters !bg-white">
      <div class="flex flex-col gap-1">
        <label class="type-label">School</label>
        <select
          v-model="filters.school"
          class="h-9 min-w-[160px] rounded-md border px-2 text-sm"
        >
          <option value="">Select School</option>
          <option v-for="s in schools" :key="s.name" :value="s.name">{{ s.label }}</option>
        </select>
      </div>

      <div class="flex flex-col gap-1">
        <label class="type-label">Free Rooms Date</label>
        <input
          type="date"
          v-model="filters.date"
          class="h-9 rounded-md border px-2 text-sm"
        />
      </div>

      <div class="flex flex-col gap-1">
        <label class="type-label">Window Start</label>
        <input
          type="time"
          v-model="filters.start_time"
          class="h-9 rounded-md border px-2 text-sm"
        />
      </div>

      <div class="flex flex-col gap-1">
        <label class="type-label">Window End</label>
        <input
          type="time"
          v-model="filters.end_time"
          class="h-9 rounded-md border px-2 text-sm"
        />
      </div>

      <div class="flex flex-col gap-1">
        <label class="type-label">Utilization Range</label>
        <div class="flex items-center gap-2">
          <input
            type="date"
            v-model="filters.from_date"
            class="h-9 rounded-md border px-2 text-sm"
          />
          <span class="text-slate-300">-</span>
          <input
            type="date"
            v-model="filters.to_date"
            class="h-9 rounded-md border px-2 text-sm"
          />
        </div>
      </div>

      <div class="flex flex-col gap-1">
        <label class="type-label">Day Start</label>
        <input
          type="time"
          v-model="filters.day_start_time"
          class="h-9 rounded-md border px-2 text-sm"
        />
      </div>

      <div class="flex flex-col gap-1">
        <label class="type-label">Day End</label>
        <input
          type="time"
          v-model="filters.day_end_time"
          class="h-9 rounded-md border px-2 text-sm"
        />
      </div>
    </FiltersBar>

    <KpiRow :items="kpiItems" />

    <section class="analytics-card">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 class="analytics-card__title">Free Rooms Finder</h3>
          <p class="analytics-card__meta">Checks meetings and school events.</p>
        </div>
        <button
          class="fui-btn-primary rounded-full px-4 py-1.5 text-sm font-medium transition active:scale-95"
          :disabled="freeRoomsLoading || !filters.date || !filters.start_time || !filters.end_time"
          @click="loadFreeRooms"
        >
          Find Free Rooms
        </button>
      </div>

      <div class="flex flex-wrap gap-2">
        <StatsTile
          label="Free Rooms"
          :value="freeRooms.length"
          :tone="freeRooms.length ? 'success' : 'warning'"
        />
        <StatsTile label="Window" :value="freeWindowLabel" tone="info" />
      </div>

      <div v-if="freeRoomsLoading" class="py-6 text-center text-sm text-slate-500">
        Loading free rooms...
      </div>
      <div v-else-if="!freeRooms.length" class="analytics-empty">
        No free rooms found for this window.
      </div>
      <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="room in freeRooms"
          :key="room.room"
          class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm"
        >
          <div class="text-sm font-semibold text-ink">{{ room.room_name }}</div>
          <div class="text-xs text-slate-500">Building: {{ room.building || '—' }}</div>
          <div class="text-xs text-slate-500">Capacity: {{ room.max_capacity ?? '—' }}</div>
        </article>
      </div>
    </section>

    <section class="analytics-card">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 class="analytics-card__title">Time Utilization</h3>
          <p class="analytics-card__meta">
            Booked minutes within the day window, per room.
          </p>
        </div>
        <StatsTile label="Average Utilization" :value="avgUtilizationLabel" tone="info" />
      </div>

      <div v-if="timeUtilLoading" class="py-6 text-center text-sm text-slate-500">
        Loading time utilization...
      </div>
      <div v-else-if="!timeRooms.length" class="analytics-empty">
        No utilization data yet. Select a school and date range.
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead class="text-left text-xs uppercase tracking-wide text-slate-400">
            <tr>
              <th class="px-2 py-2">Room</th>
              <th class="px-2 py-2">Booked Hours</th>
              <th class="px-2 py-2">Available Hours</th>
              <th class="px-2 py-2">Utilization</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="room in timeRooms"
              :key="room.room"
              class="border-t border-slate-100"
            >
              <td class="px-2 py-2 font-medium text-ink">{{ room.room_name }}</td>
              <td class="px-2 py-2 text-slate-600">{{ minutesToHours(room.booked_minutes) }}</td>
              <td class="px-2 py-2 text-slate-600">{{ minutesToHours(room.available_minutes) }}</td>
              <td class="px-2 py-2">
                <span
                  class="rounded-full px-2 py-0.5 text-xs"
                  :class="utilizationBadge(room.utilization_pct)"
                >
                  {{ room.utilization_pct.toFixed(1) }}%
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="analytics-card">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 class="analytics-card__title">Capacity Utilization</h3>
          <p class="analytics-card__meta">
            Meeting participants compared to room capacity.
          </p>
        </div>
        <StatsTile label="Over-Cap Rooms" :value="overCapRooms" tone="warning" />
      </div>

      <div v-if="capacityLoading" class="py-6 text-center text-sm text-slate-500">
        Loading capacity utilization...
      </div>
      <div v-else-if="!capacityRooms.length" class="analytics-empty">
        No capacity data yet. Select a school and date range.
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead class="text-left text-xs uppercase tracking-wide text-slate-400">
            <tr>
              <th class="px-2 py-2">Room</th>
              <th class="px-2 py-2">Max Cap</th>
              <th class="px-2 py-2">Avg Attendees</th>
              <th class="px-2 py-2">Peak Attendees</th>
              <th class="px-2 py-2">Avg %</th>
              <th class="px-2 py-2">Peak %</th>
              <th class="px-2 py-2">Over-Cap</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="room in capacityRooms"
              :key="room.room"
              class="border-t border-slate-100"
            >
              <td class="px-2 py-2 font-medium text-ink">{{ room.room_name }}</td>
              <td class="px-2 py-2 text-slate-600">{{ room.max_capacity ?? '—' }}</td>
              <td class="px-2 py-2 text-slate-600">{{ room.avg_attendees }}</td>
              <td class="px-2 py-2 text-slate-600">{{ room.peak_attendees }}</td>
              <td class="px-2 py-2 text-slate-600">{{ formatPct(room.avg_capacity_pct) }}</td>
              <td class="px-2 py-2 text-slate-600">{{ formatPct(room.peak_capacity_pct) }}</td>
              <td class="px-2 py-2">
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-xs"
                  :class="overCapBadge(room.over_capacity_count)"
                >
                  {{ room.over_capacity_count }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { createResource } from 'frappe-ui'

import FiltersBar from '@/components/analytics/FiltersBar.vue'
import StatsTile from '@/components/analytics/StatsTile.vue'
import KpiRow from '@/components/analytics/KpiRow.vue'

type SchoolOption = { name: string; label: string }

type FreeRoom = {
  room: string
  room_name: string
  building?: string
  max_capacity?: number
}

type TimeRoom = {
  room: string
  room_name: string
  booked_minutes: number
  available_minutes: number
  utilization_pct: number
}

type CapacityRoom = {
  room: string
  room_name: string
  max_capacity?: number | null
  meetings: number
  avg_attendees: number
  peak_attendees: number
  avg_capacity_pct?: number | null
  peak_capacity_pct?: number | null
  over_capacity_count: number
}

const today = new Date().toISOString().slice(0, 10)

const filters = ref({
  school: '',
  date: today,
  start_time: '09:00',
  end_time: '10:15',
  from_date: today,
  to_date: today,
  day_start_time: '07:00',
  day_end_time: '16:00',
})

const filterMetaResource = createResource({
  url: 'ifitwala_ed.api.room_utilization.get_room_utilization_filter_meta',
  method: 'GET',
  auto: true,
})

const filterMeta = computed(() => (filterMetaResource.data as any) || {})
const schools = computed<SchoolOption[]>(() => filterMeta.value.schools || [])

watch(
  filterMeta,
  (data) => {
    if (!data) return
    if (data.default_school && !filters.value.school) {
      filters.value.school = data.default_school
    }
  },
  { immediate: true }
)

const freeRoomsResource = createResource({
  url: 'ifitwala_ed.api.room_utilization.get_free_rooms',
  method: 'POST',
  auto: false,
})

const timeUtilResource = createResource({
  url: 'ifitwala_ed.api.room_utilization.get_room_time_utilization',
  method: 'POST',
  auto: false,
})

const capacityResource = createResource({
  url: 'ifitwala_ed.api.room_utilization.get_room_capacity_utilization',
  method: 'POST',
  auto: false,
})

const freeRooms = computed<FreeRoom[]>(() => freeRoomsResource.data?.rooms || [])
const timeRooms = computed<TimeRoom[]>(() => timeUtilResource.data?.rooms || [])
const capacityRooms = computed<CapacityRoom[]>(() => capacityResource.data?.rooms || [])

const freeRoomsLoading = computed(() => freeRoomsResource.loading)
const timeUtilLoading = computed(() => timeUtilResource.loading)
const capacityLoading = computed(() => capacityResource.loading)

const freeWindowLabel = computed(() => {
  if (!filters.value.date || !filters.value.start_time || !filters.value.end_time) return '—'
  return `${filters.value.date} ${filters.value.start_time}–${filters.value.end_time}`
})

const avgUtilizationLabel = computed(() => {
  if (!timeRooms.value.length) return '—'
  const total = timeRooms.value.reduce((sum, room) => sum + room.utilization_pct, 0)
  const avg = total / timeRooms.value.length
  return `${avg.toFixed(1)}%`
})

const overCapRooms = computed(() => {
  if (!capacityRooms.value.length) return 0
  return capacityRooms.value.filter((room) => room.over_capacity_count > 0).length
})

const kpiItems = computed(() => [
  {
    id: 'free_rooms',
    label: 'Free Rooms (last search)',
    value: freeRooms.value.length,
  },
  {
    id: 'total_rooms',
    label: 'Rooms in Scope',
    value: timeRooms.value.length || capacityRooms.value.length || '—',
  },
  {
    id: 'avg_util',
    label: 'Average Utilization',
    value: avgUtilizationLabel.value,
  },
  {
    id: 'over_cap',
    label: 'Over-Cap Rooms',
    value: overCapRooms.value,
  },
])

function minutesToHours(minutes: number) {
  const hours = minutes / 60
  return `${hours.toFixed(1)}h`
}

function formatPct(value?: number | null) {
  if (value === null || value === undefined) return '—'
  return `${value.toFixed(1)}%`
}

function utilizationBadge(value: number) {
  if (value >= 70) {
    return 'bg-[rgb(var(--flame-rgb)/0.12)] text-[rgb(var(--flame-rgb))]'
  }
  if (value >= 40) {
    return 'bg-[rgb(var(--jacaranda-rgb)/0.12)] text-[rgb(var(--jacaranda-rgb))]'
  }
  return 'bg-[rgb(var(--canopy-rgb)/0.08)] text-[rgb(var(--canopy-rgb))]'
}

function overCapBadge(count: number) {
  if (count > 0) {
    return 'bg-[rgb(var(--flame-rgb)/0.12)] text-[rgb(var(--flame-rgb))]'
  }
  return 'bg-[rgb(var(--canopy-rgb)/0.08)] text-[rgb(var(--canopy-rgb))]'
}

async function loadFreeRooms() {
  await freeRoomsResource.submit({
    filters: {
      school: filters.value.school,
      date: filters.value.date,
      start_time: filters.value.start_time,
      end_time: filters.value.end_time,
    },
  })
}

async function loadTimeUtil() {
  if (!filters.value.school || !filters.value.from_date || !filters.value.to_date) return
  await timeUtilResource.submit({
    filters: {
      school: filters.value.school,
      from_date: filters.value.from_date,
      to_date: filters.value.to_date,
      day_start_time: filters.value.day_start_time,
      day_end_time: filters.value.day_end_time,
    },
  })
}

async function loadCapacityUtil() {
  if (!filters.value.school || !filters.value.from_date || !filters.value.to_date) return
  await capacityResource.submit({
    filters: {
      school: filters.value.school,
      from_date: filters.value.from_date,
      to_date: filters.value.to_date,
    },
  })
}

let timeDebounce: number | undefined
let capacityDebounce: number | undefined

function debounceTimeUtil() {
  window.clearTimeout(timeDebounce)
  timeDebounce = window.setTimeout(() => {
    loadTimeUtil()
  }, 400)
}

function debounceCapacityUtil() {
  window.clearTimeout(capacityDebounce)
  capacityDebounce = window.setTimeout(() => {
    loadCapacityUtil()
  }, 400)
}

watch(
  () => [
    filters.value.school,
    filters.value.from_date,
    filters.value.to_date,
    filters.value.day_start_time,
    filters.value.day_end_time,
  ],
  () => {
    debounceTimeUtil()
  }
)

watch(
  () => [filters.value.school, filters.value.from_date, filters.value.to_date],
  () => {
    debounceCapacityUtil()
  }
)

function refreshMetrics() {
  loadTimeUtil()
  loadCapacityUtil()
}

onMounted(() => {
  refreshMetrics()
})
</script>
