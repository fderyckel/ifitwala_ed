<!-- ifitwala_ed/ui-spa/src/components/focus/FocusListItem.vue -->
<!--
  FocusListItem.vue
  Row component for FocusListCard. Displays a single actionable item with logic for "kind" (Review vs Action).

  Used by:
  - FocusListCard.vue (components/focus)
  - FocusRouterOverlay.vue (overlays/focus)
-->
<template>
	<button
		type="button"
		class="if-list-row group"
		:class="{
			'if-list-row--disabled': disabled,
		}"
		:disabled="disabled"
		@click="onClick"
	>
		<!-- Left: status dot -->
		<div class="if-list-row__dot" aria-hidden="true">
			<span class="if-list-row__dot-inner" :class="dotClass" />
		</div>

		<!-- Middle: title + subtitle OR skeleton -->
		<div class="min-w-0 flex-1">
			<template v-if="loading">
				<div class="if-skel if-skel--title" />
				<div class="mt-2 if-skel if-skel--sub" />
			</template>

			<template v-else>
				<p class="type-body-strong text-ink leading-snug line-clamp-2">
					{{ item.title }}
				</p>

				<p class="mt-1 type-caption text-ink/70 leading-snug line-clamp-2">
					{{ item.subtitle }}
				</p>
				<p
					v-if="assignedByName"
					class="mt-1 type-caption text-ink/60 leading-snug truncate"
				>
					Assigned by {{ assignedByName }}
				</p>
			</template>
		</div>

		<!-- Right: badge + chevron -->
		<div class="if-list-row__right">
			<template v-if="loading">
				<div class="if-skel if-skel--badge" />
			</template>

			<template v-else>
				<span
					v-if="item.badge"
					class="if-pill type-badge-label border-ink/10 bg-surface-soft"
				>
					{{ item.badge }}
				</span>
			</template>

			<FeatherIcon
				name="chevron-right"
				class="h-4 w-4 text-ink/40 transition-colors group-hover:text-jacaranda"
				aria-hidden="true"
			/>
		</div>
	</button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import type { FocusItem } from '@/types/focusItem'

const props = defineProps<{
	item: FocusItem
	loading?: boolean
	disabled?: boolean
}>()

const assignedByName = computed(() => {
	const p = props.item.payload
	const name = (p?.assigned_by_name || '').trim()
	return name || null
})

const emit = defineEmits<{
	(e: 'open', item: FocusItem): void
}>()

const dotClass = computed(() => {
	if (props.loading) return 'if-dot--muted'
	return props.item.kind === 'review' ? 'if-dot--review' : 'if-dot--action'
})

function onClick() {
	if (props.loading || props.disabled) return
	emit('open', props.item)
}
</script>
