<!-- ifitwala_ed/ui-spa/src/pages/staff/analytics/AttendanceAnalytics.vue -->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

import AnalyticsCard from '@/components/analytics/AnalyticsCard.vue'
import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue'
import KpiRow from '@/components/analytics/KpiRow.vue'
import StatsTile from '@/components/analytics/StatsTile.vue'
import DateRangePills from '@/components/filters/DateRangePills.vue'
import FiltersBar from '@/components/filters/FiltersBar.vue'
import { SIGNAL_ATTENDANCE_INVALIDATE, uiSignals } from '@/lib/uiSignals'
import { createAttendanceAnalyticsService } from '@/lib/services/attendance/attendanceAnalyticsService'
import { createStudentAttendanceService } from '@/lib/services/studentAttendance/studentAttendanceService'

import type {
	AttendanceBaseParams,
	AttendanceCodeUsageResponse,
	AttendanceDatePreset,
	AttendanceExceptionRow,
	AttendanceHeatmapResponse,
	AttendanceMeta,
	AttendanceMyGroupsResponse,
	AttendanceOverviewResponse,
	AttendanceRiskResponse,
	AttendanceRoleClass,
	AttendanceThresholds,
} from '@/types/contracts/attendance'
import type {
	FetchActiveProgramsResponse,
	FetchPortalStudentGroupsResponse,
	FetchSchoolFilterContextResponse,
} from '@/types/contracts/studentAttendance'

type ChartOption = Record<string, unknown>

type WindowPreset = 'term' | AttendanceDatePreset
type RiskBucket = 'critical' | 'warning' | 'ok'

const attendanceService = createStudentAttendanceService()
const analyticsService = createAttendanceAnalyticsService()

const filtersReady = ref(false)
const isLoading = ref(false)
const pageError = ref<string | null>(null)
const actionError = ref<string | null>(null)

const roleClass = ref<AttendanceRoleClass | null>(null)
const meta = ref<AttendanceMeta | null>(null)

const schools = ref<FetchSchoolFilterContextResponse['schools']>([])
const programs = ref<FetchActiveProgramsResponse>([])
const studentGroups = ref<FetchPortalStudentGroupsResponse>([])

const overview = ref<AttendanceOverviewResponse | null>(null)
const heatmap = ref<AttendanceHeatmapResponse | null>(null)
const risk = ref<AttendanceRiskResponse | null>(null)
const codeUsage = ref<AttendanceCodeUsageResponse | null>(null)
const myGroups = ref<AttendanceMyGroupsResponse | null>(null)

const contextStudent = ref<string>('')
const contextLoading = ref(false)
const contextData = ref<AttendanceRiskResponse['context_sparkline']>(null)
const selectedRiskBucket = ref<RiskBucket | null>(null)

const thresholds: AttendanceThresholds = {
	warning: 90,
	critical: 80,
}

const filters = reactive<{
	school: string | null
	program: string | null
	student_group: string | null
	whole_day: 0 | 1
	activity_only: 0 | 1
	start_date: string | null
	end_date: string | null
}>({
	school: null,
	program: null,
	student_group: null,
	whole_day: 1,
	activity_only: 0,
	start_date: null,
	end_date: null,
})

const preset = ref<WindowPreset>('term')
const presetItems: Array<{ label: string; value: WindowPreset }> = [
	{ label: 'Term', value: 'term' },
	{ label: 'Today', value: 'today' },
	{ label: '1W', value: 'last_week' },
	{ label: '2W', value: 'last_2_weeks' },
	{ label: '1M', value: 'last_month' },
	{ label: '3M', value: 'last_3_months' },
]

const isInstructor = computed(() => roleClass.value === 'instructor')
const isCounselor = computed(() => roleClass.value === 'counselor')
const isAdmin = computed(() => roleClass.value === 'admin')

const roleHeading = computed(() => {
	if (isInstructor.value) return 'Instructor Lens'
	if (isCounselor.value) return 'Counselor / Pastoral Lens'
	if (isAdmin.value) return 'Academic Admin Lens'
	return 'Role Lens'
})

const kpiItems = computed(() => {
	const kpis = overview.value?.kpis
	if (!kpis) return []
	const expected = Math.max(kpis.expected_sessions, 1)
	const absenceRate = Number(((kpis.absent_sessions / expected) * 100).toFixed(2))
	const lateRate = Number(((kpis.late_sessions / expected) * 100).toFixed(2))
	const unexplainedRate = Number(((kpis.unexplained_absent_sessions / expected) * 100).toFixed(2))
	return [
		{ id: 'attendance_rate', label: 'Attendance Rate', value: `${kpis.attendance_rate}%` },
		{ id: 'absence_rate', label: 'Absence Rate', value: `${absenceRate}%` },
		{ id: 'late_rate', label: 'Late Rate', value: `${lateRate}%` },
		{ id: 'unexplained_rate', label: 'Unexplained Rate', value: `${unexplainedRate}%` },
		{ id: 'expected_sessions', label: 'Expected Sessions', value: kpis.expected_sessions },
	]
})

