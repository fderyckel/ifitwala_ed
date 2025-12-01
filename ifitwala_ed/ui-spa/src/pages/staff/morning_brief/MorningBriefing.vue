<template>
  <div class="min-h-screen bg-transparent p-4 sm:p-6 space-y-8">

    <header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 class="text-3xl font-bold tracking-tight text-heading">
          Morning Briefing
        </h1>
        <p class="text-slate-500 mt-1 font-medium">Daily Operational & Academic Pulse</p>
      </div>
      <div class="flex items-center gap-3">
        <div class="text-right">
          <span class="section-header block mb-0.5">Today</span>
          <span class="text-lg font-semibold text-ink">{{ formattedDate }}</span>
        </div>

        <button
          @click="widgets.reload()"
          class="remark-btn flex items-center justify-center ml-2"
          title="Refresh Data"
        >
          <FeatherIcon name="refresh-cw" class="h-4 w-4" :class="{ 'animate-spin': widgets.loading }" />
        </button>
      </div>
    </header>

    <div v-if="widgets.loading" class="grid grid-cols-1 md:grid-cols-3 gap-6 animate-pulse">
      <div class="h-40 bg-slate-100/50 rounded-2xl"></div>
      <div class="h-40 bg-slate-100/50 rounded-2xl"></div>
      <div class="h-40 bg-slate-100/50 rounded-2xl"></div>
    </div>

    <div v-else class="space-y-8">

      <section v-if="hasData('staff_birthdays')">
        <h2 class="section-header mb-4 flex items-center gap-2">
          <FeatherIcon name="heart" class="h-3 w-3" />
          Community Pulse
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

          <div class="paper-card p-5 relative overflow-hidden group">
            <div class="flex items-center gap-2 mb-4">
              <div class="h-8 w-8 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center">
                <FeatherIcon name="gift" class="h-4 w-4" />
              </div>
              <h3 class="font-semibold text-canopy">Staff Birthdays</h3>
            </div>

            <div class="space-y-3">
              <div
                v-for="emp in widgets.data.staff_birthdays"
                :key="emp.name"
                class="flex items-center gap-3"
              >
                <div class="h-10 w-10 rounded-xl overflow-hidden shadow-inner bg-slate-100 ring-1 ring-border/85">
                  <img v-if="emp.image" :src="emp.image" class="h-full w-full object-cover" />
                  <div v-else class="h-full w-full flex items-center justify-center text-slate-400 text-xs font-bold">
                    {{ emp.name.substring(0,2) }}
                  </div>
                </div>
                <div>
                  <p class="text-sm font-medium text-ink">{{ emp.name }}</p>
                  <span class="inline-chip inline-chip--birthday">
                    {{ emp.birthday_display }}
                  </span>
                </div>
              </div>
              <p v-if="widgets.data.staff_birthdays.length === 0" class="text-sm text-slate-400 italic">
                No birthdays in the next 3 days.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section v-if="hasData('clinic_volume') || hasData('admissions_pulse') || widgets.data?.critical_incidents !== undefined">
        <h2 class="section-header mb-4 flex items-center gap-2">
          <FeatherIcon name="activity" class="h-3 w-3" />
          Operational Health
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">

          <div v-if="widgets.data?.critical_incidents !== undefined" class="paper-card p-5 border-l-4 border-l-flame">
            <h3 class="section-header !text-flame/80 mb-1">Critical Incidents</h3>
            <div class="text-3xl font-bold text-ink">{{ widgets.data.critical_incidents }}</div>
            <p class="text-xs text-flame mt-1 font-medium flex items-center gap-1">
              <FeatherIcon name="alert-circle" class="h-3 w-3" /> Require Follow-up
            </p>
          </div>

          <div v-if="hasData('clinic_volume')" class="paper-card p-5 md:col-span-1">
            <div class="flex items-center gap-2 mb-3">
              <div class="h-8 w-8 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center">
                <FeatherIcon name="thermometer" class="h-4 w-4" />
              </div>
              <h3 class="font-semibold text-canopy text-sm">Clinic Volume (3 Days)</h3>
            </div>
            <div class="space-y-2">
              <div v-for="day in widgets.data.clinic_volume" :key="day.date" class="flex justify-between items-center text-sm">
                <span class="text-slate-500">{{ day.date }}</span>
                <span class="font-mono font-medium" :class="day.count > 10 ? 'text-flame' : 'text-ink'">
                  {{ day.count }} Visits
                </span>
              </div>
            </div>
          </div>

          <div v-if="widgets.data?.admissions_pulse" class="paper-card p-5 md:col-span-2">
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-2">
                <div class="h-8 w-8 rounded-full bg-purple-50 text-purple-600 flex items-center justify-center">
                  <FeatherIcon name="users" class="h-4 w-4" />
                </div>
                <h3 class="font-semibold text-canopy text-sm">Admissions (Last 7 Days)</h3>
              </div>
              <span class="text-2xl font-bold text-ink">{{ widgets.data.admissions_pulse.total_new_weekly }} <span class="text-sm font-normal text-slate-500">New</span></span>
            </div>
            <div class="flex flex-wrap gap-2">
              <div
                v-for="stat in widgets.data.admissions_pulse.breakdown"
                :key="stat.application_status"
                class="inline-chip bg-slate-100 text-slate-600 border border-slate-200"
              >
                {{ stat.application_status }}: {{ stat.count }}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section v-if="hasData('my_student_birthdays') || hasData('medical_context') || widgets.data?.grading_velocity !== undefined">
        <h2 class="section-header mb-4 flex items-center gap-2">
          <FeatherIcon name="book-open" class="h-3 w-3" />
          Classroom Context
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

          <div v-if="widgets.data?.grading_velocity !== undefined" class="paper-card p-5 border-l-4 border-l-clay">
            <h3 class="section-header !text-clay/80 mb-1">Pending Grading</h3>
            <div class="mt-2 flex items-baseline gap-2">
              <span class="text-3xl font-bold text-ink">{{ widgets.data.grading_velocity }}</span>
              <span class="text-sm text-slate-500">tasks overdue</span>
            </div>
            <p class="text-xs text-clay mt-2 font-medium">Check Gradebook</p>
          </div>

          <div v-if="hasData('my_student_birthdays')" class="paper-card p-5">
            <div class="flex items-center gap-2 mb-3">
              <div class="h-8 w-8 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center">
                <FeatherIcon name="smile" class="h-4 w-4" />
              </div>
              <h3 class="font-semibold text-canopy text-sm">Student Birthdays Today</h3>
            </div>
            <ul class="space-y-3">
              <li v-for="stu in widgets.data.my_student_birthdays" :key="stu.first_name" class="flex items-center gap-3">
                 <div class="h-8 w-8 rounded-lg overflow-hidden bg-slate-100 ring-1 ring-border/50">
                   <img v-if="stu.student_image" :src="stu.student_image" class="h-full w-full object-cover" />
                 </div>
                <span class="text-sm font-medium text-ink">{{ stu.first_name }} {{ stu.last_name }}</span>
              </li>
            </ul>
          </div>

          <div v-if="hasData('medical_context')" class="paper-card p-5 border-l-4 border-l-sky md:col-span-3 lg:col-span-1">
            <div class="flex items-center gap-2 mb-3">
              <div class="h-8 w-8 rounded-full bg-sky text-canopy flex items-center justify-center">
                <FeatherIcon name="info" class="h-4 w-4" />
              </div>
              <h3 class="font-semibold text-canopy text-sm">Medical Alerts (Your Classes)</h3>
            </div>
            <div class="space-y-3 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
              <div v-for="med in widgets.data.medical_context" :key="med.first_name" class="p-3 bg-sky/50 rounded-lg text-sm border border-sky">
                <p class="font-bold text-canopy">{{ med.first_name }} {{ med.last_name }}</p>
                <p v-if="med.allergies" class="text-xs text-slate-600 mt-1">
                  <strong>Allergies:</strong> {{ med.food_allergies }}
                </p>
                <p v-if="med.medical_info" class="text-xs text-slate-600 mt-1">
                  <span v-html="med.medical_info"></span>
                </p>
              </div>
            </div>
          </div>

        </div>
      </section>

      <div v-if="isTotallyEmpty" class="text-center py-20 paper-card-frosted">
        <div class="h-14 w-14 mx-auto bg-white rounded-full shadow-sm flex items-center justify-center mb-4 ring-1 ring-border">
          <FeatherIcon name="sun" class="h-6 w-6 text-amber-500" />
        </div>
        <h3 class="text-canopy font-semibold text-lg">Good Morning!</h3>
        <p class="text-slate-500 text-sm mt-1">No specific alerts or updates for your role today.</p>
      </div>

    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { createResource, FeatherIcon } from 'frappe-ui'

// Fetch the Widget Dictionary
// FIX: Removed duplicate 'ifitwala_ed' from the path
const widgets = createResource({
  url: 'ifitwala_ed.api.morning_brief.get_briefing_widgets',
  auto: true
})

// Helper to safely check if a list widget has data
// FIX: Added safe navigation ?. to avoid null errors
function hasData(key) {
  return widgets.data && widgets.data[key] && Array.isArray(widgets.data[key]) && widgets.data[key].length > 0
}

// Check if we received absolutely nothing relevant
const isTotallyEmpty = computed(() => {
  if (!widgets.data) return false
  const keys = Object.keys(widgets.data)
  return keys.length === 0
})

const formattedDate = computed(() => {
  const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  return new Date().toLocaleDateString('en-GB', options);
})
</script>
