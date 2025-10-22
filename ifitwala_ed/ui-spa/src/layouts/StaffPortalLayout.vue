<template>
  <div class="min-h-screen bg-slate-50 flex flex-col">
    <header class="bg-white border-b border-slate-200">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        <RouterLink
          :to="{ name: 'staff-student-groups' }"
          class="text-lg font-semibold text-slate-900 tracking-tight"
        >
          Staff Portal
        </RouterLink>

        <nav class="flex items-center gap-4 text-sm font-medium text-slate-600">
          <RouterLink
            :to="{ name: 'staff-student-groups' }"
            class="transition hover:text-blue-600"
          >
            Student Groups
          </RouterLink>
          <RouterLink
            :to="{ name: 'student-home' }"
            class="transition hover:text-blue-600"
          >
            Switch to Student View
          </RouterLink>
        </nav>
      </div>
    </header>

    <main class="mx-auto flex w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
      <slot />
    </main>

    <footer class="border-t border-slate-200 bg-white">
      <div class="mx-auto max-w-6xl px-4 py-4 text-xs text-slate-500 sm:px-6 lg:px-8">
        © {{ year }} Ifitwala Staff Portal
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const year = computed(() => new Date().getFullYear())
</script>
