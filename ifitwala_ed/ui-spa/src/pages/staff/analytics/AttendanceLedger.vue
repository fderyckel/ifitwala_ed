<!-- ifitwala_ed/ui-spa/src/pages/staff/analytics/AttendanceLedger.vue -->
<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

import AnalyticsCard from '@/components/analytics/AnalyticsCard.vue'
import DateRangePills from '@/components/filters/DateRangePills.vue'
import FiltersBar from '@/components/filters/FiltersBar.vue'
import { createAttendanceAnalyticsService } from '@/lib/services/attendance/attendanceAnalyticsService'
import { createStudentAttendanceService } from '@/lib/services/studentAttendance/studentAttendanceService'

import type {
	AttendanceDatePreset,
	AttendanceLedgerParams,
	AttendanceLedgerColumn,
	AttendanceLedgerResponse,
} from '@/types/contracts/attendance'
import type {
	FetchActiveProgramsResponse,
	FetchPortalAcademicYearsResponse,
	FetchPortalStudentGroupsResponse,
	FetchPortalTermsResponse,
	FetchSchoolFilterContextResponse,
} from '@/types/contracts/studentAttendance'

type WindowPreset = 'term' | AttendanceDatePreset
type SortOrder = 'asc' | 'desc'

const attendanceService = createStudentAttendanceService()
const analyticsService = createAttendanceAnalyticsService()

const filtersReady = ref(false)
const isLoading = ref(false)
const pageError = ref<string | null>(null)
const actionError = ref<string | null>(null)

const schools = ref<FetchSchoolFilterContextResponse['schools']>([])
const programs = ref<FetchActiveProgramsResponse>([])
const studentGroups = ref<FetchPortalStudentGroupsResponse>([])
const academicYears = ref<FetchPortalAcademicYearsResponse>([])
const terms = ref<FetchPortalTermsResponse>([])

const ledger = ref<AttendanceLedgerResponse | null>(null)
const preset = ref<WindowPreset>('term')
const sortBy = ref<string>('student_label')
const sortOrder = ref<SortOrder>('asc')
const page = ref(1)
const pageLength = ref(80)

const filters = reactive<{
	school: string | null
	academic_year: string | null
	term: string | null
	program: string | null
	student_group: string | null
	start_date: string | null
	end_date: string | null
	whole_day: 0 | 1
	course: string
	instructor: string
	student: string
	attendance_code: string | null
}>({
	school: null,
	academic_year: null,
	term: null,
	program: null,
	student_group: null,
	start_date: null,
	end_date: null,
	whole_day: 1,
	course: '',
	instructor: '',
	student: '',
	attendance_code: null,
})

const presetItems: Array<{ label: string; value: WindowPreset }> = [
	{ label: 'Term', value: 'term' },
	{ label: 'Today', value: 'today' },
	{ label: '1W', value: 'last_week' },
	{ label: '2W', value: 'last_2_weeks' },
	{ label: '1M', value: 'last_month' },
	{ label: '3M', value: 'last_3_months' },
]

const pageLengthOptions = [50, 80, 120, 200]

const rows = computed(() => ledger.value?.rows || [])
const columns = computed<AttendanceLedgerColumn[]>(() => ledger.value?.columns || [])
const totalPages = computed(() => ledger.value?.pagination?.total_pages || 1)
const totalRows = computed(() => ledger.value?.pagination?.total_rows || 0)

const codeFilterOptions = computed(() => ledger.value?.codes || [])
const courseOptions = computed(() => ledger.value?.filter_options?.courses || [])
const instructorOptions = computed(() => ledger.value?.filter_options?.instructors || [])
const studentOptions = computed(() => ledger.value?.filter_options?.students || [])

let loadRunId = 0
let reloadTimer: number | null = null

function isoDate(value: Date): string {
	return value.toISOString().slice(0, 10)
}

