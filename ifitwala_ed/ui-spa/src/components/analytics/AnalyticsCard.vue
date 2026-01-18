<!-- ui-spa/src/components/analytics/AnalyticsCard.vue -->
<template>
	<div
		class="analytics-card"
		:class="[
			dense ? 'analytics-card--dense' : '',
			interactive ? 'analytics-card--interactive' : '',
		]"
		@click="handleExpand"
	>
		<div class="flex items-start justify-between gap-3">
			<div class="min-w-0">
				<div class="analytics-card__title">
					{{ title }}
				</div>
				<div v-if="$slots.subtitle" class="analytics-card__meta mt-1">
					<slot name="subtitle" />
				</div>
			</div>

			<div v-if="$slots.badge" class="shrink-0">
				<slot name="badge" />
			</div>
		</div>

		<div class="min-h-0">
			<slot name="body" />
		</div>
	</div>
</template>

<script setup lang="ts">
const props = withDefaults(
	defineProps<{
		title: string
		interactive?: boolean
		dense?: boolean
	}>(),
	{
		interactive: true,
	}
)

const emit = defineEmits<{
	(e: 'expand'): void
}>()

function handleExpand() {
	if (!props.interactive) return
	emit('expand')
}
</script>
