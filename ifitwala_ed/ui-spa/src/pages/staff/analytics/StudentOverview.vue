<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { createResource } from 'frappe-ui';

import FiltersBar from '@/components/filters/FiltersBar.vue';

import { matchesAcademicYearScope } from './student-overview/academicYearScope';
import { emptySnapshot, viewModeOptions } from './student-overview/constants';
import { formatCount, formatPct } from './student-overview/formatters';
import StudentOverviewAttendanceBand from './student-overview/StudentOverviewAttendanceBand.vue';
import StudentOverviewHistoryBand from './student-overview/StudentOverviewHistoryBand.vue';
import StudentOverviewLearningBand from './student-overview/StudentOverviewLearningBand.vue';
import StudentOverviewSnapshotBand from './student-overview/StudentOverviewSnapshotBand.vue';
import StudentOverviewWellbeingBand from './student-overview/StudentOverviewWellbeingBand.vue';
import type {
	AttendanceKpiSource,
	AttendanceScope,
	AttendanceSummaryForScope,
	AttendanceView,
	KpiTile,
	PermissionFlags,
	Snapshot,
	StudentSuggestion,
	ViewMode,
} from './student-overview/types';

const palette = {
	sand: '#f4ecdd',
	moss: '#7faa63',
	leaf: '#1f7a45',
	flame: '#f25b32',
	clay: '#b6522b',
};

const filters = ref<{ school: string | null; program: string | null; student: string | null }>({
	school: null,
	program: null,
	student: null,
});

const viewMode = ref<ViewMode>('staff');

const filterMetaResource = createResource({
	url: 'ifitwala_ed.api.student_overview_dashboard.get_filter_meta',
	method: 'GET',
	auto: true,
});

const filterMeta = computed(() => (filterMetaResource.data as any) || {});
const schools = computed(() => filterMeta.value.schools || []);
const programs = computed(() => filterMeta.value.programs || []);

watch(
	filterMeta,
	meta => {
		if (meta?.default_school && !filters.value.school) {
			filters.value.school = meta.default_school;
		}
	},
	{ immediate: true }
);

watch(
	() => filters.value.school,
	(newSchool, oldSchool) => {
		if (newSchool !== oldSchool) {
			filters.value.program = null;
			clearStudent();
		}
	}
);

const studentSearch = ref('');
const studentSuggestions = ref<StudentSuggestion[]>([]);
const studentDropdownOpen = ref(false);
let studentSearchTimer: number | undefined;

const studentSearchResource = createResource({
	url: 'ifitwala_ed.api.student_overview_dashboard.search_students',
	method: 'GET',
	auto: false,
});

const studentLoading = computed(() => studentSearchResource.loading);

function debounce(fn: () => void, delay = 350) {
	window.clearTimeout(studentSearchTimer);
	studentSearchTimer = window.setTimeout(fn, delay);
}

function openStudentDropdown() {
	studentDropdownOpen.value = true;
}

async function fetchStudents() {
	const query = studentSearch.value.trim();

	if (!query) {
		studentSuggestions.value = [];
		studentDropdownOpen.value = true;
		return;
	}

	const response = await studentSearchResource.fetch({
		search_text: query,
		school: filters.value.school,
		program: filters.value.program,
	});
	const list = (response as any[]) || [];
	studentSuggestions.value = list.map(item => ({
		id: item.student || item.name,
		name: item.student_full_name || item.full_name || item.name,
	}));
	studentDropdownOpen.value = !!studentSuggestions.value.length;
}

function selectStudent(student: StudentSuggestion) {
	filters.value.student = student.id;
	studentSearch.value = student.name;
	studentDropdownOpen.value = false;
}

function clearStudent() {
	filters.value.student = null;
	studentSearch.value = '';
	studentSuggestions.value = [];
	studentDropdownOpen.value = false;
}

const readyForSnapshot = computed(() =>
	Boolean(filters.value.school && filters.value.program && filters.value.student)
);

const snapshotResource = createResource({
	url: 'ifitwala_ed.api.student_overview_dashboard.get_student_center_snapshot',
	method: 'POST',
	auto: false,
});

const snapshotErrorMessage = ref('');
const avatarLoadFailed = ref(false);

const snapshot = computed<Snapshot>(() => (snapshotResource.data as Snapshot) || emptySnapshot);
const loadingSnapshot = computed(() => snapshotResource.loading);
const hasSnapshotData = computed(() => Boolean(snapshot.value.meta.student));

