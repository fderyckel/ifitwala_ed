<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue';

import { matchesAcademicYearScope } from './academicYearScope';
import { formatCount, formatDate } from './formatters';
import type {
	PermissionFlags,
	Snapshot,
	WellbeingFilter,
	WellbeingScope,
	WellbeingTimelineItem,
} from './types';
import WellbeingTimelineItemCard from './WellbeingTimelineItem.vue';

const WELLBEING_VISIBLE_TIMELINE_ROWS = 10;

const props = defineProps<{
	snapshot: Snapshot;
	permissions: PermissionFlags;
}>();

const wellbeingScope = ref<WellbeingScope>('current');
const wellbeingFilter = ref<WellbeingFilter>('all');
const expandedItems = ref<Record<string, boolean>>({});

watch(
	() => [props.permissions.can_view_referrals, props.permissions.can_view_nurse_details],
	([canViewReferrals, canViewNurse]) => {
		if (wellbeingFilter.value === 'referral' && !canViewReferrals) {
			wellbeingFilter.value = 'all';
		}
		if (wellbeingFilter.value === 'nurse_visit' && !canViewNurse) {
			wellbeingFilter.value = 'all';
		}
	},
	{ immediate: true }
);

watch([wellbeingFilter, wellbeingScope], () => {
	expandedItems.value = {};
});

watch(
	() => props.snapshot.meta.student,
	() => {
		expandedItems.value = {};
	}
);

const wellbeingTimeline = computed(() => {
	const events = props.snapshot.wellbeing.timeline || [];
	return events.filter(item => {
		const scopeMatch = matchesAcademicYearScope(item.academic_year, wellbeingScope.value, {
			currentAcademicYear: props.snapshot.meta.current_academic_year,
			yearOptions: props.snapshot.history.year_options || [],
		});
		const typeMatch = wellbeingFilter.value === 'all' ? true : item.type === wellbeingFilter.value;
		return scopeMatch && typeMatch;
	});
});

const wellbeingTimelineLead = computed(() =>
	wellbeingTimeline.value.slice(0, WELLBEING_VISIBLE_TIMELINE_ROWS)
);

const wellbeingTimelineOverflow = computed(() =>
	wellbeingTimeline.value.slice(WELLBEING_VISIBLE_TIMELINE_ROWS)
);

const wellbeingHealthNote = computed(() => {
	const note = props.snapshot.wellbeing.health_note || null;
	if (!note) return null;
	return wellbeingFilter.value === 'all' || wellbeingFilter.value === 'nurse_visit' ? note : null;
});

const wellbeingTimelineNeedsScroll = computed(() => wellbeingTimelineOverflow.value.length > 0);

const wellbeingSeriesOption = computed(() => {
	const series = props.snapshot.wellbeing.metrics.time_series || [];
	if (!series.length) return {};
	const labels = series.map(item => item.period);
	return {
		grid: { left: 40, right: 10, top: 10, bottom: 40 },
		tooltip: { trigger: 'axis' },
		legend: { top: 0, data: ['Logs', 'Referrals', 'Nurse visits'] },
		xAxis: { type: 'category', data: labels },
		yAxis: { type: 'value' },
		series: [
			{
				name: 'Logs',
				type: 'bar',
				stack: 'total',
				data: series.map(item => item.student_logs || 0),
			},
			{
				name: 'Referrals',
				type: 'bar',
				stack: 'total',
				data: series.map(item => item.referrals || 0),
			},
			{
				name: 'Nurse visits',
				type: 'bar',
				stack: 'total',
				data: series.map(item => item.nurse_visits || 0),
			},
		],
	};
});

function wellbeingItemKey(item: WellbeingTimelineItem) {
	return `${item.type}:${item.name}`;
}

function isExpanded(item: WellbeingTimelineItem) {
	return Boolean(expandedItems.value[wellbeingItemKey(item)]);
}

function toggleExpanded(item: WellbeingTimelineItem) {
	const key = wellbeingItemKey(item);
	expandedItems.value = {
		...expandedItems.value,
		[key]: !expandedItems.value[key],
	};
}

function deskRouteSlug(doctype: string) {
	return String(doctype || '')
		.trim()
		.toLowerCase()
		.replace(/\s+/g, '-');
}

function openDeskDoc(doctype?: string | null, name?: string | null) {
	const safeDoctype = String(doctype || '').trim();
	const safeName = String(name || '').trim();
	if (!safeDoctype || !safeName || typeof window === 'undefined') return;
	window.open(
		`/desk/${encodeURIComponent(deskRouteSlug(safeDoctype))}/${encodeURIComponent(safeName)}`,
		'_blank',
		'noopener'
	);
}
</script>