const trendTone = computed<'default' | 'warning' | 'success'>(() => {
	const delta = overview.value?.trend?.delta ?? 0
	if (delta <= -2) return 'warning'
	if (delta >= 2) return 'success'
	return 'default'
})

const heatmapOption = computed<ChartOption>(() => {
	const data = heatmap.value
	if (!data || !data.cells.length) return {}

	const x = data.axis.x
	const yRaw = data.axis.y
	const xIndex = new Map(x.map((value, index) => [value, index]))
	const yIndex = new Map(yRaw.map((value, index) => [value, index]))
	const yLabels = yRaw.map((value) => (filters.whole_day === 1 ? 'Whole Day' : `Block ${value}`))

	const seriesData = data.cells
		.map((cell) => {
			const xIdx = xIndex.get(cell.x)
			const yIdx = yIndex.get(cell.y)
			if (xIdx === undefined || yIdx === undefined) return null
			const ratio = cell.expected > 0 ? Number(((cell.present / cell.expected) * 100).toFixed(2)) : 0
			return [xIdx, yIdx, ratio, cell.present, cell.expected]
		})
		.filter((row): row is [number, number, number, number, number] => !!row)

	const maxRatio = Math.max(100, ...seriesData.map((row) => row[2]))

	return {
		grid: { left: 70, right: 18, top: 24, bottom: 44 },
		xAxis: {
			type: 'category',
			data: x,
			axisLabel: {
				fontSize: 10,
				rotate: x.length > 12 ? 40 : 0,
			},
		},
		yAxis: {
			type: 'category',
			data: yLabels,
			axisLabel: { fontSize: 11 },
		},
		visualMap: {
			show: false,
			min: 0,
			max: maxRatio,
			orient: 'horizontal',
			left: 'center',
			bottom: 6,
			text: ['High', 'Low'],
			inRange: {
				color: ['#dff4ea', '#97d7b8', '#53b587', '#1f8d5b'],
			},
		},
		tooltip: { trigger: 'item' },
		series: [
			{
				type: 'heatmap',
				data: seriesData,
			},
		],
	}
})

const riskBucketsOption = computed<ChartOption>(() => {
	const source = risk.value
	if (!source) return {}
	return {
		grid: { left: 40, right: 10, top: 20, bottom: 32 },
		xAxis: {
			type: 'category',
			data: ['Critical', 'Warning', 'OK'],
		},
		yAxis: { type: 'value' },
		series: [
			{
				type: 'bar',
				data: [source.buckets.critical, source.buckets.warning, source.buckets.ok],
				cursor: 'pointer',
				itemStyle: {
					color: '#1f8d5b',
				},
			},
		],
	}
})

const methodMixOption = computed<ChartOption>(() => {
	const list = risk.value?.method_mix || []
	if (!list.length) return {}
	return {
		grid: { left: 90, right: 20, top: 16, bottom: 24 },
		xAxis: { type: 'value' },
		yAxis: {
			type: 'category',
			data: list.map((row) => row.attendance_method),
		},
		series: [
			{
				type: 'bar',
				data: list.map((row) => row.count),
				itemStyle: { color: '#246b57' },
			},
		],
	}
})

const attendanceContextOption = computed<ChartOption>(() => {
	const points = contextData.value?.attendance || []
	if (!points.length) return {}
	return {
		grid: { left: 40, right: 14, top: 20, bottom: 38 },
		xAxis: {
			type: 'category',
			data: points.map((point) => point.day),
			axisLabel: { fontSize: 10 },
		},
		yAxis: { type: 'value', max: 100 },
		series: [
			{
				type: 'line',
				smooth: true,
				data: points.map((point) => (point.expected > 0 ? Number(((point.present / point.expected) * 100).toFixed(2)) : 0)),
			},
		],
	}
})

const academicContextOption = computed<ChartOption>(() => {
	const points = contextData.value?.academic_standing || []
	if (!points.length) return {}
	return {
		grid: { left: 40, right: 14, top: 20, bottom: 38 },
		xAxis: {
			type: 'category',
			data: points.map((point) => point.day),
			axisLabel: { fontSize: 10 },
		},
		yAxis: { type: 'value' },
		series: [
			{
				type: 'line',
				smooth: true,
				data: points.map((point) => point.average_value),
			},
		],
	}
})

