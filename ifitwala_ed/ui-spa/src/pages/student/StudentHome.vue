<script setup lang="ts">
import { RouterLink } from 'vue-router'

// If/when you want real data, you can wire API calls here.
// Example (later): fetch courses, tasks, etc. using your whitelisted methods.
// Keeping this page static for now to avoid API shape guesses.
</script>

<template>
  <div class="space-y-6">
    <!-- Header + quick action -->
    <header class="flex items-center justify-between">
      <h1 class="text-xl font-semibold">Dashboard</h1>
      <RouterLink
        to="/portal/student/profile"
        class="inline-flex items-center rounded-xl border px-3 py-1.5 text-sm hover:bg-gray-50"
      >
        <span class="mr-2">⚙️</span>
        Settings
      </RouterLink>
    </header>

    <!-- My Tasks Calendar -->
    <section aria-labelledby="tasksLabel">
      <div class="rounded-2xl border bg-white p-4 shadow-sm">
        <div class="mb-3 flex items-center justify-between">
          <h2 id="tasksLabel" class="text-base font-medium">My Tasks Calendar</h2>
          <span class="text-sm text-gray-500">Coming soon</span>
        </div>
        <div
          id="task-calendar"
          class="flex h-64 items-center justify-center rounded-lg bg-gray-50 text-gray-400"
        >
          FullCalendar integration later
        </div>
      </div>
    </section>

    <!-- Schedule Calendar -->
    <section aria-labelledby="scheduleLabel">
      <div class="rounded-2xl border bg-white p-4 shadow-sm">
        <div class="mb-3 flex items-center justify-between">
          <h2 id="scheduleLabel" class="text-base font-medium">Schedule Calendar</h2>
          <span class="text-sm text-gray-500">Placeholder</span>
        </div>
        <div
          id="schedule-calendar"
          class="flex h-64 items-center justify-center rounded-lg bg-gray-50 text-gray-400"
        >
          Calendar goes here
        </div>
      </div>
    </section>

    <!-- More -->
    <section aria-labelledby="moreLabel">
      <h2 id="moreLabel" class="mb-2 text-base font-medium">More</h2>
      <div id="extra-cards" class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        <!-- Student Log -->
        <RouterLink
          to="/portal/student/logs"
          class="group block rounded-2xl border bg-white p-4 shadow-sm transition hover:shadow"
        >
          <div class="mb-2 flex items-start justify-between">
            <h3 class="text-sm font-semibold">Student Log</h3>
            <span aria-hidden="true">🗒️</span>
          </div>
          <p class="mb-3 text-sm text-gray-500">
            View your socio-emotional notes and follow-ups.
          </p>
          <span
            class="inline-flex items-center rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white group-hover:bg-blue-700"
            >Open</span
          >
        </RouterLink>

        <!-- Wellbeing -->
        <RouterLink
          to="/portal/wellbeing"
          class="group block rounded-2xl border bg-white p-4 shadow-sm transition hover:shadow"
        >
          <div class="mb-2 flex items-start justify-between">
            <h3 class="text-sm font-semibold">Wellbeing</h3>
            <span aria-hidden="true">💗</span>
          </div>
          <p class="mb-3 text-sm text-gray-500">Resources and check-ins.</p>
          <span
            class="inline-flex items-center rounded-lg border px-3 py-1.5 text-sm font-medium group-hover:bg-gray-50"
            >Open</span
          >
        </RouterLink>

        <!-- Demographics / Profile -->
        <RouterLink
          to="/portal/student/profile"
          class="group block rounded-2xl border bg-white p-4 shadow-sm transition hover:shadow"
        >
          <div class="mb-2 flex items-start justify-between">
            <h3 class="text-sm font-semibold">Demographics</h3>
            <span aria-hidden="true">🪪</span>
          </div>
          <p class="mb-3 text-sm text-gray-500">Your profile and contact details.</p>
          <span
            class="inline-flex items-center rounded-lg border px-3 py-1.5 text-sm font-medium group-hover:bg-gray-50"
            >Manage</span
          >
        </RouterLink>
      </div>
    </section>

    <!-- Footer -->
    <footer class="border-t pt-3 text-sm text-gray-500">
      ifitwala_ed
    </footer>
  </div>
</template>
