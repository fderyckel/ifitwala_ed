<!-- ifitwala_ed/ui-spa/src/components/focus/FocusListItem.vue -->
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
				<p class="type-body-strong text-ink truncate">
					{{ item.title }}
				</p>
				<p class="mt-1 type-caption text-slate-token/70 truncate">
					{{ item.subtitle }}
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
					class="rounded-full bg-slate-100 px-2 py-0.5 type-badge-label text-slate-token/80"
				>
					{{ item.badge }}
				</span>
			</template>

			<FeatherIcon
				name="chevron-right"
				class="h-4 w-4 text-slate-token/40 transition-colors group-hover:text-jacaranda"
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
