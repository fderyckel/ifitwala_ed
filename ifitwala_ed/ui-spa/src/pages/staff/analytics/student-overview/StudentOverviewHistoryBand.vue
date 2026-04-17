<script setup lang="ts">
import { computed, ref } from 'vue';

import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue';

import { academicYearScopeLabel, matchesAcademicYearScope } from './academicYearScope';
import type { HistoryScope, Snapshot, ViewMode } from './types';

const props = defineProps<{
	snapshot: Snapshot;
	displayViewMode: ViewMode;
}>();

const historyScope = ref<HistoryScope>('all');

const displayHistoryYearOptions = computed(() =>
	(props.snapshot.history.year_options || []).map(option => ({
		...option,
		displayLabel: academicYearScopeLabel(option.key, option.label),
	}))
);

const filteredAcademicTrend = computed(() => {
	const data = props.snapshot.history.academic_trend || [];
	return data.filter(row =>
		matchesAcademicYearScope(row.academic_year, historyScope.value, {
			currentAcademicYear: props.snapshot.meta.current_academic_year,
			yearOptions: props.snapshot.history.year_options || [],
		})
	);
});

const filteredAttendanceTrend = computed(() => {
	const data = props.snapshot.history.attendance_trend || [];
	return data.filter(row =>
		matchesAcademicYearScope(row.academic_year, historyScope.value, {
			currentAcademicYear: props.snapshot.meta.current_academic_year,
			yearOptions: props.snapshot.history.year_options || [],
		})
	);
});

const academicTrendOption = computed(() => {
	if (!filteredAcademicTrend.value.length) return {};
	return {
		grid: { left: 40, right: 10, top: 10, bottom: 40 },
		tooltip: { trigger: 'axis' },
		legend: { top: 0, data: ['Overall', 'Task completion'] },
		xAxis: { type: 'category', data: filteredAcademicTrend.value.map(item => item.label) },
		yAxis: { type: 'value', min: 0 },
		series: [
			{
				name: 'Overall',
				type: 'line',
				smooth: true,
				data: filteredAcademicTrend.value.map(item => item.overall_grade_value ?? null),
			},
			{
				name: 'Task completion',
				type: 'line',
				smooth: true,
				data: filteredAcademicTrend.value.map(item =>
					item.task_completion_rate != null ? Math.round(item.task_completion_rate * 100) : null
				),
			},
		],
	};
});

const attendanceTrendOption = computed(() => {
	if (!filteredAttendanceTrend.value.length) return {};
	return {
		grid: { left: 40, right: 10, top: 10, bottom: 40 },
		tooltip: { trigger: 'axis' },
		legend: { top: 0, data: ['Attendance %', 'Unexcused absences'] },
		xAxis: { type: 'category', data: filteredAttendanceTrend.value.map(item => item.label) },
		yAxis: { type: 'value' },
		series: [
			{
				name: 'Attendance %',
				type: 'line',
				smooth: true,
				data: filteredAttendanceTrend.value.map(item =>
					item.present_percentage != null ? Math.round(item.present_percentage * 100) : null
				),
			},
			{
				name: 'Unexcused absences',
				type: 'bar',
				data: filteredAttendanceTrend.value.map(item => item.unexcused_absences || 0),
			},
		],
	};
});

const reflectionFlags = computed(() => {
	const flags = props.snapshot.history.reflection_flags || [];
	return flags.map(flag => ({
		...flag,
		message:
			props.displayViewMode === 'student' || props.displayViewMode === 'guardian'
				? flag.message_student || flag.message_staff
				: flag.message_staff || flag.message_student,
	}));
});
</script>

<template>
	<section class="card-surface px-4 py-4">
		<header class="mb-3 flex flex-wrap items-center justify-between gap-3">
			<div>
				<h3 class="text-sm font-semibold text-slate-800">History & Reflection</h3>
				<p class="text-[11px] text-slate-500">Compare years and surface narrative cues.</p>
			</div>
			<div class="flex flex-wrap gap-2">
				<button
					v-for="opt in displayHistoryYearOptions"
					:key="opt.key"
					type="button"
					:class="[
						'rounded-full px-3 py-1 text-[11px] font-semibold',
						historyScope === opt.key ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600',
					]"
					@click="historyScope = opt.key as HistoryScope"
				>
					{{ opt.displayLabel }}
				</button>
			</div>
		</header>
		<div class="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,2fr)_minmax(0,2fr)]">
			<div class="rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-3">
				<h4 class="text-xs font-semibold uppercase tracking-wide text-slate-600">
					Academic & task trend
				</h4>
				<AnalyticsChart v-if="filteredAcademicTrend.length" :option="academicTrendOption" />
				<p v-else class="text-xs text-slate-400">No academic history.</p>
			</div>
			<div class="rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-3">
				<h4 class="text-xs font-semibold uppercase tracking-wide text-slate-600">
					Attendance trend
				</h4>
				<AnalyticsChart v-if="filteredAttendanceTrend.length" :option="attendanceTrendOption" />
				<p v-else class="text-xs text-slate-400">No attendance history.</p>
			</div>
			<div class="rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-3">
				<h4 class="text-xs font-semibold uppercase tracking-wide text-slate-600">Reflection</h4>
				<ul class="space-y-2 text-xs text-slate-700">
					<li
						v-for="flag in reflectionFlags"
						:key="flag.id"
						class="rounded-lg bg-white px-3 py-2 shadow-sm"
					>
						<p class="font-semibold text-slate-900">{{ flag.message }}</p>
						<p class="text-[11px] text-slate-500">{{ flag.category }}</p>
					</li>
				</ul>
				<p v-if="!reflectionFlags.length" class="text-xs text-slate-400">No reflection prompts.</p>
			</div>
		</div>
	</section>
</template>
