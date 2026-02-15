<!-- ifitwala_ed/ui-spa/src/components/activity/ActivityStatusBadge.vue -->
<template>
	<span class="inline-flex items-center rounded-full px-2.5 py-1 type-badge-label" :class="badgeClass">
		{{ label }}
	</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
	status: string
	label: string
}>()

const badgeClass = computed(() => {
	const status = (props.status || '').toLowerCase()
	if (status === 'confirmed' || status === 'booked') {
		return 'bg-[rgb(var(--leaf-rgb)/0.15)] text-canopy ring-1 ring-[rgb(var(--leaf-rgb)/0.35)]'
	}
	if (status === 'offered') {
		return 'bg-[rgb(var(--jacaranda-rgb)/0.14)] text-jacaranda ring-1 ring-[rgb(var(--jacaranda-rgb)/0.35)]'
	}
	if (status === 'waitlisted') {
		return 'bg-[rgb(var(--sky-rgb)/0.2)] text-ink/80 ring-1 ring-[rgb(var(--sky-rgb)/0.35)]'
	}
	if (status === 'cancelled' || status === 'expired' || status === 'rejected') {
		return 'bg-[rgb(var(--flame-rgb)/0.12)] text-flame ring-1 ring-[rgb(var(--flame-rgb)/0.3)]'
	}
	return 'bg-surface-soft text-ink/75 ring-1 ring-[rgb(var(--border-rgb)/0.8)]'
})
</script>