<template>
	<section
		class="grid grid-cols-1 gap-6 lg:items-start lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]"
	>
		<div
			class="rounded-2xl border border-slate-200 bg-[rgb(var(--surface-rgb)/0.92)] px-4 py-4 shadow-sm"
		>
			<header class="mb-3 flex flex-wrap items-center justify-between gap-3">
				<div>
					<h3 class="text-sm font-semibold text-slate-800">Wellbeing timeline</h3>
					<p class="text-[11px] text-slate-500">
						Logs, referrals, nurse visits, and the staff health note.
					</p>
				</div>
				<div class="flex items-center gap-2">
					<select
						v-model="wellbeingFilter"
						class="h-8 rounded-md border border-slate-200 px-2 text-[11px]"
					>
						<option value="all">All</option>
						<option value="student_log">Logs</option>
						<option v-if="props.permissions.can_view_referrals" value="referral">Referrals</option>
						<option v-if="props.permissions.can_view_nurse_details" value="nurse_visit">
							Nurse
						</option>
					</select>
					<select
						v-model="wellbeingScope"
						class="h-8 rounded-md border border-slate-200 px-2 text-[11px]"
					>
						<option value="current">This academic year</option>
						<option value="last">Last academic year</option>
						<option value="all">All academic years</option>
					</select>
				</div>
			</header>
			<div>
				<div
					v-if="wellbeingHealthNote"
					class="mb-3 rounded-xl border border-sky-200 bg-sky-50/70 px-3 py-3"
				>
					<div class="flex items-start justify-between gap-3">
						<div class="min-w-0 flex-1">
							<div class="flex flex-wrap items-center gap-2">
								<h4 class="text-sm font-semibold text-slate-900">
									{{ wellbeingHealthNote.title }}
								</h4>
								<span
									class="rounded-full bg-white px-2 py-0.5 text-[11px] text-slate-500 shadow-sm"
								>
									Student Patient
								</span>
								<span v-if="wellbeingHealthNote.updated_on" class="text-[11px] text-slate-500">
									Updated {{ formatDate(wellbeingHealthNote.updated_on) }}
								</span>
							</div>
							<p class="mt-1 text-xs text-slate-600">
								{{ wellbeingHealthNote.summary }}
							</p>
						</div>
						<button
							type="button"
							class="rounded-full bg-white px-3 py-1 text-[11px] text-slate-600 shadow-sm"
							@click="openDeskDoc(wellbeingHealthNote.doctype, wellbeingHealthNote.name)"
						>
							Open
						</button>
					</div>
				</div>
				<p v-if="wellbeingTimelineNeedsScroll" class="mb-2 text-[11px] text-slate-500">
					Showing the latest 10 items first. Scroll below for older wellbeing activity in this
					dashboard view.
				</p>
				<div class="space-y-3">
					<WellbeingTimelineItemCard
						v-for="item in wellbeingTimelineLead"
						:key="wellbeingItemKey(item)"
						:item="item"
						:expanded="isExpanded(item)"
						@toggle="toggleExpanded(item)"
						@open="openDeskDoc(item.doctype, item.name)"
					/>
					<div
						v-if="wellbeingTimelineOverflow.length"
						class="max-h-[26rem] space-y-3 overflow-y-auto pr-1"
					>
						<WellbeingTimelineItemCard
							v-for="item in wellbeingTimelineOverflow"
							:key="`overflow-${wellbeingItemKey(item)}`"
							:item="item"
							:expanded="isExpanded(item)"
							@toggle="toggleExpanded(item)"
							@open="openDeskDoc(item.doctype, item.name)"
						/>
					</div>
					<div
						v-if="!wellbeingTimelineLead.length && !wellbeingHealthNote"
						class="text-xs text-slate-400"
					>
						No wellbeing items for this scope.
					</div>
				</div>
			</div>
		</div>

		<div
			class="self-start rounded-2xl border border-slate-200 bg-[rgb(var(--surface-rgb)/0.92)] px-4 py-4 shadow-sm"
		>
			<header class="mb-3 flex items-center justify-between">
				<h3 class="text-sm font-semibold text-slate-800">Support metrics & patterns</h3>
			</header>
			<AnalyticsChart
				v-if="props.snapshot.wellbeing.metrics.time_series?.length"
				:option="wellbeingSeriesOption"
			/>
			<div v-else class="text-xs text-slate-400">No trend data yet.</div>
			<div class="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-600 lg:grid-cols-3">
				<div class="min-w-0 rounded-lg bg-slate-50/70 px-3 py-2">
					<p class="text-[11px] uppercase tracking-wide text-slate-500">Open log follow-ups</p>
					<p class="text-base font-semibold text-slate-900">
						{{ formatCount(props.snapshot.wellbeing.metrics.student_logs?.open_followups || 0) }}
					</p>
				</div>
				<div class="min-w-0 rounded-lg bg-slate-50/70 px-3 py-2">
					<p class="text-[11px] uppercase tracking-wide text-slate-500">Active referrals</p>
					<p class="text-base font-semibold text-amber-600">
						{{ formatCount(props.snapshot.wellbeing.metrics.referrals?.active || 0) }}
					</p>
				</div>
				<div class="min-w-0 rounded-lg bg-slate-50/70 px-3 py-2">
					<p class="text-[11px] uppercase tracking-wide text-slate-500">Visible nurse visits</p>
					<p class="text-base font-semibold text-slate-900">
						{{ formatCount(props.snapshot.wellbeing.metrics.nurse_visits?.this_term || 0) }}
					</p>
				</div>
			</div>
		</div>
	</section>
</template>
