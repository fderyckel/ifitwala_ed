<!-- ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentLogAnalytics.vue -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import AnalyticsCard from '@/components/analytics/AnalyticsCard.vue';
import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue';
import AnalyticsTextPreview from '@/components/analytics/AnalyticsTextPreview.vue';
import StatsTile from '@/components/analytics/StatsTile.vue';
import FiltersBar from '@/components/filters/FiltersBar.vue';
import { useOverlayStack } from '@/composables/useOverlayStack';
import { formatLocalizedDateTime } from '@/lib/datetime';
import { openAnalyticsChartOverlay, openAnalyticsTableOverlay } from '@/lib/analyticsOverlay';
import {
	createDebouncedRunner,
	useStudentLogDashboard,
	useStudentLogFilterMeta,
	useStudentLogRecentLogs,
	type StudentLogRecentPaging,
} from '@/lib/services/studentLogDashboardService';
import type {
	StudentLogChartSeries,
	StudentLogDashboardFilters,
	StudentLogFollowUpSummary,
	StudentLogRecentRow,
	StudentLogStudentRow,
} from '@/types/studentLogDashboard';

type ChartOption = Record<string, unknown>;

type TableRow = StudentLogRecentRow | StudentLogStudentRow;

const INLINE_FOLLOW_UP_LIMIT = 2;

const filters = ref<StudentLogDashboardFilters>({
	school: null,
	academic_year: null,
	program: null,
	author: null,
	from_date: null,
	to_date: null,
	student: null,
});

const selectedStudentLabel = ref('');

const overlay = useOverlayStack();

const filterMetaState = useStudentLogFilterMeta();
const dashboardState = useStudentLogDashboard(filters);
const recentPaging = ref<StudentLogRecentPaging>({ start: 0, pageLength: 25 });
const recentState = useStudentLogRecentLogs(filters, recentPaging);

const filterMeta = filterMetaState.meta;
const filterMetaLoading = filterMetaState.loading;

const schools = computed(() => filterMeta.value.schools);
const academicYears = computed(() => filterMeta.value.academic_years);
const allPrograms = computed(() => filterMeta.value.programs);
const authors = computed(() => filterMeta.value.authors);

const programsForSchool = computed(() => {
	return allPrograms.value;
});
watch(
	filterMeta,
	data => {
		if (!data) return;
		if (data.default_school && !filters.value.school) {
			filters.value.school = data.default_school;
		}
	},
	{ immediate: true }
);

const dashboard = dashboardState.dashboard;
const dashboardRecord = computed<Record<string, unknown> | null>(() => {
	const value = dashboard.value;
	return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
});
const recentRows = computed<StudentLogRecentRow[]>(() => {
	const rows = recentState.rows.value;
	if (!Array.isArray(rows)) return [];
	return rows.map(row => normalizeRecentRow(row));
});
const recentLoading = recentState.loading;
const recentHasMore = recentState.hasMore;

const dashboardError = computed(() => {
	const error = dashboardRecord.value?.error;
	if (typeof error === 'string') return error;
	if (error instanceof Error) return error.message || 'Analytics summary request failed.';
	return '';
});

const openFollowUps = computed(() => {
	const value = dashboardRecord.value?.openFollowUps;
	return typeof value === 'number' ? value : 0;
});
const logTypeCount = computed(() => coerceChartSeries(dashboardRecord.value?.logTypeCount));
const logsByCohort = computed(() => coerceChartSeries(dashboardRecord.value?.logsByCohort));
const logsByProgram = computed(() => coerceChartSeries(dashboardRecord.value?.logsByProgram));
const logsByAuthor = computed(() => coerceChartSeries(dashboardRecord.value?.logsByAuthor));
const nextStepTypes = computed(() => coerceChartSeries(dashboardRecord.value?.nextStepTypes));
const incidentsOverTime = computed(() =>
	coerceChartSeries(dashboardRecord.value?.incidentsOverTime)
);
const studentLogs = computed<StudentLogStudentRow[]>(() => {
	const rows = dashboardRecord.value?.studentLogs;
	if (!Array.isArray(rows)) return [];
	return rows.map(row => normalizeStudentRow(row));
});

