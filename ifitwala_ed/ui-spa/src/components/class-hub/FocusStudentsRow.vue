<!-- ifitwala_ed/ui-spa/src/components/class-hub/FocusStudentsRow.vue -->
<!--
  FocusStudentsRow.vue
  Displays a row of chips representing students currently marked for focus/attention.

  Used by:
  - ClassHub.vue
-->
<template>
  <section class="space-y-3">
    <p class="type-overline text-slate-token/70">Students in Focus</p>
    <div class="flex flex-wrap gap-2">
      <button
        v-for="student in students"
        :key="student.student"
        type="button"
        class="chip"
        @click="$emit('open', student)"
      >
        <span class="type-caption text-ink">{{ student.student_name }}</span>
      </button>
      <span v-if="!students.length" class="type-caption text-slate-token/60">No focus students yet.</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ClassHubBundle } from '@/types/classHub'

defineProps<{
  students: ClassHubBundle['focus_students']
}>()

defineEmits<{
  (e: 'open', student: ClassHubBundle['focus_students'][number]): void
}>()
</script>
