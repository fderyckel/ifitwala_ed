<!-- ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentLogAnalytics.vue -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import AnalyticsCard from '@/components/analytics/AnalyticsCard.vue'
import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue'
import StatsTile from '@/components/analytics/StatsTile.vue'
import FiltersBar from '@/components/filters/FiltersBar.vue'
import { useOverlayStack } from '@/composables/useOverlayStack'
import {
	createDebouncedRunner,
	useStudentLogDashboard,
	useStudentLogFilterMeta,
	useStudentLogRecentLogs,
	type StudentLogRecentPaging,
} from '@/services/studentLogDashboardService'
import type {
	StudentLogChartSeries,
	StudentLogDashboardFilters,
	StudentLogRecentRow,
	StudentLogStudentRow,
} from '@/types/studentLogDashboard'

type ChartOption = Record<string, unknown>

type TableRow = StudentLogRecentRow | StudentLogStudentRow

const filters = ref<StudentLogDashboardFilters>({
	school: null,
	academic_year: null,
	program: null,
	author: null,
	from_date: null,
	to_date: null,
	student: null,
})

const selectedStudentLabel = ref('')

const overlay = useOverlayStack()

const filterMetaState = useStudentLogFilterMeta()
const dashboardState = useStudentLogDashboard(filters)
const recentPaging = ref<StudentLogRecentPaging>({ start: 0, pageLength: 25 })
const recentState = useStudentLogRecentLogs(filters, recentPaging)

const filterMeta = filterMetaState.meta
const filterMetaLoading = filterMetaState.loading

const schools = computed(() => filterMeta.value.schools)
const academicYears = computed(() => filterMeta.value.academic_years)
const allPrograms = computed(() => filterMeta.value.programs)
const authors = computed(() => filterMeta.value.authors)

const programsForSchool = computed(() => {
	return allPrograms.value
})

watch(
	filterMeta,
	(data) => {
		if (!data) return
		if (data.default_school && !filters.value.school) {
			filters.value.school = data.default_school
		}
	},
	{ immediate: true }
)

const dashboard = dashboardState.dashboard
const recentRows = recentState.rows
const recentLoading = recentState.loading
const recentHasMore = recentState.hasMore

const openFollowUps = computed(() => dashboard.value.openFollowUps)
const logTypeCount = computed(() => dashboard.value.logTypeCount)
const logsByCohort = computed(() => dashboard.value.logsByCohort)
const logsByProgram = computed(() => dashboard.value.logsByProgram)
const logsByAuthor = computed(() => dashboard.value.logsByAuthor)
const nextStepTypes = computed(() => dashboard.value.nextStepTypes)
const incidentsOverTime = computed(() => dashboard.value.incidentsOverTime)
const studentLogs = computed(() => dashboard.value.studentLogs)

const incidentsOption = computed<ChartOption>(() => {
	const data = incidentsOverTime.value
	if (!data.length) return {}

	return {
		tooltip: { trigger: 'axis' },
		grid: { left: '4%', right: '4%', bottom: '8%', containLabel: true },
		xAxis: {
			type: 'category',
			data: data.map((d) => d.label),
			axisLabel: { fontSize: 10 },
		},
		yAxis: { type: 'value' },
		series: [
			{
				type: 'line',
				smooth: true,
				data: data.map((d) => d.value),
			},
		],
	}
})

function buildBarOption(data: StudentLogChartSeries[], rotate = 30): ChartOption {
	if (!data.length) return {}
	return {
		tooltip: { trigger: 'item' },
		grid: { left: '4%', right: '4%', bottom: '8%', containLabel: true },
		xAxis: {
			type: 'category',
			data: data.map((d) => d.label),
			axisLabel: { fontSize: 10, interval: 0, rotate },
		},
		yAxis: { type: 'value' },
		series: [
			{
				type: 'bar',
				data: data.map((d) => d.value),
			},
		],
	}
}

