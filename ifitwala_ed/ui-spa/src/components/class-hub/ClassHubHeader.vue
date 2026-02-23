<!-- ifitwala_ed/ui-spa/src/components/class-hub/ClassHubHeader.vue -->
<!--
  ClassHubHeader.vue
  Sticky header for the Class Hub page. Displays the current class context (Subject, Grade)
  and session controls (Start/End Class, Quick Evidence).

  Used by:
  - ClassHub.vue (pages/staff)
-->
<template>
	<!--
  ClassHubHeader.vue
  Sticky header for the Class Hub page. Displays the current class context (Subject, Grade)
  and session controls (Start/End Class).

  Used by:
  - ClassHub.vue (pages/staff)
-->
	<header class="space-y-4">
		<div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
			<div class="space-y-2">
				<nav class="type-overline text-slate-token/70">
					<RouterLink :to="{ name: 'staff-home' }" class="hover:text-ink">Staff</RouterLink>
					<span class="mx-2 text-slate-token/40">/</span>
					<span>Class Hub</span>
				</nav>
				<h1 class="type-h1 text-ink">
					{{ header.title }}
				</h1>
			</div>

			<div class="flex flex-wrap items-center gap-2">
				<button
					type="button"
					class="rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-ink shadow-sm transition hover:-translate-y-0.5 hover:border-jacaranda/60"
					@click="$emit('start')"
				>
					{{ session.status === 'active' ? 'Resume Session' : 'Start Session' }}
				</button>
				<button
					type="button"
					class="rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-ink shadow-sm transition hover:-translate-y-0.5 hover:border-jacaranda/60"
					@click="$emit('quick-evidence')"
				>
					Quick Evidence
				</button>
				<button
					type="button"
					class="rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-ink shadow-sm transition hover:-translate-y-0.5 hover:border-jacaranda/60"
					@click="$emit('end')"
				>
					End Session
				</button>
			</div>
		</div>

		<div class="flex flex-wrap items-center gap-3">
			<div
				class="rounded-full border border-slate-200 bg-white/80 px-4 py-2 type-caption text-slate-token/70 shadow-sm"
			>
				<span>{{ now.date_label }}</span>
				<span v-if="now.rotation_day_label" class="mx-2 text-slate-token/40">|</span>
				<span v-if="now.rotation_day_label">{{ now.rotation_day_label }}</span>
				<span v-if="now.block_label" class="mx-2 text-slate-token/40">|</span>
				<span v-if="now.block_label">{{ now.block_label }}</span>
				<span v-if="now.time_range" class="mx-2 text-slate-token/40">|</span>
				<span v-if="now.time_range">{{ now.time_range }}</span>
				<span v-if="now.location" class="mx-2 text-slate-token/40">|</span>
				<span v-if="now.location">{{ now.location }}</span>
			</div>
			<div v-if="session.live_success_criteria" class="type-caption text-slate-token/70">
				Focus: {{ session.live_success_criteria }}
			</div>
		</div>
	</header>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';
import type { ClassHubBundle } from '@/types/classHub';

defineProps<{
	header: ClassHubBundle['header'];
	now: ClassHubBundle['now'];
	session: ClassHubBundle['session'];
}>();

defineEmits<{
	(e: 'start'): void;
	(e: 'quick-evidence'): void;
	(e: 'end'): void;
}>();
</script>
