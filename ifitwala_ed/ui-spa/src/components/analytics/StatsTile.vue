<!-- ifitwala_ed/ui-spa/src/components/analytics/StatsTile.vue -->
<!--
  StatsTile.vue
  Small, pill-shaped indicator for a single metric/status with a colored dot.
  Used for dense displays of status counts.

  Used by:
  - StudentLogAnalytics.vue
  - RoomUtilization.vue
  - InquiryAnalytics.vue
  (all in pages/staff/analytics)
-->
<template>
	<div :class="containerClass">
		<span :class="dotClass"></span>
		<span class="font-medium">{{ value }}</span>
		<span class="text-slate-500">{{ label }}</span>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
	label: string;
	value: number | string;
	tone?: 'default' | 'warning' | 'success' | 'info';
}>();

const tone = computed(() => props.tone ?? 'default');

const containerClass = computed(() => {
	return [
		'inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs shadow-sm bg-white',
		'border-slate-200',
	];
});

const dotClass = computed(() => {
	const base = 'h-2 w-2 rounded-full';
	switch (tone.value) {
		case 'warning':
			return base + ' bg-amber-500';
		case 'success':
			return base + ' bg-emerald-500';
		case 'info':
			return base + ' bg-sky-500';
		default:
			return base + ' bg-slate-400';
	}
});
</script>