const logTypeOption = computed(() => buildBarOption(logTypeCount.value))
const nextStepTypesOption = computed(() => buildBarOption(nextStepTypes.value))
const logsByCohortOption = computed(() => buildBarOption(logsByCohort.value))
const logsByProgramOption = computed(() => buildBarOption(logsByProgram.value))
const logsByAuthorOption = computed(() => buildBarOption(logsByAuthor.value))

const scheduleRefresh = createDebouncedRunner(400)

watch(
	filters,
	() => {
		scheduleRefresh(() => {
			dashboardState.reload()
			recentState.reload({ reset: true })
		})
	},
	{ deep: true }
)

watch(
	() => filters.value.student,
	(value) => {
		if (!value) selectedStudentLabel.value = ''
	}
)

onMounted(() => {
	filterMetaState.reload()
	dashboardState.reload()
	recentState.reload({ reset: true })
})

function openChartOverlay(title: string, option: ChartOption) {
	overlay.open('student-log-analytics-expand', {
		title,
		chartOption: option,
		kind: 'chart',
	})
}

function openTableOverlay(title: string, rows: TableRow[], subtitle?: string | null) {
	overlay.open('student-log-analytics-expand', {
		title,
		chartOption: {},
		kind: 'table',
		rows,
		subtitle: subtitle ?? null,
	})
}

function selectStudentFromRecent(row: StudentLogRecentRow) {
	filters.value.student = row.student
	selectedStudentLabel.value = row.student_full_name || row.student
}

function formatDate(value: string | null | undefined) {
	return value || ''
}

function stripHtml(html: string) {
	if (!html) return ''
	return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
}

function truncate(text: string, max = 140) {
	if (!text) return ''
	return text.length > max ? `${text.slice(0, max)}...` : text
}
</script>