function describeResourceError(error: unknown, fallback: string) {
	let message = '';

	if (typeof error === 'string') {
		message = error.trim();
	} else if (error instanceof Error) {
		message = error.message.trim();
	} else if (error && typeof error === 'object' && 'message' in error) {
		message =
			typeof (error as { message?: unknown }).message === 'string'
				? (error as { message: string }).message.trim()
				: '';
	}

	if (
		message &&
		!/\/api\/method\/|Traceback|ProgrammingError|INTERNAL SERVER ERROR/i.test(message) &&
		message.length <= 180
	) {
		return message;
	}
	return fallback;
}

function handleAvatarError() {
	avatarLoadFailed.value = true;
}

let snapshotDebounce: number | undefined;

function debounceSnapshot() {
	window.clearTimeout(snapshotDebounce);
	snapshotDebounce = window.setTimeout(() => {
		if (readyForSnapshot.value) loadSnapshot();
	}, 350);
}

async function loadSnapshot() {
	if (!readyForSnapshot.value || snapshotResource.loading) return;

	snapshotErrorMessage.value = '';
	try {
		await snapshotResource.submit({
			student: filters.value.student,
			school: filters.value.school,
			program: filters.value.program,
			view_mode: viewMode.value,
		});
	} catch (error) {
		snapshotErrorMessage.value = describeResourceError(
			error,
			'Unable to load this student overview right now.'
		);
	}
}

watch(
	[filters, viewMode],
	() => {
		snapshotErrorMessage.value = '';
		debounceSnapshot();
	},
	{ deep: true }
);

onMounted(() => {
	if (readyForSnapshot.value) loadSnapshot();
});

watch(
	() => readyForSnapshot.value,
	ready => {
		if (!ready) {
			snapshotErrorMessage.value = '';
		}
	}
);

watch(
	() => snapshot.value.identity.photo,
	() => {
		avatarLoadFailed.value = false;
	},
	{ immediate: true }
);

const attendanceView = ref<AttendanceView>('all_day');
const attendanceScope = ref<AttendanceScope>('current');
const attendanceKpiSource = ref<AttendanceKpiSource>('all_day');

const permissions = computed<PermissionFlags>(() => snapshot.value.meta.permissions);
const displayViewMode = computed<ViewMode>(() => snapshot.value.meta.view_mode || viewMode.value);

const hasAllDayHeatmap = computed(
	() => (snapshot.value.attendance.all_day_heatmap || []).length > 0
);
const hasByCourseHeatmap = computed(
	() => (snapshot.value.attendance.by_course_heatmap || []).length > 0
);

watch(
	[() => hasAllDayHeatmap.value, () => hasByCourseHeatmap.value],
	([hasAllDay, hasByCourse]) => {
		if (hasAllDay) {
			attendanceView.value = 'all_day';
			attendanceKpiSource.value = 'all_day';
		} else if (hasByCourse) {
			attendanceView.value = 'by_course';
			attendanceKpiSource.value = 'by_course';
		}
	}
);

const attendanceSourceToggle = computed(() => ({
	active: attendanceKpiSource.value,
	options: [
		{ id: 'all_day' as AttendanceKpiSource, label: 'Whole day' },
		{ id: 'by_course' as AttendanceKpiSource, label: 'Per course' },
	],
}));

function setAttendanceKpiSource(source: AttendanceKpiSource) {
	attendanceKpiSource.value = source;
	attendanceView.value = source;
}

function setAttendanceScope(scope: AttendanceScope) {
	attendanceScope.value = scope;
}

const filteredAllDayHeatmap = computed(() => {
	const list = snapshot.value.attendance.all_day_heatmap || [];
	return list.filter(row =>
		matchesAcademicYearScope(row.academic_year, attendanceScope.value, {
			currentAcademicYear: snapshot.value.meta.current_academic_year,
			yearOptions: snapshot.value.history.year_options || [],
		})
	);
});

