<!-- ifitwala_ed/ui-spa/src/components/class-hub/StudentsGrid.vue -->
<!--
  StudentsGrid.vue
  The main grid view in Class Hub displaying student cards with status indicators (attendance, behavior).
  Each card shows the student's name, evidence count, and signal status.

  Used by:
  - ClassHub.vue (pages/staff)
-->
<template>
<!--
  StudentsGrid.vue
  The main grid view in Class Hub displaying student cards with status indicators (attendance, behavior).

  Used by:
  - ClassHub.vue (pages/staff)
-->
  <section class="space-y-3">
    <p class="type-overline text-slate-token/70">Student Grid</p>
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <button
        v-for="student in students"
        :key="student.student"
        type="button"
        class="card-surface flex h-32 flex-col justify-between p-4 text-left transition hover:-translate-y-0.5 hover:border-jacaranda/60"
        @click="$emit('open', student)"
      >
        <div class="space-y-1">
          <p class="type-body-strong text-ink truncate">{{ student.student_name }}</p>
          <p class="type-caption text-slate-token/70">
            Evidence today: {{ student.evidence_count_today }}
          </p>
        </div>
        <div class="flex items-center justify-between">
          <p class="type-caption text-slate-token/70">
            Signal: {{ student.signal || 'n/a' }}
          </p>
          <span
            v-if="student.has_note_today"
            class="h-2 w-2 rounded-full bg-canopy"
            aria-label="Has note"
          ></span>
        </div>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ClassHubBundle } from '@/types/classHub'

defineProps<{
  students: ClassHubBundle['students']
}>()

defineEmits<{
  (e: 'open', student: ClassHubBundle['students'][number]): void
}>()
</script>