<template>
	<div class="analytics-shell">
		<header class="flex flex-wrap items-center justify-between gap-3">
			<div>
				<h1 class="type-h2 text-canopy">Student Log Analytics</h1>
				<p class="type-body text-slate-token/80 mt-1">
					Trends and follow-ups for the students you have access to.
				</p>
			</div>

			<StatsTile
				:value="openFollowUps"
				label="Open follow-ups"
				tone="warning"
			/>
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
				<select
					v-model="filters.program"
					class="h-9 rounded-md border border-slate-200 px-2"
				>
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

		<section class="analytics-grid">
			<AnalyticsCard
				class="analytics-card--wide"
				title="Logs Over Time"
				@expand="openChartOverlay('Logs Over Time', incidentsOption)"
			>
				<template #body>
					<AnalyticsChart v-if="incidentsOverTime.length" :option="incidentsOption" />
					<div v-else class="analytics-empty">No logs for this period.</div>
				</template>
			</AnalyticsCard>

			<AnalyticsCard
				title="Log Types"
				@expand="openChartOverlay('Log Types', logTypeOption)"
			>
				<template #body>
					<AnalyticsChart v-if="logTypeCount.length" :option="logTypeOption" />
					<div v-else class="analytics-empty">No logs found.</div>
				</template>
			</AnalyticsCard>

			<AnalyticsCard
				title="Next Step Types"
				@expand="openChartOverlay('Next Step Types', nextStepTypesOption)"
			>
				<template #body>
					<AnalyticsChart v-if="nextStepTypes.length" :option="nextStepTypesOption" />
					<div v-else class="analytics-empty">No next steps recorded.</div>
				</template>
			</AnalyticsCard>

			<AnalyticsCard
				title="Logs by Cohort"
				@expand="openChartOverlay('Logs by Cohort', logsByCohortOption)"
			>
				<template #body>
					<AnalyticsChart v-if="logsByCohort.length" :option="logsByCohortOption" />
					<div v-else class="analytics-empty">No cohorts found.</div>
				</template>
			</AnalyticsCard>

			<AnalyticsCard
				title="Logs by Program"
				@expand="openChartOverlay('Logs by Program', logsByProgramOption)"
			>
				<template #body>
					<AnalyticsChart v-if="logsByProgram.length" :option="logsByProgramOption" />
					<div v-else class="analytics-empty">No programs found.</div>
				</template>
			</AnalyticsCard>

			<AnalyticsCard
				title="Logs by Author"
				@expand="openChartOverlay('Logs by Author', logsByAuthorOption)"
			>
				<template #body>
					<AnalyticsChart v-if="logsByAuthor.length" :option="logsByAuthorOption" />
					<div v-else class="analytics-empty">No authors found.</div>
				</template>
			</AnalyticsCard>

			<AnalyticsCard
				title="Recent Student Logs"
				@expand="openTableOverlay('Recent Student Logs', recentRows)"
			>
				<template #body>
					<div class="max-h-[320px] overflow-auto">
						<table class="min-w-full border-collapse type-caption text-ink/80">
							<thead>
								<tr class="border-b border-slate-200 bg-slate-50">
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Date</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Student</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Program</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Type</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Log</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Author</th>
									<th class="px-2 py-2 text-center type-label text-slate-token/70">FU</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="row in recentRows"
									:key="`${row.date}-${row.student}-${row.log_type}-${row.author}`"
									class="border-b border-slate-100 hover:bg-slate-50 cursor-pointer"
									@click.stop="selectStudentFromRecent(row)"
								>
									<td class="px-2 py-2 align-top whitespace-nowrap">
										{{ formatDate(row.date) }}
									</td>
									<td class="px-2 py-2 align-top whitespace-nowrap">
										{{ row.student_full_name || row.student }}
									</td>
									<td class="px-2 py-2 align-top whitespace-nowrap">
										{{ row.program || '-' }}
									</td>
									<td class="px-2 py-2 align-top whitespace-nowrap">
										{{ row.log_type }}
									</td>
									<td class="px-2 py-2 align-top" :title="stripHtml(row.content || '')">
										{{ truncate(stripHtml(row.content || '')) }}
									</td>
									<td class="px-2 py-2 align-top whitespace-nowrap">
										{{ row.author }}
									</td>
									<td class="px-2 py-2 align-top text-center">
										<span
											v-if="row.requires_follow_up"
											class="inline-flex h-4 w-4 items-center justify-center rounded-full bg-amber-100 type-badge-label text-amber-700"
										>
											Y
										</span>
									</td>
								</tr>
								<tr v-if="!recentRows.length">
									<td colspan="7" class="px-2 py-3 text-center type-empty">
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

			<AnalyticsCard
				title="Selected Student Logs"
				@expand="openTableOverlay('Selected Student Logs', studentLogs, selectedStudentLabel || filters.student)"
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
						<table class="min-w-full border-collapse type-caption text-ink/80">
							<thead>
								<tr class="border-b border-slate-200 bg-slate-50">
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Date</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Type</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Log</th>
									<th class="px-2 py-2 text-left type-label text-slate-token/70">Author</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="row in studentLogs"
									:key="`${row.date}-${row.log_type}-${row.author}`"
									class="border-b border-slate-100 hover:bg-slate-50"
								>
									<td class="px-2 py-2 align-top whitespace-nowrap">
										{{ formatDate(row.date) }}
									</td>
									<td class="px-2 py-2 align-top whitespace-nowrap">
										{{ row.log_type }}
									</td>
									<td class="px-2 py-2 align-top" :title="stripHtml(row.content || '')">
										{{ truncate(stripHtml(row.content || ''), 200) }}
									</td>
									<td class="px-2 py-2 align-top whitespace-nowrap">
										{{ row.author }}
									</td>
								</tr>
								<tr v-if="!studentLogs.length">
									<td colspan="4" class="px-2 py-3 text-center type-empty">
										No logs to show yet.
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
