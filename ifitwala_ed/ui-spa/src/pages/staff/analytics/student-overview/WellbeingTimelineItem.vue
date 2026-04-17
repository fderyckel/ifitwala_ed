<script setup lang="ts">
import { computed } from 'vue';

import { formatDate } from './formatters';
import type { WellbeingTimelineItem } from './types';

const props = defineProps<{
	item: WellbeingTimelineItem;
	expanded: boolean;
}>();

const emit = defineEmits<{
	(e: 'toggle'): void;
	(e: 'open'): void;
}>();

const canToggle = computed(() =>
	Boolean(props.item.summary && props.item.summary.trim().length > 180)
);

function wellbeingTypeLabel(type: WellbeingTimelineItem['type']) {
	if (type === 'student_log') return 'Student log';
	if (type === 'referral') return 'Referral';
	return 'Nurse visit';
}
</script>

<template>
	<div class="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2">
		<div
			class="mt-1 h-2.5 w-2.5 rounded-full"
			:class="{
				'bg-emerald-500': props.item.type === 'student_log',
				'bg-amber-500': props.item.type === 'referral',
				'bg-sky-500': props.item.type === 'nurse_visit',
			}"
		></div>
		<div class="min-w-0 flex-1 text-sm text-slate-700">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0 font-semibold text-slate-900">{{ props.item.title }}</div>
				<span class="text-[11px] text-slate-500">{{ formatDate(props.item.date) }}</span>
			</div>
			<p
				v-if="props.item.summary"
				:class="[
					'mt-1 break-words text-xs leading-relaxed text-slate-500',
					props.expanded ? 'whitespace-pre-wrap' : 'line-clamp-2',
				]"
			>
				{{ props.item.summary }}
			</p>
			<div class="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
				<span class="rounded-full bg-white px-2 py-0.5 shadow-sm">
					{{ wellbeingTypeLabel(props.item.type) }}
				</span>
				<span v-if="props.item.status" class="rounded-full bg-white px-2 py-0.5 shadow-sm">
					{{ props.item.status }}
				</span>
				<button
					v-if="canToggle"
					type="button"
					class="rounded-full bg-white px-2 py-0.5 shadow-sm"
					@click="emit('toggle')"
				>
					{{ props.expanded ? 'Show less' : 'Read more' }}
				</button>
				<button
					type="button"
					class="rounded-full bg-white px-2 py-0.5 shadow-sm"
					@click="emit('open')"
				>
					Open
				</button>
			</div>
		</div>
	</div>
</template>