const allDayHeatmapOption = computed(() => {
	if (attendanceView.value !== 'all_day') return {};
	const data = filteredAllDayHeatmap.value;
	if (!data.length) return {};
	const dates = data.map(item => item.date);
	const values = data.map((item, index) => [index, 0, 1, item]);
	return {
		grid: { left: 20, right: 10, top: 10, bottom: 30 },
		xAxis: {
			type: 'category',
			data: dates,
			axisLabel: { show: false },
			splitArea: { show: false },
		},
		yAxis: {
			type: 'category',
			data: [''],
			axisLabel: { show: false },
			splitArea: { show: false },
		},
		tooltip: {
			formatter: (params: any) => {
				const item = params.value?.[3] || {};
				return `${item.date || ''}<br>${item.attendance_code_name || item.attendance_code || ''}`;
			},
		},
		visualMap: { show: false, min: 0, max: 1 },
		series: [
			{
				type: 'heatmap',
				data: values,
				itemStyle: {
					borderWidth: 1,
					borderColor: 'rgba(7,16,25,0.08)',
					color: (params: any) => {
						const row = params.value?.[3] || {};
						if (row.color) return row.color;
						if (row.is_late) return palette.clay;
						if (row.count_as_present) return palette.leaf;
						return palette.flame;
					},
				},
			},
		],
	};
});

const filteredByCourseHeatmap = computed(() => {
	const list = snapshot.value.attendance.by_course_heatmap || [];
	return list.filter(row =>
		matchesAcademicYearScope(row.academic_year, attendanceScope.value, {
			currentAcademicYear: snapshot.value.meta.current_academic_year,
			yearOptions: snapshot.value.history.year_options || [],
		})
	);
});

const byCourseHeatmapOption = computed(() => {
	if (attendanceView.value !== 'by_course') return {};
	const rows = filteredByCourseHeatmap.value;
	if (!rows.length) return {};
	const courses = Array.from(new Set(rows.map(row => row.course_name || row.course)));
	const weeks = Array.from(new Set(rows.map(row => row.week_label)));
	const data = rows.map(row => {
		const severity =
			(row.unexcused_sessions || 0) * 2 +
			(row.absent_sessions || 0) +
			(row.late_sessions || 0) +
			1;
		return {
			value: [
				weeks.indexOf(row.week_label),
				courses.indexOf(row.course_name || row.course),
				severity,
			],
			row,
		};
	});
	const minSeverity = Math.min(...data.map(item => item.value[2]));
	const maxSeverity = Math.max(...data.map(item => item.value[2]));
	return {
		grid: { left: 120, right: 10, top: 10, bottom: 48 },
		xAxis: { type: 'category', data: weeks, axisLabel: { rotate: 30 } },
		yAxis: { type: 'category', data: courses },
		tooltip: {
			formatter: (params: any) => {
				const row = params.data?.row || {};
				return `${row.course_name || row.course} (${row.week_label})<br>${formatCount(
					row.unexcused_sessions
				)} unexcused / ${formatCount(row.absent_sessions)} absent / ${formatCount(
					row.late_sessions
				)} late / ${formatCount(row.present_sessions)} present`;
			},
		},
		visualMap: {
			show: false,
			min: minSeverity,
			max: maxSeverity,
			orient: 'horizontal',
			left: 'center',
			bottom: 10,
			text: ['More misses', 'Fewer'],
			inRange: {
				color: [palette.sand, palette.moss, palette.flame],
			},
		},
		series: [
			{
				type: 'heatmap',
				data,
				itemStyle: { borderWidth: 1, borderColor: '#fff' },
				emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.2)' } },
			},
		],
	};
});

const breakdownRows = computed(() => {
	const list = snapshot.value.attendance.by_course_breakdown || [];
	return list
		.filter(row =>
			matchesAcademicYearScope(row.academic_year, attendanceScope.value, {
				currentAcademicYear: snapshot.value.meta.current_academic_year,
				yearOptions: snapshot.value.history.year_options || [],
			})
		)
		.map(row => ({
			category: row.course_name || row.course,
			values: {
				present: row.present_sessions,
				excused: row.excused_absent_sessions,
				unexcused: row.unexcused_absent_sessions,
				late: row.late_sessions,
			},
		}));
});

