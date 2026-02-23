<!-- ifitwala_ed/ui-spa/src/components/class-hub/MyTeachingPanel.vue -->
<!--
  MyTeachingPanel.vue
  Sidebar or panel in Class Hub showing the teacher's schedule/timetable, notes, and queued tasks
  for quick navigation.

  Used by:
  - ClassHub.vue (pages/staff)
-->
<template>
	<!--
  MyTeachingPanel.vue
  Sidebar or panel in Class Hub showing the teacher's schedule/timetable, notes, and queued tasks
  for quick navigation.

  Used by:
  - ClassHub.vue (pages/staff)
-->
	<section class="grid grid-cols-1 gap-4 lg:grid-cols-2">
		<div class="card-surface p-4 space-y-3">
			<div class="flex items-center justify-between">
				<p class="type-overline text-slate-token/70">Notes & Observations</p>
				<button
					type="button"
					class="type-button-label text-jacaranda hover:text-canopy"
					@click="$emit('add-note')"
				>
					Add note
				</button>
			</div>
			<div class="space-y-2">
				<button
					v-for="note in notes"
					:key="note.id"
					type="button"
					class="w-full rounded-xl border border-slate-200 bg-white/90 px-3 py-3 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-jacaranda/60"
					@click="$emit('open-note', note)"
				>
					<p class="type-body-strong text-ink">{{ note.student_name }}</p>
					<p class="type-caption text-slate-token/70">{{ note.preview }}</p>
					<p class="type-caption text-slate-token/50">{{ note.created_at_label }}</p>
				</button>
				<div
					v-if="!notes.length"
					class="rounded-xl border border-dashed border-slate-200 bg-white/80 px-3 py-3"
				>
					<p class="type-caption text-slate-token/70">No notes yet for this session.</p>
				</div>
			</div>
		</div>

		<div class="card-surface p-4 space-y-3">
			<div class="flex items-center justify-between">
				<p class="type-overline text-slate-token/70">Tasks & Evidence</p>
			</div>
			<div class="space-y-2">
				<button
					v-for="task in tasks"
					:key="task.id"
					type="button"
					class="w-full rounded-xl border border-slate-200 bg-white/90 px-3 py-3 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-jacaranda/60"
					@click="$emit('open-task', task)"
				>
					<p class="type-body-strong text-ink">{{ task.title }}</p>
					<p class="type-caption text-slate-token/70">{{ task.status_label }}</p>
				</button>
				<div
					v-if="!tasks.length"
					class="rounded-xl border border-dashed border-slate-200 bg-white/80 px-3 py-3"
				>
					<p class="type-caption text-slate-token/70">No tasks waiting.</p>
				</div>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { ClassHubBundle } from '@/types/classHub';

defineProps<{
	notes: ClassHubBundle['notes_preview'];
	tasks: ClassHubBundle['task_items'];
}>();

defineEmits<{
	(e: 'add-note'): void;
	(e: 'open-note', note: ClassHubBundle['notes_preview'][number]): void;
	(e: 'open-task', task: ClassHubBundle['task_items'][number]): void;
}>();
</script>