const incidentsOption = computed<ChartOption>(() => {
	const data = incidentsOverTime.value;
	if (!data.length) return {};

	return {
		tooltip: { trigger: 'axis' },
		grid: { left: '4%', right: '4%', bottom: '8%', containLabel: true },
		xAxis: {
			type: 'category',
			data: data.map(d => d.label),
			axisLabel: { fontSize: 10 },
		},
		yAxis: { type: 'value' },
		series: [
			{
				type: 'line',
				smooth: true,
				data: data.map(d => d.value),
			},
		],
	};
});

function buildBarOption(data: StudentLogChartSeries[], rotate = 30): ChartOption {
	if (!data.length) return {};
	return {
		tooltip: { trigger: 'item' },
		grid: { left: '4%', right: '4%', bottom: '8%', containLabel: true },
		xAxis: {
			type: 'category',
			data: data.map(d => d.label),
			axisLabel: { fontSize: 10, interval: 0, rotate },
		},
		yAxis: { type: 'value' },
		series: [
			{
				type: 'bar',
				data: data.map(d => d.value),
			},
		],
	};
}

const logTypeOption = computed(() => buildBarOption(logTypeCount.value));
const nextStepTypesOption = computed(() => buildBarOption(nextStepTypes.value));
const logsByCohortOption = computed(() => buildBarOption(logsByCohort.value));
const logsByProgramOption = computed(() => buildBarOption(logsByProgram.value));
const logsByAuthorOption = computed(() => buildBarOption(logsByAuthor.value));
const nonStudentFilterKey = computed(() =>
	JSON.stringify({
		school: filters.value.school,
		academic_year: filters.value.academic_year,
		program: filters.value.program,
		author: filters.value.author,
		from_date: filters.value.from_date,
		to_date: filters.value.to_date,
	})
);

const scheduleRefresh = createDebouncedRunner(400);

watch(
	nonStudentFilterKey,
	() => {
		scheduleRefresh(() => {
			dashboardState.reload();
			recentState.reload({ reset: true });
		});
	},
	{ immediate: false }
);

watch(
	() => filters.value.student,
	(value, previous) => {
		if (!value) {
			selectedStudentLabel.value = '';
			return;
		}
		if (value !== previous) {
			dashboardState.reload();
		}
	}
);

onMounted(() => {
	filterMetaState.reload();
	dashboardState.reload();
	recentState.reload({ reset: true });
});

function openChartOverlay(title: string, option: ChartOption) {
	openAnalyticsChartOverlay(overlay, title, option);
}

function openTableOverlay(title: string, rows: TableRow[], subtitle?: string | null) {
	openAnalyticsTableOverlay(overlay, title, rows, subtitle);
}

function selectStudentFromRecent(row: StudentLogRecentRow) {
	filters.value.student = row.student;
	selectedStudentLabel.value = row.student_full_name || row.student;
}

function formatDate(value: string | null | undefined) {
	return value || '';
}

function stripHtml(html: string) {
	if (!html) return '';
	return html
		.replace(/<[^>]+>/g, ' ')
		.replace(/\s+/g, ' ')
		.trim();
}

function coerceChartSeries(series: unknown): StudentLogChartSeries[] {
	return Array.isArray(series) ? (series as StudentLogChartSeries[]) : [];
}

function normalizeRecentRow(row: StudentLogRecentRow): StudentLogRecentRow {
	const followUps = Array.isArray(row.follow_ups) ? row.follow_ups : [];
	return {
		...row,
		follow_ups: followUps,
		follow_up_count:
			typeof row.follow_up_count === 'number' ? row.follow_up_count : followUps.length,
	};
}

function normalizeStudentRow(row: StudentLogStudentRow): StudentLogStudentRow {
	const followUps = Array.isArray(row.follow_ups) ? row.follow_ups : [];
	return {
		...row,
		follow_ups: followUps,
		follow_up_count:
			typeof row.follow_up_count === 'number' ? row.follow_up_count : followUps.length,
	};
}

