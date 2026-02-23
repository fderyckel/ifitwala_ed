<!-- ifitwala_ed/ui-spa/src/components/class-hub/ClassPulse.vue -->
<!--
  ClassPulse.vue
  A dashboard card displaying "pulse items" or key metrics/alerts for a class.

  Used by:
  - ClassHub.vue
-->
<template>
	<section class="space-y-3">
		<p class="type-overline text-slate-token/70">Class Pulse</p>
		<div class="space-y-2">
			<div
				v-for="item in items"
				:key="item.id"
				class="rounded-xl border border-slate-200 bg-white/90 px-4 py-3 shadow-sm"
			>
				<RouterLink
					v-if="item.route"
					:to="item.route"
					class="type-body-strong text-ink hover:text-jacaranda"
				>
					{{ item.label }}
				</RouterLink>
				<p v-else class="type-body-strong text-ink">
					{{ item.label }}
				</p>
			</div>
			<div
				v-if="!items.length"
				class="rounded-xl border border-dashed border-slate-200 bg-white/80 px-4 py-3"
			>
				<p class="type-caption text-slate-token/70">No pulse items yet.</p>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';
import type { ClassHubBundle } from '@/types/classHub';

defineProps<{
	items: ClassHubBundle['pulse_items'];
}>();
</script>
