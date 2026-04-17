<script setup lang="ts">
import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue';
import StackedBarChart from '@/components/analytics/StackedBarChart.vue';

import { academicYearScopeLabel } from './academicYearScope';
import { formatCount } from './formatters';
import type {
	AttendanceScope,
	AttendanceSummaryForScope,
	AttendanceView,
	Snapshot,
	ViewMode,
} from './types';

const palette = {
	sand: '#f4ecdd',
	leaf: '#1f7a45',
	flame: '#f25b32',
	clay: '#b6522b',
};

const props = defineProps<{
	snapshot: Snapshot;
	displayViewMode: ViewMode;
	attendanceView: AttendanceView;
	attendanceScope: AttendanceScope;
	filteredAllDayHeatmap: Snapshot['attendance']['all_day_heatmap'];
	filteredByCourseHeatmap: Snapshot['attendance']['by_course_heatmap'];
	allDayHeatmapOption: Record<string, unknown>;
	byCourseHeatmapOption: Record<string, unknown>;
	breakdownRows: {
		category: string;
		values: { present: number; excused: number; unexcused: number; late: number };
	}[];
	attendanceSummaryForScope: AttendanceSummaryForScope;
}>();

const emit = defineEmits<{
	(e: 'update:attendanceKpiSource', value: AttendanceView): void;
	(e: 'update:attendanceScope', value: AttendanceScope): void;
}>();
</script>

<template>
	<section class="analytics-card palette-card mt-6 space-y-4">
		<div class="flex flex-wrap items-center justify-center gap-2">
			<button
				type="button"
				:class="[
					'chip-toggle',
					props.attendanceView === 'all_day' ? 'chip-toggle-active' : 'chip-toggle-muted',
				]"
				@click="emit('update:attendanceKpiSource', 'all_day')"
			>
				All-day view
			</button>
			<button
				type="button"
				:class="[
					'chip-toggle',
					props.attendanceView === 'by_course' ? 'chip-toggle-active' : 'chip-toggle-muted',
				]"
				@click="emit('update:attendanceKpiSource', 'by_course')"
			>
				By course / activity
			</button>
			<div class="ml-auto flex items-center gap-2">
				<button
					v-for="scope in ['current', 'last', 'all']"
					:key="scope"
					type="button"
					:class="[
						'chip-scope',
						props.attendanceScope === scope ? 'chip-scope-active' : 'chip-scope-muted',
					]"
					@click="emit('update:attendanceScope', scope as AttendanceScope)"
				>
					{{ academicYearScopeLabel(scope) }}
				</button>
			</div>
		</div>

		<div class="grid grid-cols-1 gap-4 2xl:grid-cols-2">
			<div class="attendance-card palette-card">
				<header class="attendance-card-header">
					<div>
						<h3 class="section-header">Attendance heatmap</h3>
						<p class="type-meta">
							{{
								props.attendanceView === 'all_day'
									? 'Daily status by code'
									: 'Course × week patterns'
							}}
						</p>
					</div>
					<span class="type-chip-muted">
						{{
							props.attendanceView === 'all_day' ? 'Whole-day records' : 'Session-level records'
						}}
					</span>
				</header>

				<div class="attendance-card-body">
					<AnalyticsChart
						v-if="props.attendanceView === 'all_day' && props.filteredAllDayHeatmap.length"
						:option="props.allDayHeatmapOption"
					/>
					<AnalyticsChart
						v-else-if="
							props.attendanceView === 'by_course' && props.filteredByCourseHeatmap.length
						"
						:option="props.byCourseHeatmapOption"
					/>
					<p v-else class="type-empty">No attendance data for this scope.</p>
				</div>
			</div>

			<div class="attendance-card palette-card">
				<header class="attendance-card-header">
					<div>
						<h3 class="section-header">Attendance by course</h3>
						<p class="type-meta">
							{{
								props.attendanceView === 'by_course'
									? 'Sessions by code and course'
									: 'Switch to “By course” to see breakdown'
							}}
						</p>
					</div>
				</header>

				<div class="attendance-card-body space-y-3">
					<StackedBarChart
						v-if="props.attendanceView === 'by_course' && props.breakdownRows.length"
						title=""
						:series="[
							{ key: 'present', label: 'Present', color: palette.leaf },
							{ key: 'excused', label: 'Excused', color: palette.sand },
							{ key: 'unexcused', label: 'Unexcused', color: palette.flame },
							{ key: 'late', label: 'Late', color: palette.clay },
						]"
						:rows="props.breakdownRows"
					/>
					<p v-else class="type-empty">Switch to course view to see breakdown.</p>

					<div class="grid grid-cols-1 gap-2 text-xs sm:grid-cols-3">
						<div class="mini-kpi-card min-w-0">
							<p class="mini-kpi-label">Total days absent</p>
							<p class="mini-kpi-value">
								{{
									formatCount(
										props.attendanceSummaryForScope.excused +
											props.attendanceSummaryForScope.unexcused
									)
								}}
							</p>
						</div>
						<div class="mini-kpi-card mini-kpi-card-alert min-w-0">
							<p class="mini-kpi-label">Unexcused absences</p>
							<p class="mini-kpi-value text-[color:rgb(var(--flame-rgb))]">
								{{ formatCount(props.attendanceSummaryForScope.unexcused) }}
							</p>
						</div>
						<div class="mini-kpi-card min-w-0">
							<p class="mini-kpi-label">
								{{
									props.displayViewMode === 'student'
										? 'Most fragile course'
										: 'Most impacted course'
								}}
							</p>
							<p class="mini-kpi-value">
								{{ props.snapshot.attendance.summary.most_impacted_course?.course_name || '—' }}
							</p>
						</div>
					</div>
				</div>
			</div>
		</div>
	</section>
</template>