const behaviourContextOption = computed<ChartOption>(() => {
	const points = contextData.value?.behaviour_incidents || []
	if (!points.length) return {}
	return {
		grid: { left: 40, right: 14, top: 20, bottom: 38 },
		xAxis: {
			type: 'category',
			data: points.map((point) => point.day),
			axisLabel: { fontSize: 10 },
		},
		yAxis: { type: 'value' },
		series: [
			{
				type: 'line',
				smooth: true,
				data: points.map((point) => point.follow_up_logs),
			},
		],
	}
})

const contextStudentOptions = computed(() => {
	const options = new Map<string, string>()
	for (const row of risk.value?.top_critical || []) options.set(row.student, row.student_name)
	for (const row of risk.value?.declining_trend || []) options.set(row.student, row.student_name)
	for (const row of risk.value?.frequent_unexplained || []) options.set(row.student, row.student_name)
	return Array.from(options.entries()).map(([student, student_name]) => ({ student, student_name }))
})

const selectedRiskBucketLabel = computed(() => {
	if (selectedRiskBucket.value === 'critical') return 'Critical'
	if (selectedRiskBucket.value === 'warning') return 'Warning'
	if (selectedRiskBucket.value === 'ok') return 'OK'
	return 'Bucket'
})

const selectedRiskBucketRows = computed(() => {
	if (!selectedRiskBucket.value) return []
	let rows = risk.value?.bucket_students?.[selectedRiskBucket.value] || []
	if (!rows.length && selectedRiskBucket.value === 'critical') {
		rows = risk.value?.top_critical || []
	}
	return rows.map((row) => ({ ...row, id: row.student, name: row.student_name }))
})

const activeRiskThresholds = computed(() => risk.value?.thresholds || thresholds)

let loadRunId = 0
let reloadTimer: number | null = null
let disposeAttendanceInvalidate: (() => void) | null = null

function isoDate(value: Date): string {
	return value.toISOString().slice(0, 10)
}

function applyPreset(nextPreset: WindowPreset) {
	preset.value = nextPreset
	if (nextPreset === 'term') {
		filters.start_date = null
		filters.end_date = null
		return
	}

	const today = new Date()
	const end = new Date(today)
	const start = new Date(today)
	const days = {
		today: 0,
		last_week: 7,
		last_2_weeks: 14,
		last_month: 30,
		last_3_months: 90,
	}[nextPreset]
	start.setDate(end.getDate() - days)
	filters.start_date = isoDate(start)
	filters.end_date = isoDate(end)
}

function applyCalendarRangeChange() {
	if (filters.start_date && filters.end_date) {
		preset.value = 'term'
	}
}

function clearCalendarRange() {
	filters.start_date = null
	filters.end_date = null
}

function formatError(error: unknown): string {
	if (error instanceof Error && error.message) return error.message
	return 'Unable to load attendance analytics right now.'
}

function buildBasePayload(): Omit<AttendanceBaseParams, 'mode'> {
	const payload: Omit<AttendanceBaseParams, 'mode'> = {
		whole_day: filters.whole_day,
		activity_only: filters.activity_only,
	}

	if (filters.school) payload.school = filters.school
	if (filters.program) payload.program = filters.program
	if (filters.student_group) payload.student_group = filters.student_group
	if (filters.start_date) payload.start_date = filters.start_date
	if (filters.end_date) payload.end_date = filters.end_date
	if (!filters.start_date && !filters.end_date && preset.value !== 'term') payload.date_preset = preset.value

	return payload
}

function scheduleReload() {
	if (!filtersReady.value) return
	if (Boolean(filters.start_date) !== Boolean(filters.end_date)) {
		actionError.value = 'Select both start and end dates for a calendar range.'
		return
	}
	if (actionError.value === 'Select both start and end dates for a calendar range.') {
		actionError.value = null
	}
	if (reloadTimer) window.clearTimeout(reloadTimer)
	reloadTimer = window.setTimeout(() => {
		void reloadDashboard()
	}, 350)
}

async function loadStudentGroups() {
	actionError.value = null
	try {
		const groups = await attendanceService.fetchStudentGroups({
			school: filters.school,
			program: filters.program,
		})
		studentGroups.value = groups
		if (filters.student_group && !groups.some((group) => group.name === filters.student_group)) {
			filters.student_group = null
		}
	} catch (error) {
		studentGroups.value = []
		filters.student_group = null
		actionError.value = formatError(error)
	}
}

async function initializeFilters() {
	const schoolContext = await attendanceService.fetchSchoolContext()
	schools.value = schoolContext.schools || []
	filters.school = schoolContext.default_school || schoolContext.schools?.[0]?.name || null

	programs.value = await attendanceService.fetchPrograms()
	await loadStudentGroups()
}