function chartHasData(series: StudentLogChartSeries[] | null | undefined) {
	return Array.isArray(series) && series.length > 0;
}

function dashboardCardMessage(fallback: string) {
	return dashboardError.value ? 'Summary unavailable while analytics reloads.' : fallback;
}

function followUpsFor(row: TableRow) {
	return Array.isArray(row.follow_ups) ? row.follow_ups : [];
}

function visibleFollowUps(row: TableRow, limit = INLINE_FOLLOW_UP_LIMIT) {
	return followUpsFor(row).slice(0, limit);
}

function hiddenFollowUpCount(row: TableRow, limit = INLINE_FOLLOW_UP_LIMIT) {
	const total = followUpsFor(row).length;
	return total > limit ? total - limit : 0;
}

function followUpEmptyLabel(row: TableRow) {
	return row.requires_follow_up ? 'Awaiting submitted follow-up' : 'No follow-up recorded';
}

function formatRespondedAt(value: string | null | undefined) {
	return value ? formatLocalizedDateTime(value, { includeWeekday: false, month: 'short' }) : '';
}

function responseMetric(followUp: StudentLogFollowUpSummary) {
	return followUp.responded_in_label ? `Responded in ${followUp.responded_in_label}` : '';
}
</script>

<template>
	<div class="analytics-shell">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-canopy">Student Log Analytics</h1>
				<p class="type-meta text-slate-token/80">
					Trends and follow-ups for the students you have access to.
				</p>
			</div>

			<div class="page-header__actions">
				<StatsTile :value="openFollowUps" label="Open follow-ups" tone="warning" />
			</div>
		</header>

		<FiltersBar>
			<div class="flex flex-col gap-1 w-40">
				<label class="type-label">School</label>
				<select
					v-model="filters.school"
					class="h-9 rounded-md border border-slate-200 px-2"
					:disabled="filterMetaLoading"
				>
					<option value="">All</option>
					<option v-for="s in schools" :key="s.name" :value="s.name">
						{{ s.label || s.name }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1 w-40">
				<label class="type-label">Academic Year</label>
				<select
					v-model="filters.academic_year"
					class="h-9 rounded-md border border-slate-200 px-2"
				>
					<option value="">All</option>
					<option v-for="ay in academicYears" :key="ay.name" :value="ay.name">
						{{ ay.label || ay.name }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1 w-48">
				<label class="type-label">Program</label>
				<select v-model="filters.program" class="h-9 rounded-md border border-slate-200 px-2">
					<option value="">All</option>
					<option v-for="p in programsForSchool" :key="p.name" :value="p.name">
						{{ p.label || p.name }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1 w-48">
				<label class="type-label">Author</label>
				<select v-model="filters.author" class="h-9 rounded-md border border-slate-200 px-2">
					<option value="">All</option>
					<option v-for="a in authors" :key="a.user_id" :value="a.label">
						{{ a.label }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1 w-32">
				<label class="type-label">From</label>
				<input
					v-model="filters.from_date"
					type="date"
					class="h-9 rounded-md border border-slate-200 px-2"
				/>
			</div>

			<div class="flex flex-col gap-1 w-32">
				<label class="type-label">To</label>
				<input
					v-model="filters.to_date"
					type="date"
					class="h-9 rounded-md border border-slate-200 px-2"
				/>
			</div>
		</FiltersBar>

		<div
			v-if="dashboardError"
			class="mt-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3"
		>
			<h2 class="text-sm font-semibold text-amber-900">Analytics summary unavailable</h2>
			<p class="mt-1 text-xs text-amber-800">
				The summary cards could not be loaded. Recent student logs still load below.
			</p>
			<p class="mt-1 text-xs text-amber-700">
				{{ dashboardError }}
			</p>
		</div>

		<section class="analytics-grid">
			<AnalyticsCard
				class="analytics-card--wide"
				title="Logs Over Time"
				@expand="openChartOverlay('Logs Over Time', incidentsOption)"
			>
				<template #body>
					<AnalyticsChart v-if="chartHasData(incidentsOverTime)" :option="incidentsOption" />
					<div v-else class="analytics-empty">
						{{ dashboardCardMessage('No logs for this period.') }}
					</div>
				</template>
			</AnalyticsCard>

			<AnalyticsCard title="Log Types" @expand="openChartOverlay('Log Types', logTypeOption)">
				<template #body>
					<AnalyticsChart v-if="chartHasData(logTypeCount)" :option="logTypeOption" />
					<div v-else class="analytics-empty">{{ dashboardCardMessage('No logs found.') }}</div>
				</template>
			</AnalyticsCard>

			<AnalyticsCard
				title="Next Step Types"
				@expand="openChartOverlay('Next Step Types', nextStepTypesOption)"
			>
				<template #body>
					<AnalyticsChart v-if="chartHasData(nextStepTypes)" :option="nextStepTypesOption" />
					<div v-else class="analytics-empty">
						{{ dashboardCardMessage('No next steps recorded.') }}
					</div>
				</template>
			</AnalyticsCard>

			<AnalyticsCard
				title="Logs by Cohort"
				@expand="openChartOverlay('Logs by Cohort', logsByCohortOption)"
			>
				<template #body>
					<AnalyticsChart v-if="chartHasData(logsByCohort)" :option="logsByCohortOption" />
					<div v-else class="analytics-empty">{{ dashboardCardMessage('No cohorts found.') }}</div>
				</template>
			</AnalyticsCard>

			<AnalyticsCard
				title="Logs by Program"
				@expand="openChartOverlay('Logs by Program', logsByProgramOption)"
			>
				<template #body>
					<AnalyticsChart v-if="chartHasData(logsByProgram)" :option="logsByProgramOption" />
					<div v-else class="analytics-empty">
						{{ dashboardCardMessage('No programs found.') }}
					</div>
				</template>
			</AnalyticsCard>

			<AnalyticsCard
				title="Logs by Author"
				@expand="openChartOverlay('Logs by Author', logsByAuthorOption)"
			>
				<template #body>
					<AnalyticsChart v-if="chartHasData(logsByAuthor)" :option="logsByAuthorOption" />
					<div v-else class="analytics-empty">{{ dashboardCardMessage('No authors found.') }}</div>
				</template>
			</AnalyticsCard>

			<!-- ============================================================
			     TABLE 1: Recent Student Logs
			     Change: bump body typography from caption -> body
			   ============================================================ -->
			<AnalyticsCard
				class="md:col-span-2 xl:col-span-2"
				title="Recent Student Logs"
				@expand="openTableOverlay('Recent Student Logs', recentRows)"
			>
				<template #body>
					<div class="max-h-[320px] overflow-auto">
						<table class="min-w-[680px] w-full table-fixed border-collapse text-ink/80">
							<colgroup>
								<col style="width: 16%" />
								<col style="width: 18%" />
								<col style="width: 14%" />
								<col style="width: 22%" />
								<col style="width: 30%" />
							</colgroup>
							<thead>
								<tr class="border-b border-slate-200 bg-slate-50">
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Date</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Student</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Type</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Log</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Follow-ups</th>
								</tr>
							</thead>

							<tbody class="type-body">
								<tr
									v-for="row in recentRows"
									:key="row.name"
									class="border-b border-slate-100 hover:bg-slate-50 cursor-pointer"
									@click.stop="selectStudentFromRecent(row)"
								>
									<td class="px-2 py-2 align-top whitespace-nowrap">
										{{ formatDate(row.date) }}
									</td>
									<td class="px-2 py-2 align-top">
										<div
											class="analytics-table__cell-truncate"
											:title="row.student_full_name || row.student"
										>
											{{ row.student_full_name || row.student }}
										</div>
									</td>
									<td class="px-2 py-2 align-top">
										<div class="analytics-table__cell-truncate" :title="row.log_type">
											{{ row.log_type }}
										</div>
									</td>
									<td class="px-2 py-2 align-top">
										<AnalyticsTextPreview
											class="analytics-recent-log__snippet"
											:text="stripHtml(row.content || '')"
											:lines="4"
										/>
									</td>
									<td class="px-2 py-2 align-top">
										<div v-if="followUpsFor(row).length" class="analytics-followup-stack">
											<div
												v-for="followUp in visibleFollowUps(row)"
												:key="followUp.name"
												class="analytics-followup-card"
											>
												<div class="analytics-followup-card__meta">
													<span class="analytics-followup-card__chip">{{ followUp.doctype }}</span>
													<span v-if="followUp.next_step"
														>Next step: {{ followUp.next_step }}</span
													>
													<span v-if="responseMetric(followUp)">
														{{ responseMetric(followUp) }}
													</span>
												</div>
												<div class="analytics-followup-card__submeta">
													<span v-if="followUp.follow_up_author">
														{{ followUp.follow_up_author }}
													</span>
													<span v-if="formatRespondedAt(followUp.responded_at)">
														{{ formatRespondedAt(followUp.responded_at) }}
													</span>
												</div>
												<AnalyticsTextPreview
													v-if="followUp.comment_text"
													class="analytics-followup-card__comment"
													:text="followUp.comment_text"
													:lines="2"
													:preview-width="500"
												/>
											</div>
											<p v-if="hiddenFollowUpCount(row)" class="analytics-followup-stack__more">
												+{{ hiddenFollowUpCount(row) }} more follow-up<span
													v-if="hiddenFollowUpCount(row) > 1"
												>
													s
												</span>
											</p>
										</div>
										<div v-else class="analytics-followup-empty">
											{{ followUpEmptyLabel(row) }}
										</div>
									</td>
								</tr>

								<tr v-if="!recentRows.length">
									<td colspan="5" class="px-2 py-3 text-center type-empty">
										No logs in this period.
									</td>
								</tr>
							</tbody>
						</table>
					</div>

					<div class="mt-3 flex justify-center">
						<button
							type="button"
							class="inline-flex items-center justify-center rounded-full border border-slate-200 px-3 py-1 type-button-label text-slate-token/70 hover:bg-slate-50"
							:disabled="recentLoading || !recentHasMore"
							@click.stop="recentState.reload()"
						>
							{{ recentLoading ? 'Loading...' : recentHasMore ? 'Load more' : 'No more logs' }}
						</button>
					</div>
				</template>
			</AnalyticsCard>

			<!-- ============================================================
			     TABLE 2: Selected Student Logs
			     Change: bump body typography from caption -> body
			   ============================================================ -->
			<AnalyticsCard
				class="md:col-span-2 xl:col-span-3"
				title="Selected Student Logs"
				@expand="
					openTableOverlay(
						'Selected Student Logs',
						studentLogs,
						selectedStudentLabel || filters.student
					)
				"
			>
				<template #subtitle>
					<span v-if="filters.student" class="type-caption text-slate-token/70">
						{{ selectedStudentLabel || filters.student }}
					</span>
					<span v-else class="type-caption text-slate-token/60">
						Choose a student (from the table) to see their logs.
					</span>
				</template>

				<template #body>
					<div class="max-h-[260px] overflow-auto">
						<table class="min-w-full border-collapse text-ink/80">
							<thead>
								<tr class="border-b border-slate-200 bg-slate-50">
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Date</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Type</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Log</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Author</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Follow-ups</th>
								</tr>
							</thead>

							<tbody class="type-body">
								<tr
									v-for="row in studentLogs"
									:key="row.name"
									class="border-b border-slate-100 hover:bg-slate-50"
								>
									<td class="px-2 py-2 align-top whitespace-nowrap">
										{{ formatDate(row.date) }}
									</td>
									<td class="px-2 py-2 align-top whitespace-nowrap">
										{{ row.log_type }}
									</td>
									<td class="px-2 py-2 align-top">
										<AnalyticsTextPreview
											class="analytics-selected-log__snippet"
											:text="stripHtml(row.content || '')"
											:lines="3"
										/>
									</td>
									<td class="px-2 py-2 align-top whitespace-nowrap">
										{{ row.author }}
									</td>
									<td class="px-2 py-2 align-top">
										<div v-if="followUpsFor(row).length" class="analytics-followup-stack">
											<div
												v-for="followUp in visibleFollowUps(row)"
												:key="followUp.name"
												class="analytics-followup-card"
											>
												<div class="analytics-followup-card__meta">
													<span class="analytics-followup-card__chip">{{ followUp.doctype }}</span>
													<span v-if="followUp.next_step"
														>Next step: {{ followUp.next_step }}</span
													>
													<span v-if="responseMetric(followUp)">
														{{ responseMetric(followUp) }}
													</span>
												</div>
												<div class="analytics-followup-card__submeta">
													<span v-if="followUp.follow_up_author">
														{{ followUp.follow_up_author }}
													</span>
													<span v-if="formatRespondedAt(followUp.responded_at)">
														{{ formatRespondedAt(followUp.responded_at) }}
													</span>
												</div>
												<AnalyticsTextPreview
													v-if="followUp.comment_text"
													class="analytics-followup-card__comment"
													:text="followUp.comment_text"
													:lines="2"
													:preview-width="500"
												/>
											</div>
											<p v-if="hiddenFollowUpCount(row)" class="analytics-followup-stack__more">
												+{{ hiddenFollowUpCount(row) }} more follow-up<span
													v-if="hiddenFollowUpCount(row) > 1"
												>
													s
												</span>
											</p>
										</div>
										<div v-else class="analytics-followup-empty">
											{{ followUpEmptyLabel(row) }}
										</div>
									</td>
								</tr>

								<tr v-if="!studentLogs.length">
									<td colspan="5" class="px-2 py-3 text-center type-empty">
										{{ dashboardCardMessage('No logs to show yet.') }}
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</template>
			</AnalyticsCard>
		</section>
	</div>
</template>

<style scoped>
.analytics-table__cell-truncate {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.analytics-recent-log__snippet {
	font-size: 1rem;
	line-height: 1.5rem;
	color: rgb(var(--ink-rgb) / 0.92);
}

.analytics-selected-log__snippet {
	font-size: 1rem;
	line-height: 1.6rem;
	color: rgb(var(--ink-rgb) / 0.92);
}

.analytics-followup-stack {
	display: flex;
	flex-direction: column;
	gap: 0.5rem;
}

.analytics-followup-card {
	border: 1px solid rgb(var(--border-rgb) / 0.6);
	border-radius: var(--radius-lg);
	padding: 0.55rem 0.7rem;
	background: linear-gradient(
		135deg,
		rgb(var(--sand-rgb) / 0.7),
		rgb(var(--surface-strong-rgb) / 0.98)
	);
}

.analytics-followup-card__meta,
.analytics-followup-card__submeta {
	display: flex;
	flex-wrap: wrap;
	gap: 0.35rem 0.55rem;
	align-items: center;
}

.analytics-followup-card__meta {
	font-size: 0.73rem;
	line-height: 1.05rem;
	font-weight: 600;
	color: rgb(var(--flame-rgb) / 0.92);
}

.analytics-followup-card__submeta {
	margin-top: 0.22rem;
	font-size: 0.72rem;
	line-height: 1rem;
	color: rgb(var(--slate-rgb) / 0.82);
}

.analytics-followup-card__chip {
	display: inline-flex;
	align-items: center;
	border-radius: 9999px;
	padding: 0.08rem 0.48rem;
	background: rgb(var(--flame-rgb) / 0.14);
	color: rgb(var(--flame-rgb) / 0.92);
}

.analytics-followup-card__comment {
	margin-top: 0.4rem;
	font-size: 0.8rem;
	line-height: 1.25rem;
	color: rgb(var(--ink-rgb) / 0.9);
}

.analytics-followup-stack__more,
.analytics-followup-empty {
	font-size: 0.75rem;
	line-height: 1rem;
	color: rgb(var(--slate-rgb) / 0.78);
}
</style>
