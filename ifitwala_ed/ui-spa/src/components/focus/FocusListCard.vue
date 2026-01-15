<!-- ifitwala_ed/ui-spa/src/components/focus/FocusListCard.vue -->
 <template>
	<section class="palette-card overflow-hidden">
		<!-- Header -->
		<header class="flex items-center justify-between px-5 py-4 border-b border-line-soft">
			<div class="flex items-center gap-3">
				<h2 class="section-header">
					{{ title }}
				</h2>

				<span
					v-if="count !== undefined"
					class="inline-flex items-center justify-center px-2 py-0.5 rounded-full
					       text-[11px] font-semibold
					       bg-surface-soft text-ink/70 border border-ink/10"
				>
					{{ count }}
				</span>
			</div>

			<!-- Optional header action slot -->
			<div v-if="$slots.action" class="flex items-center">
				<slot name="action" />
			</div>
		</header>

		<!-- Body -->
		<div class="divide-y divide-ink/10">
			<slot />
		</div>

		<!-- Empty state -->
		<div
			v-if="empty"
			class="px-5 py-10 flex items-center justify-center"
		>
			<p class="type-empty text-center">
				Nothing requires your attention right now.
			</p>
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