async function reloadDashboard() {
	const runId = ++loadRunId
	isLoading.value = true
	pageError.value = null
	actionError.value = null
	contextData.value = null
	selectedRiskBucket.value = null

	try {
		const basePayload = buildBasePayload()
		const [overviewResponse, heatmapResponse] = await Promise.all([
			analyticsService.getOverview({ mode: 'overview', ...basePayload }),
			analyticsService.getHeatmap({
				mode: 'heatmap',
				heatmap_mode: filters.whole_day === 1 ? 'day' : 'block',
				...basePayload,
			}),
		])

		if (runId !== loadRunId) return

		overview.value = overviewResponse
		heatmap.value = heatmapResponse
		roleClass.value = overviewResponse.meta.role_class
		meta.value = overviewResponse.meta

		if (roleClass.value === 'instructor') {
			const myGroupsResponse = await analyticsService.getMyGroups({ mode: 'my_groups', ...basePayload })
			if (runId !== loadRunId) return
			myGroups.value = myGroupsResponse
			risk.value = null
			codeUsage.value = null
			return
		}

		if (roleClass.value === 'counselor') {
			const riskResponse = await analyticsService.getRisk({ mode: 'risk', ...basePayload })
			if (runId !== loadRunId) return
			risk.value = riskResponse
			myGroups.value = null
			codeUsage.value = null
			return
		}

		const [riskResponse, codeUsageResponse] = await Promise.all([
			analyticsService.getRisk({ mode: 'risk', ...basePayload }),
			analyticsService.getCodeUsage({ mode: 'code_usage', ...basePayload }),
		])
		if (runId !== loadRunId) return
		risk.value = riskResponse
		codeUsage.value = codeUsageResponse
		myGroups.value = null
	} catch (error) {
		if (runId !== loadRunId) return
		pageError.value = formatError(error)
	} finally {
		if (runId === loadRunId) {
			isLoading.value = false
		}
	}
}

async function loadContextSparkline() {
	actionError.value = null
	if (!contextStudent.value) {
		actionError.value = 'Select a student to load attendance context.'
		return
	}

	contextLoading.value = true
	try {
		const payload = buildBasePayload()
		const response = await analyticsService.getRisk({
			mode: 'risk',
			include_context: 1,
			context_student: contextStudent.value,
			...payload,
		})
		if (!response.context_sparkline) {
			contextData.value = null
			actionError.value = 'No context available for this student in your current scope.'
			return
		}
		contextData.value = response.context_sparkline
	} catch (error) {
		actionError.value = formatError(error)
	} finally {
		contextLoading.value = false
	}
}

function exceptionTone(status: AttendanceExceptionRow['status']) {
	if (status === 'Absent') return 'text-flame bg-flame/10'
	if (status === 'Late') return 'text-amber-700 bg-amber-100'
	return 'text-slate-600 bg-slate-100'
}

function openRiskBucket(bucket: RiskBucket) {
	selectedRiskBucket.value = bucket
}

function onRiskRadarClick(event: unknown) {
	const payload = event as { name?: string; dataIndex?: number } | null
	const byName = (payload?.name || '').toLowerCase()
	if (byName === 'critical') return openRiskBucket('critical')
	if (byName === 'warning') return openRiskBucket('warning')
	if (byName === 'ok') return openRiskBucket('ok')

	const byIndex = Number(payload?.dataIndex)
	if (byIndex === 0) return openRiskBucket('critical')
	if (byIndex === 1) return openRiskBucket('warning')
	if (byIndex === 2) return openRiskBucket('ok')
}

watch(
	() => [filters.school, filters.program],
	() => {
		if (!filtersReady.value) return
		void loadStudentGroups()
	}
)

watch(
	() => [
		filters.school,
		filters.program,
		filters.student_group,
		filters.whole_day,
		filters.activity_only,
		filters.start_date,
		filters.end_date,
		preset.value,
	],
	() => {
		scheduleReload()
	}
)

onMounted(async () => {
	applyPreset('term')
	try {
		await initializeFilters()
		filtersReady.value = true
		await reloadDashboard()
	} catch (error) {
		pageError.value = formatError(error)
	}

	disposeAttendanceInvalidate = uiSignals.subscribe(SIGNAL_ATTENDANCE_INVALIDATE, () => {
		scheduleReload()
	})
})

onBeforeUnmount(() => {
	if (reloadTimer) window.clearTimeout(reloadTimer)
	if (disposeAttendanceInvalidate) disposeAttendanceInvalidate()
})
</script>