function formatError(error: unknown): string {
	if (error instanceof Error && error.message) return error.message
	return 'Unable to load attendance ledger right now.'
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

function buildPayload(): AttendanceLedgerParams {
	const payload: AttendanceLedgerParams = {
		mode: 'ledger',
		whole_day: filters.whole_day,
		page: page.value,
		page_length: pageLength.value,
		sort_by: sortBy.value,
		sort_order: sortOrder.value,
	}

	if (filters.school) payload.school = filters.school
	if (filters.academic_year) payload.academic_year = filters.academic_year
	if (filters.term) payload.term = filters.term
	if (filters.program) payload.program = filters.program
	if (filters.student_group) payload.student_group = filters.student_group
	if (filters.start_date) payload.start_date = filters.start_date
	if (filters.end_date) payload.end_date = filters.end_date
	if (!filters.start_date && !filters.end_date && preset.value !== 'term') payload.date_preset = preset.value
	if (filters.course.trim()) payload.course = filters.course.trim()
	if (filters.instructor.trim()) payload.instructor = filters.instructor.trim()
	if (filters.student.trim()) payload.student = filters.student.trim()
	if (filters.attendance_code) payload.attendance_code = filters.attendance_code

	return payload
}

function csvEscape(value: unknown): string {
	if (value === null || value === undefined) return ''
	const text = String(value)
	return `"${text.replace(/"/g, '""')}"`
}

function exportCurrentSliceCsv() {
	if (!rows.value.length || !columns.value.length) {
		actionError.value = 'No ledger rows to export for current filters.'
		return
	}

	const header = columns.value.map((column) => csvEscape(column.label)).join(',')
	const body = rows.value
		.map((row) =>
			columns.value
				.map((column) => {
					const raw = row[column.fieldname]
					if (column.fieldname === 'percentage_present' && raw !== null && raw !== undefined && raw !== '') {
						return csvEscape(`${raw}%`)
					}
					return csvEscape(raw)
				})
				.join(',')
		)
		.join('\n')
	const csv = `${header}\n${body}`
	const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
	const url = URL.createObjectURL(blob)
	const anchor = document.createElement('a')
	anchor.href = url
	anchor.download = `attendance_ledger_${new Date().toISOString().slice(0, 10)}.csv`
	anchor.click()
	URL.revokeObjectURL(url)
}

function toggleSort(fieldname: string) {
	if (!fieldname) return
	if (sortBy.value === fieldname) {
		sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
	} else {
		sortBy.value = fieldname
		sortOrder.value = 'asc'
	}
	page.value = 1
	scheduleReload()
}

function scheduleReload() {
	if (!filtersReady.value) return
	if (!filters.academic_year && academicYears.value.length) {
		actionError.value = 'Academic Year is required for the ledger.'
		return
	}
	if (Boolean(filters.start_date) !== Boolean(filters.end_date)) {
		actionError.value = 'Select both start and end dates for a calendar range.'
		return
	}
	if (
		actionError.value === 'Academic Year is required for the ledger.' ||
		actionError.value === 'Select both start and end dates for a calendar range.'
	) {
		actionError.value = null
	}
	if (reloadTimer) window.clearTimeout(reloadTimer)
	reloadTimer = window.setTimeout(() => {
		void reloadLedger()
	}, 350)
}

async function loadStudentGroups() {
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

async function loadAcademicYears() {
	try {
		let years = await attendanceService.fetchAcademicYears({ school: filters.school })
		if (!years.length) {
			const groups = studentGroups.value.length
				? studentGroups.value
				: await attendanceService.fetchStudentGroups({
					school: filters.school,
					program: filters.program,
				})
			if (!studentGroups.value.length && groups.length) {
				studentGroups.value = groups
			}
			const derivedYears = Array.from(
				new Set(
					groups
						.map((group) => group.academic_year)
						.filter((value): value is string => typeof value === 'string' && value.trim().length > 0),
				),
			).sort((left, right) => right.localeCompare(left))
			years = derivedYears.map((name) => ({ name }))
		}
		academicYears.value = years
		if (filters.academic_year && !years.some((year) => year.name === filters.academic_year)) {
			filters.academic_year = years[0]?.name || null
		}
		if (!filters.academic_year) {
			filters.academic_year = years[0]?.name || null
		}
	} catch (error) {
		academicYears.value = []
		filters.academic_year = null
		actionError.value = formatError(error)
	}
}

async function loadTerms() {
	try {
		const values = await attendanceService.fetchTerms({
			school: filters.school,
			academic_year: filters.academic_year,
		})
		terms.value = values
		if (filters.term && !values.some((term) => term.name === filters.term)) {
			filters.term = null
		}
	} catch (error) {
		terms.value = []
		filters.term = null
		actionError.value = formatError(error)
	}
}

async function initializeFilters() {
	const schoolContext = await attendanceService.fetchSchoolContext()
	schools.value = schoolContext.schools || []
	filters.school = schoolContext.default_school || schoolContext.schools?.[0]?.name || null

	programs.value = await attendanceService.fetchPrograms()
	await loadAcademicYears()
	await loadTerms()
	await loadStudentGroups()
}

async function reloadLedger() {
	const runId = ++loadRunId
	isLoading.value = true
	pageError.value = null
	actionError.value = null

	try {
		const payload = buildPayload()
		const response = await analyticsService.getLedger(payload)
		if (runId !== loadRunId) return
		ledger.value = response

		const returnedTotalPages = response.pagination?.total_pages || 1
		if (page.value > returnedTotalPages) {
			page.value = returnedTotalPages
		}
	} catch (error) {
		if (runId !== loadRunId) return
		pageError.value = formatError(error)
	} finally {
		if (runId === loadRunId) {
			isLoading.value = false
		}
	}
}

watch(
	() => filters.school,
	async () => {
		if (!filtersReady.value) return
		filters.term = null
		filters.student_group = null
		page.value = 1
		await loadAcademicYears()
		await loadTerms()
		await loadStudentGroups()
		scheduleReload()
	}
)

watch(
	() => filters.academic_year,
	async () => {
		if (!filtersReady.value) return
		filters.term = null
		page.value = 1
		await loadTerms()
		scheduleReload()
	}
)

watch(
	() => filters.program,
	async () => {
		if (!filtersReady.value) return
		filters.student_group = null
		page.value = 1
		await loadStudentGroups()
		scheduleReload()
	}
)

watch(
	() => [
		filters.term,
		filters.student_group,
		filters.start_date,
		filters.end_date,
		filters.whole_day,
		filters.course,
		filters.instructor,
		filters.student,
		filters.attendance_code,
		preset.value,
	],
	() => {
		page.value = 1
		scheduleReload()
	}
)

watch(
	() => [page.value, pageLength.value, sortBy.value, sortOrder.value],
	() => {
		scheduleReload()
	}
)

onMounted(async () => {
	applyPreset('term')
	try {
		await initializeFilters()
		filtersReady.value = true
		await reloadLedger()
	} catch (error) {
		pageError.value = formatError(error)
	}
})
</script>

<template>
	<div class="analytics-shell attendance-ledger-shell">
		<header class="flex flex-wrap items-end justify-between gap-3">
			<div>
				<h1 class="type-h2 text-canopy">Attendance Ledger</h1>
				<p class="type-body mt-1 text-slate-token/80">
					Desk-equivalent attendance reporting for student-level code audits and operational follow-up.
				</p>
			</div>
		</header>

		<FiltersBar>
			<div class="flex w-44 flex-col gap-1">
				<label class="type-label">School</label>
				<select v-model="filters.school" class="h-9 rounded-md border border-slate-200 px-2 text-sm">
					<option v-for="school in schools" :key="school.name" :value="school.name">
						{{ school.school_name || school.name }}
					</option>
				</select>
			</div>

			<div class="flex w-44 flex-col gap-1">
				<label class="type-label">Academic Year</label>
				<select v-model="filters.academic_year" class="h-9 rounded-md border border-slate-200 px-2 text-sm">
					<option :value="null">Select</option>
					<option v-for="year in academicYears" :key="year.name" :value="year.name">
						{{ year.name }}
					</option>
				</select>
			</div>

			<div class="flex w-44 flex-col gap-1">
				<label class="type-label">Term</label>
				<select v-model="filters.term" class="h-9 rounded-md border border-slate-200 px-2 text-sm">
					<option :value="null">All</option>
					<option v-for="term in terms" :key="term.name" :value="term.name">
						{{ term.name }}
					</option>
				</select>
			</div>

			<div class="flex w-44 flex-col gap-1">
				<label class="type-label">Program</label>
				<select v-model="filters.program" class="h-9 rounded-md border border-slate-200 px-2 text-sm">
					<option :value="null">All</option>
					<option v-for="program in programs" :key="program.name" :value="program.name">
						{{ program.program_name || program.name }}
					</option>
				</select>
			</div>

			<div class="flex w-44 flex-col gap-1">
				<label class="type-label">Student Group</label>
				<select v-model="filters.student_group" class="h-9 rounded-md border border-slate-200 px-2 text-sm">
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

			<div class="flex w-40 flex-col gap-1">
				<label class="type-label">Student</label>
				<input
					v-model="filters.student"
					list="attendance-ledger-student-options"
					type="text"
					class="h-9 rounded-md border border-slate-200 px-2 text-sm"
					placeholder="Student ID"
				/>
				<datalist id="attendance-ledger-student-options">
					<option v-for="student in studentOptions" :key="student.student" :value="student.student">
						{{ student.student_name }}
					</option>
				</datalist>
			</div>

			<div class="flex w-40 flex-col gap-1">
				<label class="type-label">Instructor</label>
				<input
					v-model="filters.instructor"
					list="attendance-ledger-instructor-options"
					type="text"
					class="h-9 rounded-md border border-slate-200 px-2 text-sm"
					placeholder="Instructor ID"
				/>
				<datalist id="attendance-ledger-instructor-options">
					<option v-for="instructor in instructorOptions" :key="instructor" :value="instructor" />
				</datalist>
			</div>

			<div class="flex w-40 flex-col gap-1">
				<label class="type-label">Course</label>
				<input
					v-model="filters.course"
					list="attendance-ledger-course-options"
					type="text"
					class="h-9 rounded-md border border-slate-200 px-2 text-sm"
					placeholder="Course ID"
					:disabled="filters.whole_day === 1"
				/>
				<datalist id="attendance-ledger-course-options">
					<option v-for="courseOption in courseOptions" :key="courseOption" :value="courseOption" />
				</datalist>
			</div>

			<div class="flex w-40 flex-col gap-1">
				<label class="type-label">Attendance Code</label>
				<select v-model="filters.attendance_code" class="h-9 rounded-md border border-slate-200 px-2 text-sm">
					<option :value="null">All</option>
					<option v-for="code in codeFilterOptions" :key="code.attendance_code" :value="code.attendance_code">
						{{ code.attendance_code }} - {{ code.attendance_code_name }}
					</option>
				</select>
			</div>
		</FiltersBar>

		<div v-if="pageError" class="rounded-xl border border-flame/30 bg-flame/10 px-4 py-3 text-sm text-flame">
			{{ pageError }}
		</div>

		<div v-if="actionError" class="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
			{{ actionError }}
		</div>

		<section class="analytics-grid attendance-ledger-grid">
			<AnalyticsCard title="Attendance Ledger (Grouped View)" :interactive="false" class="analytics-card--wide">
				<template #body>
					<div class="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
						<p>
							{{ totalRows }} grouped row(s)
						</p>
						<div class="flex items-center gap-2">
							<button
								type="button"
								class="rounded-md border border-slate-200 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
								@click="exportCurrentSliceCsv"
							>
								Export CSV
							</button>
							<label class="type-label">Rows per page</label>
							<select v-model.number="pageLength" class="h-8 rounded-md border border-slate-200 px-2">
								<option v-for="size in pageLengthOptions" :key="size" :value="size">{{ size }}</option>
							</select>
						</div>
					</div>

					<div class="mt-3 overflow-auto">
						<table class="w-full min-w-[980px] text-left text-xs">
							<thead class="text-slate-500">
								<tr>
									<th
										v-for="(col, colIndex) in columns"
										:key="col.fieldname"
										:class="[
											'whitespace-nowrap border-b border-slate-200 py-2 pr-3',
											colIndex === 0 ? 'ledger-sticky-col ledger-sticky-col--first' : '',
											colIndex === 1 ? 'ledger-sticky-col ledger-sticky-col--second' : '',
										]"
									>
										<button
											type="button"
											class="inline-flex items-center gap-1 text-left hover:text-slate-700"
											@click="toggleSort(col.fieldname)"
										>
											<span>{{ col.label }}</span>
											<span v-if="sortBy === col.fieldname">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
										</button>
									</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="(row, rowIndex) in rows" :key="`${row.student || 'row'}:${rowIndex}`" class="border-b border-slate-100">
									<td
										v-for="(col, colIndex) in columns"
										:key="`${col.fieldname}:${rowIndex}`"
										:class="[
											'py-2 pr-3 align-top',
											colIndex === 0 ? 'ledger-sticky-col ledger-sticky-col--first' : '',
											colIndex === 1 ? 'ledger-sticky-col ledger-sticky-col--second' : '',
										]"
									>
										<a
											v-if="col.fieldname === 'student_label' && row.student"
											class="text-canopy hover:underline"
											:href="`/app/student/${row.student}`"
											target="_blank"
											rel="noopener noreferrer"
										>
											{{ row[col.fieldname] }}
										</a>
										<span v-else-if="col.fieldname === 'percentage_present'" :class="[
											'rounded-full px-2 py-0.5 text-[11px] font-medium',
											Number(row[col.fieldname] || 0) >= 95 ? 'bg-leaf/15 text-leaf' : Number(row[col.fieldname] || 0) < 75 ? 'bg-flame/15 text-flame' : 'bg-amber-100 text-amber-700',
										]">
											{{ row[col.fieldname] }}%
										</span>
										<span v-else>{{ row[col.fieldname] }}</span>
									</td>
								</tr>
								<tr v-if="!rows.length">
									<td :colspan="Math.max(columns.length, 1)" class="py-6 text-center text-slate-400">
										No attendance ledger rows match these filters.
									</td>
								</tr>
							</tbody>
						</table>
					</div>

					<div class="mt-3 flex flex-wrap items-center justify-between gap-3">
						<p class="text-xs text-slate-500">
							Page {{ page }} of {{ totalPages }}
						</p>
						<div class="flex items-center gap-2">
							<button
								type="button"
								class="rounded-md border border-slate-200 px-3 py-1.5 text-xs text-slate-700 disabled:opacity-40"
								:disabled="page <= 1 || isLoading"
								@click="page = Math.max(page - 1, 1)"
							>
								Previous
							</button>
							<button
								type="button"
								class="rounded-md border border-slate-200 px-3 py-1.5 text-xs text-slate-700 disabled:opacity-40"
								:disabled="page >= totalPages || isLoading"
								@click="page = Math.min(page + 1, totalPages)"
							>
								Next
							</button>
						</div>
					</div>
				</template>
			</AnalyticsCard>

			<AnalyticsCard title="Slice Summary" :interactive="false">
				<template #body>
					<div class="space-y-2 text-xs text-slate-700">
						<p><span class="font-medium text-slate-800">Raw records:</span> {{ ledger?.summary.raw_records || 0 }}</p>
						<p><span class="font-medium text-slate-800">Distinct students:</span> {{ ledger?.summary.total_students || 0 }}</p>
						<p><span class="font-medium text-slate-800">Present rows:</span> {{ ledger?.summary.total_present || 0 }}</p>
						<p><span class="font-medium text-slate-800">Total rows:</span> {{ ledger?.summary.total_attendance || 0 }}</p>
						<p><span class="font-medium text-slate-800">% Present:</span> {{ ledger?.summary.percentage_present || 0 }}%</p>
					</div>
				</template>
			</AnalyticsCard>
		</section>

		<p v-if="isLoading" class="analytics-empty">Refreshing attendance ledger...</p>
	</div>
</template>

<style scoped>
.attendance-ledger-shell {
	max-width: none;
}

.attendance-ledger-grid {
	grid-template-columns: minmax(0, 1fr);
}

.ledger-sticky-col {
	position: sticky;
	background: rgb(var(--surface-rgb) / 0.98);
	z-index: 2;
}

.ledger-sticky-col--first {
	left: 0;
	min-width: 14rem;
	max-width: 18rem;
}

.ledger-sticky-col--second {
	left: 14rem;
	min-width: 8rem;
}

thead .ledger-sticky-col {
	z-index: 5;
}

@media (min-width: 768px) {
	.attendance-ledger-grid {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
}
</style>