const attendanceSummaryForScope = computed<AttendanceSummaryForScope>(() => {
	if (attendanceKpiSource.value === 'by_course') {
		const totals = breakdownRows.value.reduce(
			(accumulator, row) => {
				accumulator.present += row.values.present || 0;
				accumulator.excused += row.values.excused || 0;
				accumulator.unexcused += row.values.unexcused || 0;
				accumulator.late += row.values.late || 0;
				return accumulator;
			},
			{ present: 0, excused: 0, unexcused: 0, late: 0 }
		);
		const totalSessions = totals.present + totals.excused + totals.unexcused + totals.late;
		return {
			present_percentage: totalSessions ? totals.present / totalSessions : 0,
			total_entries: totalSessions,
			present: totals.present,
			excused: totals.excused,
			unexcused: totals.unexcused,
			late: totals.late,
		};
	}

	const rows = filteredAllDayHeatmap.value;
	const present = rows.filter(row => row.count_as_present).length;
	const excused = rows.filter(row => row.is_excused).length;
	const late = rows.filter(row => row.is_late).length;
	const total = rows.length;
	const unexcused = rows.filter(
		row => !row.count_as_present && !row.is_excused && !row.is_late
	).length;
	return {
		present_percentage: total
			? present / total
			: snapshot.value.kpis.attendance.present_percentage,
		total_entries: total,
		present,
		excused: total ? excused : snapshot.value.kpis.attendance.excused_absences,
		unexcused: total ? unexcused : snapshot.value.kpis.attendance.unexcused_absences,
		late: total ? late : snapshot.value.kpis.attendance.late_count,
	};
});

const kpiTiles = computed<KpiTile[]>(() => [
	{
		label: 'Attendance',
		value: `${formatPct(attendanceSummaryForScope.value.present_percentage)} present`,
		sub: `${formatCount(attendanceSummaryForScope.value.unexcused || 0)} unexcused · ${formatCount(
			attendanceSummaryForScope.value.excused || 0
		)} excused`,
		clickable: hasAllDayHeatmap.value && hasByCourseHeatmap.value,
		onClick: () => {
			if (hasAllDayHeatmap.value && hasByCourseHeatmap.value) {
				attendanceKpiSource.value =
					attendanceKpiSource.value === 'all_day' ? 'by_course' : 'all_day';
				attendanceView.value = attendanceKpiSource.value;
			}
		},
		sourceToggle: attendanceSourceToggle.value,
	},
	{
		label: 'Tasks',
		value: `${formatPct(snapshot.value.kpis.tasks.completion_rate)} tasks completed`,
		sub: `${formatCount(snapshot.value.kpis.tasks.overdue_tasks)} overdue · ${formatCount(
			snapshot.value.kpis.tasks.missed_tasks
		)} missed`,
	},
	{
		label: 'Academic progress',
		value: snapshot.value.kpis.academic.latest_overall_label || '—',
		sub: snapshot.value.kpis.academic.trend
			? `Trend: ${snapshot.value.kpis.academic.trend}`
			: 'Latest overall grade',
	},
	{
		label: 'Support signals',
		value: `${formatCount(snapshot.value.kpis.support.student_logs_total)} logs`,
		sub: `${formatCount(snapshot.value.kpis.support.active_referrals)} referral(s) · ${formatCount(
			snapshot.value.kpis.support.nurse_visits_this_term
		)} nurse visits`,
	},
]);
</script>

