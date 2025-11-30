<!-- ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue -->
<template>
  <div class="staff-shell space-y-10">

    <!-- ============================================================
         HEADER / GREETING
       ============================================================ -->
    <header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">

      <div>
        <h1 class="text-3xl font-bold tracking-tight text-ink sm:text-4xl">
          {{ greeting }},
          <span class="text-canopy">{{ firstName }}</span>
        </h1>
      </div>

      <RouterLink
        :to="{ name: 'MorningBriefing' }"
        target="_blank"
        class="inline-flex items-center gap-2 rounded-full bg-jacaranda px-5 py-2.5 text-sm font-bold text-white shadow-soft
               transition-transform hover:-translate-y-0.5 hover:shadow-strong"
      >
        <FeatherIcon name="sun" class="h-4 w-4 text-yellow-300" />
        <span>Morning Brief</span>
      </RouterLink>

    </header>


    <!-- ============================================================
         CALENDAR
       ============================================================ -->
    <ScheduleCalendar />


    <!-- ============================================================
         TWO-COLUMN GRID
       ============================================================ -->
    <section class="grid grid-cols-1 gap-10 lg:grid-cols-12">

      <!-- LEFT COL: TASKS / FOCUS -------------------------------->
      <div class="lg:col-span-8 space-y-4">

        <!-- Section Title -->
        <div class="flex items-center justify-between px-1">
          <h3 class="flex items-center gap-2 text-lg font-semibold text-canopy">
            <FeatherIcon name="list" class="h-4 w-4 opacity-70" />
            Your Focus
          </h3>
          <span class="text-xs font-semibold uppercase tracking-wider text-slate-token/70">
            Pending Tasks
          </span>
        </div>

        <!-- Palette card wrapper -->
        <div class="palette-card rounded-2xl overflow-hidden">

          <!-- Example tasks (replace with real later) -->
          <div
            class="group flex cursor-pointer items-start gap-4 border-b border-[rgba(var(--sand-rgb),0.4)]
                   bg-white px-6 py-4 transition-colors hover:bg-sky/20 last:border-0"
          >
            <div class="mt-1 h-5 w-5 rounded border-2 border-slate-token/60 transition-colors group-hover:border-jacaranda"></div>

            <div class="flex-1">
              <p class="text-sm font-medium text-ink transition-colors group-hover:text-jacaranda">
                Submit Semester Reports for Year 9
              </p>
              <div class="mt-1 flex items-center gap-3 text-xs text-slate-token/70">
                <span class="flex items-center gap-1 text-flame font-medium">
                  <FeatherIcon name="alert-circle" class="h-3 w-3" />
                  Due Today
                </span>
                <span>•</span>
                <span>Academics</span>
              </div>
            </div>
          </div>

          <div
            class="group flex cursor-pointer items-start gap-4 bg-white px-6 py-4 transition-colors hover:bg-sky/20"
          >
            <div class="mt-1 h-5 w-5 rounded border-2 border-slate-token/60 transition-colors group-hover:border-jacaranda"></div>

            <div class="flex-1">
              <p class="text-sm font-medium text-ink transition-colors group-hover:text-jacaranda">
                Approve Field Trip: Grade 10 Science
              </p>
              <div class="mt-1 flex items-center gap-3 text-xs text-slate-token/70">
                <span>Tomorrow</span>
                <span>•</span>
                <span>Approval</span>
              </div>
            </div>
          </div>

        </div>
      </div>


      <!-- RIGHT COL: QUICK ACTIONS ------------------------------->
      <div class="lg:col-span-4 space-y-4">

        <h3 class="px-1 text-lg font-semibold text-canopy">
          Quick Actions
        </h3>

        <div class="grid gap-3">

          <!-- Standard Quick Actions -->
          <RouterLink
            v-for="action in quickActions"
            :key="action.label"
            :to="action.to"
            class="action-tile group"
          >

            <!-- Icon container -->
            <div class="action-tile__icon">
              <FeatherIcon :name="action.icon" class="h-6 w-6" />
            </div>

            <!-- Text -->
            <div class="flex-1 min-w-0">
              <p class="font-semibold text-ink transition-colors group-hover:text-jacaranda">
                {{ action.label }}
              </p>
              <p class="truncate text-xs text-slate-token/70">
                {{ action.caption }}
              </p>
            </div>

            <FeatherIcon
              name="chevron-right"
              class="h-4 w-4 text-slate-token/40 transition-colors group-hover:text-jacaranda"
            />

          </RouterLink>

          <!-- Switch to Desk -->
          <a
            href="/app"
            class="action-tile group border-dashed border-slate-token/40 bg-white"
          >
            <div class="action-tile__icon bg-slate-100 text-slate-500 group-hover:bg-slate-200">
              <FeatherIcon name="monitor" class="h-5 w-5" />
            </div>

            <div class="flex-1">
              <p class="text-sm font-semibold text-slate-token/70 transition-colors group-hover:text-ink">
                Switch to Desk
              </p>
              <p class="text-[10px] uppercase tracking-wider text-slate-token/50">
                Classic ERP View
              </p>
            </div>

            <FeatherIcon name="chevron-right" class="h-4 w-4 text-slate-token/40" />
          </a>

        </div>

      </div>

    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { FeatherIcon } from 'frappe-ui'
import ScheduleCalendar from '@/components/calendar/ScheduleCalendar.vue'

/* USER --------------------------------------------------------- */
const userDoc = ref<any | null>(null)

onMounted(async () => {
  try {
    const whoRes = await fetch('/api/method/frappe.auth.get_logged_user', { credentials: 'include' })
    const whoJson = await whoRes.json()
    const userId = whoJson.message

    if (!userId || userId === 'Guest') return

    const userRes = await fetch(`/api/resource/User/${encodeURIComponent(userId)}`, {
      credentials: 'include',
    })
    const userJson = await userRes.json()
    userDoc.value = userJson.data || null
  } catch (err) {
    console.error('[StaffHome] Failed to load user doc:', err)
  }
})

const firstName = computed(() => {
  const doc = userDoc.value
  if (!doc) return 'Staff'
  if (doc.first_name) return doc.first_name
  if (doc.full_name) return doc.full_name.split(' ')[0]
  return 'Staff'
})

/* QUICK ACTIONS ------------------------------------------------ */
const quickActions = [
  {
    label: 'Plan Student Groups',
    caption: 'Manage rosters, rotation days & instructors',
    icon: 'layout',
    to: { name: 'staff-student-groups' },
  },
  {
    label: 'Take Attendance',
    caption: 'Record attendance for classes today',
    icon: 'check-square',
    to: { name: 'staff-attendance' },
  },
  {
    label: 'Update Gradebook',
    caption: 'Capture evidence, notes, and marks',
    icon: 'edit-3',
    to: { name: 'staff-gradebook' },
  },
]

/* GREETING ----------------------------------------------------- */
const now = new Date()
const greeting = computed(() => {
  const hour = now.getHours()
  return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
})
</script>
