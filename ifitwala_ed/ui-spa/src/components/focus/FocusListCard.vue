<!-- ifitwala_ed/ui-spa/src/components/focus/FocusListCard.vue -->
<template>
	<section class="space-y-3">
		<!-- Header -->
		<div class="flex items-center justify-between px-1">
			<h3 class="flex items-center gap-2 type-h3 text-canopy">
				<FeatherIcon name="list" class="h-4 w-4 opacity-70" />
				{{ title }}
			</h3>
			<span v-if="meta" class="type-overline">
				{{ meta }}
			</span>
		</div>

		<!-- Card -->
		<div class="palette-card overflow-hidden">
			<template v-if="loading">
				<FocusListItem
					v-for="n in skeletonCount"
					:key="`sk_${n}`"
					:loading="true"
					:disabled="true"
					:item="skeletonItem"
				/>
			</template>

			<template v-else-if="!safeItems.length">
				<div class="px-6 py-6 bg-white">
					<p class="type-body text-slate-token/75">
						{{ emptyText }}
					</p>
				</div>
			</template>

			<template v-else>
				<FocusListItem
					v-for="item in displayed"
					:key="item.id"
					:item="item"
					@open="emitOpen"
				/>
			</template>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import FocusListItem from './FocusListItem.vue'
import type { FocusItem } from '@/types/focusItem'

const props = defineProps<{
	items: FocusItem[]
	loading?: boolean
	title?: string
	meta?: string | null
	emptyText?: string
	maxItems?: number
	skeletonCount?: number
}>()

const emit = defineEmits<{
	(e: 'open', item: FocusItem): void
}>()

const title = computed(() => props.title ?? 'Your Focus')
const emptyText = computed(() => props.emptyText ?? 'Nothing urgent right now.')
const maxItems = computed(() => props.maxItems ?? 8)
const skeletonCount = computed(() => props.skeletonCount ?? 6)

const safeItems = computed(() => (Array.isArray(props.items) ? props.items : []))
const displayed = computed(() => safeItems.value.slice(0, maxItems.value))

const skeletonItem: FocusItem = {
	id: 'sk',
	kind: 'action',
	title: 'Loading',
	subtitle: 'Loading',
	badge: null,
	priority: null,
	due_date: null,
	action_type: 'loading',
	reference_doctype: 'Loading',
	reference_name: 'Loading',
	payload: null,
	permissions: { can_open: false },
}

function emitOpen(item: FocusItem) {
	emit('open', item)
}
</script>