<template>
	<div class="analytics-shell">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-canopy">Student Overview</h1>
				<p class="type-meta text-slate-token/80">
					One student snapshot across identity, learning, attendance, wellbeing, and history.
				</p>
			</div>
			<div class="page-header__actions ifit-filters">
				<div class="flex flex-col gap-1">
					<label for="student-overview-view-mode" class="type-label">Lens</label>
					<select
						id="student-overview-view-mode"
						v-model="viewMode"
						class="h-9 rounded-md border px-2 text-sm"
					>
						<option v-for="mode in viewModeOptions" :key="mode.id" :value="mode.id">
							{{ mode.label }}
						</option>
					</select>
				</div>
			</div>
		</header>

		<FiltersBar class="analytics-filters" data-testid="student-overview-filter-bar">
			<div
				class="grid w-full gap-3 md:grid-cols-2 xl:grid-cols-[repeat(2,minmax(0,12rem))_minmax(0,16rem)]"
			>
				<div class="flex min-w-0 flex-col gap-1">
					<label class="type-label">School</label>
					<select
						v-model="filters.school"
						class="h-9 rounded-md border px-2 text-xs"
						data-testid="student-overview-school-filter"
					>
						<option value="">Select a school</option>
						<option v-for="school in schools" :key="school.name" :value="school.name">
							{{ school.label || school.name }}
						</option>
					</select>
				</div>

				<div class="flex min-w-0 flex-col gap-1">
					<label class="type-label">Program</label>
					<select
						v-model="filters.program"
						class="h-9 rounded-md border px-2 text-xs"
						data-testid="student-overview-program-filter"
					>
						<option value="">Select</option>
						<option v-for="program in programs" :key="program.name" :value="program.name">
							{{ program.label || program.name }}
						</option>
					</select>
				</div>

				<div class="relative flex min-w-0 flex-col gap-1">
					<label class="type-label">Student</label>
					<div class="control-input flex h-9 items-center rounded-md border px-2">
						<span class="mr-1 text-[11px] text-ink/60">🔍</span>
						<input
							v-model="studentSearch"
							class="h-full w-full text-xs"
							data-testid="student-overview-student-search"
							placeholder="Search student"
							type="search"
							@focus="openStudentDropdown"
							@input="debounce(fetchStudents)"
						/>
						<button
							v-if="studentSearch"
							type="button"
							class="ml-1 text-[11px] text-ink/60"
							@click="clearStudent"
						>
							Clear
						</button>
					</div>
					<div
						v-if="studentDropdownOpen"
						class="absolute top-full z-30 mt-1 max-h-56 w-full overflow-auto rounded-xl border border-border/80 bg-[rgb(var(--surface-rgb))] shadow-soft"
					>
						<div v-if="studentLoading" class="px-3 py-2 text-xs text-ink/70">Searching…</div>
						<button
							v-for="student in studentSuggestions"
							:key="student.id"
							type="button"
							class="flex w-full items-start gap-2 px-3 py-2 text-left text-xs hover:bg-[rgb(var(--surface-rgb)/0.9)]"
							@click="selectStudent(student)"
						>
							<span class="font-semibold text-ink">{{ student.name }}</span>
						</button>
						<div
							v-if="!studentLoading && !studentSuggestions.length"
							class="px-3 py-2 text-xs text-ink/60"
						>
							{{
								studentSearch
									? 'No matches. Try a different name or ID.'
									: 'Start typing to search for a student.'
							}}
						</div>
					</div>
				</div>
			</div>
		</FiltersBar>

		<section class="mt-4 space-y-4">
			<div
				v-if="!readyForSnapshot"
				class="rounded-xl border border-dashed border-slate-200 bg-white/70 px-4 py-6 text-sm text-slate-500"
			>
				Choose a school, program, and student to load the overview.
			</div>

			<div v-else>
				<div
					v-if="loadingSnapshot"
					class="rounded-xl border border-slate-200 bg-white/70 px-4 py-6 text-sm text-slate-500 shadow-sm"
				>
					Loading snapshot…
				</div>

				<div
					v-else-if="snapshotErrorMessage && !hasSnapshotData"
					class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-900 shadow-sm"
				>
					<p class="font-semibold">Unable to load this student overview.</p>
					<p class="mt-1 text-rose-800/90">{{ snapshotErrorMessage }}</p>
					<p class="mt-2 text-xs text-rose-800/80">
						Try reselecting the student. If the error persists, review the server logs for this
						snapshot request.
					</p>
				</div>

				<div v-else class="space-y-6">
					<div
						v-if="snapshotErrorMessage"
						class="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 shadow-sm"
					>
						{{ snapshotErrorMessage }}
					</div>

					<StudentOverviewSnapshotBand
						:snapshot="snapshot"
						:avatar-load-failed="avatarLoadFailed"
						:kpi-tiles="kpiTiles"
						@avatar-error="handleAvatarError"
						@attendance-kpi-source="setAttendanceKpiSource"
					/>

					<StudentOverviewLearningBand :snapshot="snapshot" :permissions="permissions" />

					<StudentOverviewAttendanceBand
						:snapshot="snapshot"
						:display-view-mode="displayViewMode"
						:attendance-view="attendanceView"
						:attendance-scope="attendanceScope"
						:filtered-all-day-heatmap="filteredAllDayHeatmap"
						:filtered-by-course-heatmap="filteredByCourseHeatmap"
						:all-day-heatmap-option="allDayHeatmapOption"
						:by-course-heatmap-option="byCourseHeatmapOption"
						:breakdown-rows="breakdownRows"
						:attendance-summary-for-scope="attendanceSummaryForScope"
						@update:attendance-kpi-source="setAttendanceKpiSource"
						@update:attendance-scope="setAttendanceScope"
					/>

					<StudentOverviewWellbeingBand :snapshot="snapshot" :permissions="permissions" />

					<StudentOverviewHistoryBand :snapshot="snapshot" :display-view-mode="displayViewMode" />
				</div>
			</div>
		</section>
	</div>
</template>