<template>
	<div class="analytics-shell attendance-analytics-shell">
		<header class="flex flex-wrap items-end justify-between gap-3">
			<div>
				<h1 class="type-h2 text-canopy">Attendance Analytics</h1>
				<p class="type-body mt-1 text-slate-token/80">
					Pattern-first attendance intelligence with role-aware framing.
				</p>
			</div>
			<StatsTile
				:label="roleHeading"
				:value="meta?.window_source || 'window'"
				tone="info"
			/>
		</header>

		<FiltersBar>
			<div class="flex w-48 flex-col gap-1">
				<label class="type-label">School</label>
				<select v-model="filters.school" class="h-9 rounded-md border border-slate-200 px-2" :disabled="isLoading">
					<option v-for="school in schools" :key="school.name" :value="school.name">
						{{ school.school_name || school.name }}
					</option>
				</select>
			</div>

			<div class="flex w-48 flex-col gap-1">
				<label class="type-label">Program</label>
				<select v-model="filters.program" class="h-9 rounded-md border border-slate-200 px-2" :disabled="isLoading">
					<option :value="null">All</option>
					<option v-for="program in programs" :key="program.name" :value="program.name">
						{{ program.program_name || program.name }}
					</option>
				</select>
			</div>

			<div class="flex w-48 flex-col gap-1">
				<label class="type-label">Student Group</label>
				<select v-model="filters.student_group" class="h-9 rounded-md border border-slate-200 px-2" :disabled="isLoading">
					<option :value="null">All</option>
					<option v-for="group in studentGroups" :key="group.name" :value="group.name">
						{{ group.student_group_name || group.name }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Window</label>
				<DateRangePills :model-value="preset" :items="presetItems" size="sm" @update:model-value="applyPreset" />
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">From Date</label>
				<input
					v-model="filters.start_date"
					type="date"
					class="h-9 rounded-md border border-slate-200 px-2 text-sm"
					@change="applyCalendarRangeChange"
				/>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">To Date</label>
				<input
					v-model="filters.end_date"
					type="date"
					class="h-9 rounded-md border border-slate-200 px-2 text-sm"
					@change="applyCalendarRangeChange"
				/>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Calendar Range</label>
				<button
					type="button"
					class="h-9 rounded-md border border-slate-200 px-3 text-xs text-slate-700 hover:bg-slate-50"
					@click="clearCalendarRange"
				>
					Clear Custom Range
				</button>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Attendance Mode</label>
				<div class="flex items-center gap-2">
					<button
						type="button"
						class="rounded-lg border px-3 py-1.5 text-xs"
						:class="filters.whole_day === 1 ? 'border-leaf bg-leaf/10 text-leaf' : 'border-slate-200 text-slate-600'"
						@click="filters.whole_day = 1"
					>
						Whole Day
					</button>
					<button
						type="button"
						class="rounded-lg border px-3 py-1.5 text-xs"
						:class="filters.whole_day === 0 ? 'border-canopy bg-canopy/10 text-canopy' : 'border-slate-200 text-slate-600'"
						@click="filters.whole_day = 0"
					>
						By Block
					</button>
				</div>
			</div>

			<label class="mt-5 inline-flex items-center gap-2 text-xs text-slate-700">
				<input v-model="filters.activity_only" :true-value="1" :false-value="0" type="checkbox" />
				Activities Lens
			</label>
		</FiltersBar>

		<div v-if="pageError" class="rounded-xl border border-flame/30 bg-flame/10 px-4 py-3 text-sm text-flame">
			{{ pageError }}
		</div>

		<div v-if="actionError" class="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
			{{ actionError }}
		</div>

		<section class="analytics-grid attendance-analytics-grid">
			<AnalyticsCard title="Universal KPIs" :interactive="false" class="analytics-card--wide">
				<template #body>
					<KpiRow :items="kpiItems" :clickable="false" />
					<div class="mt-3 flex flex-wrap items-center gap-2">
						<StatsTile
							label="Trend vs previous window"
							:value="overview?.trend?.delta ?? 0"
							:tone="trendTone"
						/>
						<StatsTile
							label="Previous attendance rate"
							:value="overview?.trend?.previous_rate ?? 0"
						/>
					</div>
				</template>
			</AnalyticsCard>

			<AnalyticsCard title="Block / Day Integrity" :interactive="false" class="analytics-card--wide">
				<template #body>
					<AnalyticsChart v-if="Object.keys(heatmapOption).length" :option="heatmapOption" />
					<p v-else class="analytics-empty">No attendance cells for the selected scope.</p>
				</template>
			</AnalyticsCard>
		</section>

		<section v-if="isInstructor" class="space-y-4">
			<header>
				<h2 class="type-h3 text-canopy">Teachers: This Week Focus</h2>
				<p class="type-body mt-1 text-slate-token/75">Patterns, exceptions, and turnaround signals for your groups.</p>
			</header>

			<div class="analytics-grid attendance-analytics-grid">
				<AnalyticsCard title="My Groups Attendance Snapshot" :interactive="false" class="analytics-card--wide">
					<template #body>
						<div v-if="myGroups?.groups?.length" class="grid gap-3 md:grid-cols-2">
							<article v-for="group in myGroups.groups" :key="group.student_group" class="rounded-xl border border-slate-200 bg-surface-soft px-3 py-3">
								<div class="flex items-center justify-between">
									<p class="type-label">{{ group.student_group_abbreviation || group.student_group_name }}</p>
									<span class="text-[11px] text-slate-500">{{ group.group_based_on || 'Group' }}</span>
								</div>
								<div class="mt-2 grid grid-cols-4 gap-2 text-xs text-slate-700">
									<div><p class="text-slate-500">Expected</p><p class="font-semibold">{{ group.expected }}</p></div>
									<div><p class="text-slate-500">Present</p><p class="font-semibold">{{ group.present }}</p></div>
									<div><p class="text-slate-500">Absent</p><p class="font-semibold">{{ group.absent }}</p></div>
									<div><p class="text-slate-500">Late</p><p class="font-semibold">{{ group.late }}</p></div>
								</div>
							</article>
						</div>
						<p v-else class="analytics-empty">No instructor groups in this scope.</p>
					</template>
				</AnalyticsCard>

				<AnalyticsCard title="Students with Emerging Patterns" :interactive="false">
					<template #body>
						<div v-if="myGroups?.emerging_patterns?.length" class="max-h-72 overflow-auto">
							<table class="w-full text-left text-xs">
								<thead class="text-slate-500">
									<tr>
										<th class="py-1">Student</th>
										<th class="py-1">Abs</th>
										<th class="py-1">Late</th>
										<th class="py-1">Block1</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="row in myGroups.emerging_patterns.slice(0, 40)" :key="row.student" class="border-t border-slate-100">
										<td class="py-1.5">{{ row.student_name }}</td>
										<td class="py-1.5">{{ row.absent_count }}</td>
										<td class="py-1.5">{{ row.late_count }}</td>
										<td class="py-1.5">{{ row.pattern_absent_block_1 }}</td>
									</tr>
								</tbody>
							</table>
						</div>
						<p v-else class="analytics-empty">No emerging risk pattern in this window.</p>
					</template>
				</AnalyticsCard>

				<AnalyticsCard title="Today / This Week Exceptions" :interactive="false">
					<template #body>
						<ul v-if="myGroups?.exceptions?.length" class="max-h-72 space-y-2 overflow-auto text-xs">
							<li v-for="item in myGroups.exceptions.slice(0, 40)" :key="`${item.student_group}:${item.student}`" class="rounded-lg border border-slate-200 px-2 py-2">
								<div class="flex items-center justify-between gap-2">
									<span class="font-medium text-ink">{{ item.student_name }}</span>
									<span :class="['rounded-full px-2 py-0.5 text-[11px] font-medium', exceptionTone(item.status)]">{{ item.status }}</span>
								</div>
								<p class="mt-1 text-slate-500">{{ item.student_group_abbreviation }}</p>
							</li>
						</ul>
						<p v-else class="analytics-empty">No missing, absent, or late exceptions today.</p>
					</template>
				</AnalyticsCard>

				<AnalyticsCard title="Back on Track" :interactive="false">
					<template #body>
						<ul v-if="myGroups?.improving_trends?.length" class="space-y-2 text-xs">
							<li v-for="item in myGroups.improving_trends.slice(0, 20)" :key="item.student" class="rounded-lg border border-leaf/30 bg-leaf/10 px-2 py-2">
								<p class="font-medium text-leaf">{{ item.student_name }}</p>
								<p class="mt-1 text-slate-700">{{ item.previous_rate }}% -> {{ item.current_rate }}% ({{ item.delta }} pts)</p>
							</li>
						</ul>
						<p v-else class="analytics-empty">No turnaround student in this window.</p>
					</template>
				</AnalyticsCard>
			</div>
		</section>

		<section v-if="isCounselor || isAdmin" class="space-y-4">
			<header>
				<h2 class="type-h3 text-canopy">Risk & Wellbeing Signals</h2>
				<p class="type-body mt-1 text-slate-token/75">Decline detection, unexplained absences, and positive turnaround.</p>
			</header>

			<div class="analytics-grid attendance-analytics-grid">
				<AnalyticsCard title="Chronic Absence Radar" :interactive="false">
					<template #body>
						<AnalyticsChart v-if="Object.keys(riskBucketsOption).length" :option="riskBucketsOption" @click="onRiskRadarClick" />
						<p v-if="Object.keys(riskBucketsOption).length" class="mt-2 text-[11px] text-slate-500">
							Click a bucket bar to show student details.
						</p>
						<details v-if="Object.keys(riskBucketsOption).length" class="mt-2 rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2 text-xs text-slate-700">
							<summary class="cursor-pointer font-medium text-slate-800">
								What do these buckets mean?
							</summary>
							<ul class="mt-2 space-y-1">
								<li>Critical: attendance rate &lt; {{ activeRiskThresholds.critical }}%</li>
								<li>Warning: attendance rate &gt;= {{ activeRiskThresholds.critical }}% and &lt; {{ activeRiskThresholds.warning }}%</li>
								<li>OK: attendance rate &gt;= {{ activeRiskThresholds.warning }}%</li>
							</ul>
							<p class="mt-2 text-[11px] text-slate-500">
								Only students with expected sessions in the selected window are bucketed.
							</p>
						</details>
						<p v-else class="analytics-empty">No risk distribution available for this scope.</p>
					</template>
				</AnalyticsCard>

				<template v-if="isCounselor">
					<AnalyticsCard title="Top Critical" :interactive="false">
						<template #body>
							<ul v-if="risk?.top_critical?.length" class="max-h-72 space-y-2 overflow-auto text-xs">
								<li v-for="item in risk.top_critical.slice(0, 30)" :key="item.student" class="rounded-lg border border-slate-200 px-2 py-2">
									<p class="font-medium text-ink">{{ item.student_name }}</p>
									<p class="mt-1 text-slate-600">Rate {{ item.attendance_rate }}% • Abs {{ item.absent_count }} • Late {{ item.late_count }}</p>
								</li>
							</ul>
							<p v-else class="analytics-empty">No critical student in this window.</p>
						</template>
					</AnalyticsCard>

					<AnalyticsCard title="Block vs Day Mismatch" :interactive="false">
						<template #body>
							<ul v-if="risk?.mismatch_students?.length" class="max-h-72 space-y-2 overflow-auto text-xs">
								<li v-for="item in risk.mismatch_students.slice(0, 30)" :key="item.student" class="rounded-lg border border-slate-200 px-2 py-2">
									<p class="font-medium text-ink">{{ item.student_name }}</p>
									<p class="mt-1 text-slate-600">{{ item.mismatch_days }} mismatch day(s)</p>
								</li>
							</ul>
							<p v-else class="analytics-empty">No day/block mismatch detected.</p>
						</template>
					</AnalyticsCard>

					<AnalyticsCard title="Back on Track" :interactive="false">
						<template #body>
							<ul v-if="risk?.improving_trends?.length" class="space-y-2 text-xs">
								<li v-for="item in risk.improving_trends.slice(0, 20)" :key="item.student" class="rounded-lg border border-leaf/30 bg-leaf/10 px-2 py-2">
									<p class="font-medium text-leaf">{{ item.student_name }}</p>
									<p class="mt-1 text-slate-700">{{ item.previous_rate }}% -> {{ item.current_rate }}% ({{ item.delta }} pts)</p>
								</li>
							</ul>
							<p v-else class="analytics-empty">No improving trend in this window.</p>
						</template>
					</AnalyticsCard>
				</template>

				<AnalyticsCard v-else title="Student Details" :interactive="false">
					<template #body>
						<div v-if="selectedRiskBucketRows.length" class="space-y-2 text-xs">
							<p class="type-label text-slate-600">{{ selectedRiskBucketLabel }} bucket preview</p>
							<ul class="max-h-48 space-y-2 overflow-auto">
								<li
									v-for="item in selectedRiskBucketRows.slice(0, 8)"
									:key="item.student"
									class="rounded-lg border border-slate-200 px-2 py-2"
								>
									<p class="font-medium text-ink">{{ item.student_name }}</p>
									<p class="mt-1 text-slate-600">Rate {{ item.attendance_rate }}% • Abs {{ item.absent_count }} • Late {{ item.late_count }}</p>
								</li>
							</ul>
						</div>
						<p v-else-if="selectedRiskBucket" class="analytics-empty">
							No students found in the {{ selectedRiskBucketLabel }} bucket for current filters.
						</p>
						<p v-else class="analytics-empty">Click a radar bar to inspect student names for that bucket.</p>
					</template>
				</AnalyticsCard>
			</div>

			<AnalyticsCard v-if="isCounselor" title="Context Sparkline" :interactive="false" class="analytics-card--wide">
				<template #body>
					<div class="flex flex-wrap items-end gap-3">
						<div class="flex min-w-64 flex-col gap-1">
							<label class="type-label">Risk Student</label>
							<select v-model="contextStudent" class="h-9 rounded-md border border-slate-200 px-2">
								<option value="">Select student</option>
								<option v-for="item in contextStudentOptions" :key="item.student" :value="item.student">
									{{ item.student_name }}
								</option>
							</select>
						</div>
						<button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-700" :disabled="contextLoading" @click="loadContextSparkline">
							{{ contextLoading ? 'Loading context...' : 'Load Context' }}
						</button>
					</div>

					<div v-if="contextData" class="mt-4 grid gap-4 md:grid-cols-3">
						<div>
							<p class="type-label mb-1">Attendance Signal</p>
							<AnalyticsChart v-if="Object.keys(attendanceContextOption).length" :option="attendanceContextOption" />
							<p v-else class="analytics-empty">No attendance points.</p>
						</div>
						<div>
							<p class="type-label mb-1">Academic Standing (Task Outcomes)</p>
							<AnalyticsChart v-if="Object.keys(academicContextOption).length" :option="academicContextOption" />
							<p v-else class="analytics-empty">No academic points.</p>
						</div>
						<div>
							<p class="type-label mb-1">Behavior / Follow-Up (Student Logs)</p>
							<AnalyticsChart v-if="Object.keys(behaviourContextOption).length" :option="behaviourContextOption" />
							<p v-else class="analytics-empty">No behavior points.</p>
						</div>
					</div>
				</template>
			</AnalyticsCard>
		</section>

		<section v-if="isAdmin" class="space-y-4">
			<header>
				<h2 class="type-h3 text-canopy">Operational Compliance</h2>
				<p class="type-body mt-1 text-slate-token/75">School/program health, attendance method reliability, and code governance.</p>
			</header>

			<div class="analytics-grid attendance-analytics-grid">
				<AnalyticsCard title="Attendance Compliance Overview" :interactive="false" class="analytics-card--wide">
					<template #body>
						<div v-if="risk?.compliance_by_scope?.length" class="max-h-72 overflow-auto">
							<table class="w-full text-left text-xs">
								<thead class="text-slate-500">
									<tr>
										<th class="py-1">School</th>
										<th class="py-1">Program</th>
										<th class="py-1">Expected</th>
										<th class="py-1">Present</th>
										<th class="py-1">Rate</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="row in risk.compliance_by_scope" :key="`${row.school}:${row.program}`" class="border-t border-slate-100">
										<td class="py-1.5">{{ row.school_label }}</td>
										<td class="py-1.5">{{ row.program || 'General' }}</td>
										<td class="py-1.5">{{ row.expected_sessions }}</td>
										<td class="py-1.5">{{ row.present_sessions }}</td>
										<td class="py-1.5">{{ row.attendance_rate }}%</td>
									</tr>
								</tbody>
							</table>
						</div>
						<p v-else class="analytics-empty">No compliance rows in this window.</p>
					</template>
				</AnalyticsCard>

				<AnalyticsCard title="Attendance Method Mix" :interactive="false">
					<template #body>
						<AnalyticsChart v-if="Object.keys(methodMixOption).length" :option="methodMixOption" />
						<p v-else class="analytics-empty">No method mix available.</p>
					</template>
				</AnalyticsCard>

				<AnalyticsCard title="Codes Usage Audit" :interactive="false">
					<template #body>
						<div v-if="codeUsage?.codes?.length" class="max-h-72 overflow-auto">
							<table class="w-full text-left text-xs">
								<thead class="text-slate-500">
									<tr>
										<th class="py-1">Code</th>
										<th class="py-1">Count</th>
										<th class="py-1">Share</th>
										<th class="py-1">Present</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="row in codeUsage.codes.slice(0, 80)" :key="row.attendance_code" class="border-t border-slate-100">
										<td class="py-1.5">{{ row.attendance_code_name }}</td>
										<td class="py-1.5">{{ row.count }}</td>
										<td class="py-1.5">{{ row.usage_share }}%</td>
										<td class="py-1.5">{{ row.count_as_present ? 'Yes' : 'No' }}</td>
									</tr>
								</tbody>
							</table>
						</div>
						<p v-else class="analytics-empty">No code usage rows in this window.</p>
					</template>
				</AnalyticsCard>
			</div>
			</section>

		<p v-if="isLoading" class="analytics-empty">Refreshing attendance analytics...</p>
	</div>
</template>

<style scoped>
.attendance-analytics-shell {
	max-width: none;
}

.attendance-analytics-grid {
	grid-template-columns: minmax(0, 1fr);
}

@media (min-width: 768px) {
	.attendance-analytics-grid {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
}
</style>
