<template>
	<span v-if="hasInsights" ref="wrapperEl" class="inline-flex">
		<button
			type="button"
			class="inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-jacaranda"
			:class="buttonClass"
			:title="buttonTitle"
			:aria-label="buttonTitle"
			:aria-expanded="open"
			@click.stop="toggle"
		>
			<FeatherIcon name="message-square" class="h-3.5 w-3.5" />
			<span>{{ label }}</span>
			<span v-if="summary && summary.active_count > 1" class="text-[0.68rem] opacity-75">
				{{ summary.active_count }}
			</span>
		</button>
	</span>

	<div
		v-if="open && summary"
		ref="popoverEl"
		:style="popoverStyle"
		class="fixed z-50 w-[min(28rem,calc(100vw-2rem))] rounded-2xl border border-border bg-[rgb(var(--surface-rgb))] p-4 text-sm text-ink shadow-xl ring-1 ring-black/5"
		role="dialog"
		aria-modal="true"
	>
		<div class="mb-3 flex items-start gap-2">
			<span
				class="mt-1 inline-block h-2.5 w-2.5 rounded-full"
				:class="summary.needs_review_count ? 'bg-sand' : 'bg-jacaranda'"
			/>
			<div class="min-w-0">
				<h3 class="text-sm font-semibold text-ink">{{ __('Student notes') }}</h3>
				<p class="mt-0.5 text-xs text-ink/55">
					{{ categoryLine }}
				</p>
			</div>
			<button
				type="button"
				class="ml-auto inline-flex h-7 w-7 items-center justify-center rounded-full text-ink/40 hover:bg-[rgb(var(--surface-strong-rgb))] hover:text-ink"
				:aria-label="__('Close')"
				@click="close"
			>
				<FeatherIcon name="x" class="h-4 w-4" />
			</button>
		</div>

		<div class="space-y-3">
			<article
				v-for="note in visibleNotes"
				:key="note.name"
				class="rounded-xl border border-border/70 bg-[rgb(var(--surface-strong-rgb)/0.45)] p-3"
			>
				<div class="mb-1.5 flex flex-wrap items-center gap-2">
					<span class="text-xs font-semibold uppercase tracking-wide text-ink/45">
						{{ note.category }}
					</span>
					<span
						v-if="note.status === 'Needs Review'"
						class="rounded-full bg-sand/25 px-2 py-0.5 text-xs font-semibold text-clay"
					>
						{{ __('Needs review') }}
					</span>
				</div>
				<p class="whitespace-pre-line leading-relaxed text-ink/78">{{ note.summary }}</p>
				<p class="mt-2 text-xs text-ink/45">
					{{ noteFooter(note) }}
				</p>
			</article>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import { FeatherIcon } from 'frappe-ui';

import { __ } from '@/lib/i18n';
import type { StudentInsightNote, StudentInsightSummary } from '@/types/contracts/studentInsight';

const props = withDefaults(
	defineProps<{
		summary?: StudentInsightSummary | null;
		label?: string | null;
	}>(),
	{
		summary: null,
		label: null,
	}
);

const open = ref(false);
const wrapperEl = ref<HTMLElement | null>(null);
const popoverEl = ref<HTMLElement | null>(null);
const left = ref(0);
const top = ref(0);

const hasInsights = computed(() => Boolean(props.summary && props.summary.active_count > 0));
const label = computed(() => props.label || __('Note'));
const buttonTitle = computed(() => __('Student insight notes'));
const buttonClass = computed(() =>
	props.summary?.needs_review_count
		? 'border-sand/70 bg-sand/20 text-clay hover:bg-sand/30'
		: 'border-jacaranda/25 bg-jacaranda/5 text-jacaranda hover:bg-jacaranda/10'
);
const categoryLine = computed(() => {
	const categories = props.summary?.categories || [];
	if (!categories.length) return __('Current context');
	const shown = categories.slice(0, 3).join(' / ');
	if (categories.length <= 3) return shown;
	return `${shown} +${categories.length - 3}`;
});
const visibleNotes = computed(() => props.summary?.notes?.slice(0, 5) || []);
const popoverStyle = computed(() => ({
	left: `${left.value}px`,
	top: `${top.value}px`,
}));

async function toggle() {
	open.value = !open.value;
	if (!open.value) return;
	await nextTick();
	positionPopover();
}

function close() {
	open.value = false;
}

function positionPopover() {
	if (!open.value || !wrapperEl.value || !popoverEl.value) return;
	const anchor = wrapperEl.value.getBoundingClientRect();
	const popover = popoverEl.value.getBoundingClientRect();
	const margin = 12;
	const gap = 8;
	const vw = window.innerWidth;
	const vh = window.innerHeight;

	let nextLeft = anchor.left + anchor.width / 2 - popover.width / 2;
	nextLeft = Math.max(margin, Math.min(nextLeft, vw - popover.width - margin));

	let nextTop = anchor.bottom + gap;
	if (nextTop + popover.height > vh - margin) {
		nextTop = anchor.top - gap - popover.height;
	}
	if (nextTop < margin) nextTop = margin;

	left.value = Math.round(nextLeft);
	top.value = Math.round(nextTop);
}

function onDocClick(event: MouseEvent) {
	if (!open.value) return;
	const target = event.target;
	if (!(target instanceof Node)) return;
	if (popoverEl.value?.contains(target) || wrapperEl.value?.contains(target)) return;
	close();
}

function onEsc(event: KeyboardEvent) {
	if (event.key === 'Escape') close();
}

function onScrollOrResize() {
	if (open.value) positionPopover();
}

function noteFooter(note: StudentInsightNote) {
	const bits = [];
	if (note.source) bits.push(note.source);
	if (note.review_on) bits.push(__('Review {0}', [note.review_on]));
	return bits.join(' / ');
}

onMounted(() => {
	document.addEventListener('click', onDocClick, true);
	document.addEventListener('keydown', onEsc);
	window.addEventListener('scroll', onScrollOrResize, { passive: true });
	window.addEventListener('resize', onScrollOrResize, { passive: true });
});

onBeforeUnmount(() => {
	document.removeEventListener('click', onDocClick, true);
	document.removeEventListener('keydown', onEsc);
	window.removeEventListener('scroll', onScrollOrResize);
	window.removeEventListener('resize', onScrollOrResize);
});
</script>
