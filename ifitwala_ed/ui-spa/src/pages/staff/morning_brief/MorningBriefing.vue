<template>
  <div class="min-h-screen bg-gray-50 p-6">
    <header class="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Morning Briefing</h1>
        <p class="text-gray-500 mt-1">Daily Operational & Academic Pulse</p>
      </div>
      <div class="flex items-center gap-3">
        <div class="text-right">
          <span class="block text-xs font-bold uppercase tracking-wider text-gray-400">Today</span>
          <span class="text-lg font-semibold text-gray-900">{{ formattedDate }}</span>
        </div>
        <button
          @click="widgets.reload()"
          class="ml-4 rounded-full p-2 text-gray-400 hover:bg-gray-200 hover:text-gray-600 transition-colors"
          title="Refresh Data"
        >
          <FeatherIcon name="refresh-cw" class="h-5 w-5" :class="{ 'animate-spin': widgets.loading }" />
        </button>
      </div>
    </header>

    <div v-if="widgets.loading" class="grid grid-cols-1 md:grid-cols-3 gap-6 animate-pulse">
      <div class="h-40 bg-gray-200 rounded-xl"></div>
      <div class="h-40 bg-gray-200 rounded-xl"></div>
      <div class="h-40 bg-gray-200 rounded-xl"></div>
    </div>

    <div v-else class="space-y-8">

      <section v-if="hasData('staff_birthdays')">
        <h2 class="text-sm font-bold uppercase tracking-wider text-gray-500 mb-4">Community Pulse</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

          <div class="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
            <div class="flex items-center gap-2 mb-4">
              <div class="p-2 bg-pink-50 rounded-lg text-pink-600">
                <FeatherIcon name="gift" class="h-5 w-5" />
              </div>
              <h3 class="font-semibold text-gray-900">Staff Birthdays</h3>
            </div>

            <div class="space-y-3">
              <div
                v-for="emp in widgets.data.staff_birthdays"
                :key="emp.name"
                class="flex items-center gap-3"
              >
                <div class="h-10 w-10 rounded-full bg-gray-100 overflow-hidden">
                  <img v-if="emp.image" :src="emp.image" class="h-full w-full object-cover" />
                  <div v-else class="h-full w-full flex items-center justify-center text-gray-400 text-xs font-bold">
                    {{ emp.name.substring(0,2) }}
                  </div>
                </div>
                <div>
                  <p class="text-sm font-medium text-gray-900">{{ emp.name }}</p>
                  <p class="text-xs text-gray-500">{{ emp.birthday_display }}</p>
                </div>
              </div>
              <p v-if="widgets.data.staff_birthdays.length === 0" class="text-sm text-gray-400 italic">
                No birthdays in the next 3 days.
              </p>
            </div>
          </div>

          </div>
      </section>

      <section v-if="hasData('clinic_volume') || hasData('admissions_pulse') || hasData('critical_incidents')">
        <h2 class="text-sm font-bold uppercase tracking-wider text-gray-500 mb-4">Operational Health</h2>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">

          <div v-if="widgets.data.critical_incidents !== undefined" class="bg-white p-5 rounded-xl shadow-sm border-l-4 border-red-500">
            <h3 class="text-xs font-bold text-gray-400 uppercase">Critical Incidents</h3>
            <div class="mt-2 text-3xl font-bold text-gray-900">{{ widgets.data.critical_incidents }}</div>
            <p class="text-xs text-red-600 mt-1 font-medium">Require Follow-up</p>
          </div>

          <div v-if="hasData('clinic_volume')" class="bg-white p-5 rounded-xl shadow-sm border border-gray-100 md:col-span-1">
            <div class="flex items-center gap-2 mb-3">
              <FeatherIcon name="activity" class="h-4 w-4 text-blue-500" />
              <h3 class="font-semibold text-gray-900 text-sm">Clinic Volume (3 Days)</h3>
            </div>
            <div class="space-y-2">
              <div v-for="day in widgets.data.clinic_volume" :key="day.date" class="flex justify-between items-center text-sm">
                <span class="text-gray-500">{{ day.date }}</span>
                <span class="font-mono font-medium" :class="day.count > 10 ? 'text-red-600' : 'text-gray-900'">
                  {{ day.count }} Visits
                </span>
              </div>
            </div>
          </div>

          <div v-if="widgets.data.admissions_pulse" class="bg-white p-5 rounded-xl shadow-sm border border-gray-100 md:col-span-2">
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-2">
                <FeatherIcon name="users" class="h-4 w-4 text-purple-500" />
                <h3 class="font-semibold text-gray-900 text-sm">Admissions (Last 7 Days)</h3>
              </div>
              <span class="text-2xl font-bold text-gray-900">{{ widgets.data.admissions_pulse.total_new_weekly }} New</span>
            </div>
            <div class="flex gap-2">
              <div
                v-for="stat in widgets.data.admissions_pulse.breakdown"
                :key="stat.application_status"
                class="px-3 py-1 bg-gray-100 rounded text-xs text-gray-600 font-medium"
              >
                {{ stat.application_status }}: {{ stat.count }}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section v-if="hasData('my_student_birthdays') || hasData('medical_context') || widgets.data.grading_velocity !== undefined">
        <h2 class="text-sm font-bold uppercase tracking-wider text-gray-500 mb-4">Classroom Context</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

          <div v-if="widgets.data.grading_velocity !== undefined" class="bg-white p-5 rounded-xl shadow-sm border-l-4 border-orange-400">
            <h3 class="text-xs font-bold text-gray-400 uppercase">Pending Grading</h3>
            <div class="mt-2 flex items-baseline gap-2">
              <span class="text-3xl font-bold text-gray-900">{{ widgets.data.grading_velocity }}</span>
              <span class="text-sm text-gray-500">tasks overdue</span>
            </div>
            <p class="text-xs text-orange-600 mt-2">Check Gradebook</p>
          </div>

          <div v-if="hasData('my_student_birthdays')" class="bg-white p-5 rounded-xl shadow-sm border border-gray-100">
            <div class="flex items-center gap-2 mb-3">
              <FeatherIcon name="smile" class="h-4 w-4 text-yellow-500" />
              <h3 class="font-semibold text-gray-900 text-sm">Student Birthdays Today</h3>
            </div>
            <ul class="space-y-2">
              <li v-for="stu in widgets.data.my_student_birthdays" :key="stu.first_name" class="flex items-center gap-2 text-sm text-gray-700">
                <div class="h-6 w-6 rounded-full bg-gray-100 overflow-hidden">
                  <img v-if="stu.student_image" :src="stu.student_image" class="h-full w-full object-cover" />
                </div>
                <span>{{ stu.first_name }} {{ stu.last_name }}</span>
              </li>
            </ul>
          </div>

          <div v-if="hasData('medical_context')" class="bg-white p-5 rounded-xl shadow-sm border-l-4 border-blue-400 md:col-span-3 lg:col-span-1">
            <div class="flex items-center gap-2 mb-3">
              <FeatherIcon name="info" class="h-4 w-4 text-blue-500" />
              <h3 class="font-semibold text-gray-900 text-sm">Medical Alerts (Your Classes)</h3>
            </div>
            <div class="space-y-3 max-h-48 overflow-y-auto">
              <div v-for="med in widgets.data.medical_context" :key="med.first_name" class="p-3 bg-blue-50 rounded text-sm">
                <p class="font-bold text-blue-900">{{ med.first_name }} {{ med.last_name }}</p>
                <p v-if="med.allergies" class="text-xs text-blue-700 mt-1">
                  <strong>Allergies:</strong> {{ med.food_allergies }}
                </p>
                <p v-if="med.medical_info" class="text-xs text-blue-700 mt-1">
                  <span v-html="med.medical_info"></span>
                </p>
              </div>
            </div>
          </div>

        </div>
      </section>

      <div v-if="isTotallyEmpty" class="text-center py-20 bg-white rounded-xl border border-dashed border-gray-300">
        <div class="h-12 w-12 mx-auto bg-gray-100 rounded-full flex items-center justify-center mb-3">
          <FeatherIcon name="sun" class="h-6 w-6 text-gray-400" />
        </div>
        <h3 class="text-gray-900 font-medium">Good Morning!</h3>
        <p class="text-gray-500 text-sm">No specific alerts or updates for your role today.</p>
      </div>

    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { createResource, FeatherIcon } from 'frappe-ui'

// Fetch the Widget Dictionary
const widgets = createResource({
  url: 'ifitwala_ed.api.morning_brief.get_briefing_widgets',
  auto: true
})

// Helper to safely check if a list widget has data
function hasData(key) {
  return widgets.data && widgets.data[key] && Array.isArray(widgets.data[key]) && widgets.data[key].length > 0
}

// Check if we received absolutely nothing relevant
const isTotallyEmpty = computed(() => {
  if (!widgets.data) return false
  const keys = Object.keys(widgets.data)
  // If keys exist but arrays are empty, it's still "empty" visually for some
  return keys.length === 0
})

const formattedDate = computed(() => {
  const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  return new Date().toLocaleDateString('en-GB', options);
})
</script>
