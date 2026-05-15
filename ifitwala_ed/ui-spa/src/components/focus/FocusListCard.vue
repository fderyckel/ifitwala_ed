<!-- ifitwala_ed/ui-spa/src/components/focus/FocusListCard.vue -->
<!--
  FocusListCard.vue
  A dashboard card component that displays a summary or list of active Focus items (ToDos).

  Used by:
  - StaffHome.vue (pages/staff)
  - Focus page (if exists)
-->
<template>
	<section class="palette-card overflow-hidden">
		<!-- Header -->
		<header class="flex items-center justify-between px-5 py-4 border-b border-line-soft">
			<div class="min-w-0 flex items-center gap-3">
				<h2 class="section-header truncate">
					{{ titleText }}
				</h2>

				<span
					v-if="showCount"
					class="inline-flex items-center justify-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-surface-soft text-ink/70 border border-ink/10"
				>
					{{ countValue }}
				</span>

				<span v-if="metaText" class="type-caption text-ink/60 truncate">
					{{ metaText }}
				</span>
			</div>

			<!-- Optional header action slot -->
			<div v-if="$slots.action" class="flex items-center gap-2 shrink-0">
				<slot name="action" />
			</div>
		</header>

		<!-- Empty state -->
		<div v-if="isEmpty" class="px-5 py-10">
			<div class="card-surface p-5">
				<p class="type-empty">
					{{ emptyText }}
				</p>
			</div>
		</div>

		<!-- Body -->
		<div v-else class="divide-y divide-ink/10">
			<!-- Loading skeletons -->
			<template v-if="loading">
				<FocusListItem
					v-for="n in skeletonCountValue"
					:key="`sk_${n}`"
					:item="skeletonItem"
					:loading="true"
					:disabled="true"
				/>
			</template>

			<!-- Items -->
			<template v-else>
				<FocusListItem v-for="it in displayed" :key="keyFor(it)" :item="it" @open="emitOpen" />
			</template>
		</div>

		<!-- Optional footer slot -->
		<div v-if="$slots.footer" class="px-5 py-4 border-t border-line-soft">
			<slot name="footer" />
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import FocusListItem from './FocusListItem.vue';
import type { FocusItem } from '@/types/focusItem';

const props = defineProps<{
	items: FocusItem[];
	loading?: boolean;
	title?: string;
	meta?: string | null;
	emptyText?: string;
	maxItems?: number;
	skeletonCount?: number;
	/**
	 * If provided, overrides badge count display.
	 * If undefined, count defaults to items.length.
	 */
	count?: number;
}>();

const emit = defineEmits<{
	(e: 'open', item: FocusItem): void;
}>();

/* Normalized props ------------------------------------------------ */
const loading = computed(() => !!props.loading);
const safeItems = computed<FocusItem[]>(() => (Array.isArray(props.items) ? props.items : []));

const titleText = computed(() =>
	props.title && String(props.title).trim() ? props.title : 'Your Focus'
);
const metaText = computed(() => (props.meta && String(props.meta).trim() ? props.meta : null));
const emptyText = computed(() =>
	props.emptyText && String(props.emptyText).trim() ? props.emptyText : 'Nothing urgent right now.'
);

const maxItemsValue = computed(() => {
	const n = Number(props.maxItems ?? 8);
	return Number.isFinite(n) ? Math.min(Math.max(Math.floor(n), 1), 50) : 8;
});

const skeletonCountValue = computed(() => {
	const n = Number(props.skeletonCount ?? 6);
	return Number.isFinite(n) ? Math.min(Math.max(Math.floor(n), 1), 12) : 6;
});

const displayed = computed(() => safeItems.value.slice(0, maxItemsValue.value));

/* Badge count ----------------------------------------------------- */
const countValue = computed(() => {
	if (typeof props.count === 'number' && Number.isFinite(props.count)) return props.count;
	return safeItems.value.length;
});

const showCount = computed(() => typeof countValue.value === 'number');

/* Empty logic ----------------------------------------------------- */
const isEmpty = computed(() => !loading.value && safeItems.value.length === 0);

/* Skeleton item --------------------------------------------------- */
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
};

/* Emit ------------------------------------------------------------ */
function emitOpen(item: FocusItem) {
	emit('open', item);
}

/**
 * Defensive keying:
 * - Prefer stable server id.
 * - Fallback to reference tuple if id missing (shouldn’t happen, but prevents silent empty list).
 */
function keyFor(it: FocusItem) {
	const id = (it as any)?.id;
	if (typeof id === 'string' && id.trim()) return id;
	const a = String((it as any)?.action_type ?? '');
	const d = String((it as any)?.reference_doctype ?? '');
	const n = String((it as any)?.reference_name ?? '');
	return `${a}::${d}::${n}`;
}
</script>
