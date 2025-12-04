<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { createResource } from 'frappe-ui'

import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue'
import FiltersBar from '@/components/analytics/FiltersBar.vue'
import StackedBarChart from '@/components/analytics/StackedBarChart.vue'

type HeatmapMode = 'whole-day' | 'per-block'
type HeatmapCodeOption = {
	label?: string
	value: string
	description?: string
	severity?: 'present' | 'unexcused' | 'excused' | 'late' | 'no_school' | 'missing' | 'neutral'
	severityScore?: number
}

const palette = {
	sand: '#f4ecdd',
	moss: '#7faa63',
	leaf: '#1f7a45',
	flame: '#f25b32',
	clay: '#b6522b',
	ink: '#071019',
}

type PermissionFlags = {
	can_view_tasks: boolean
	can_view_task_marks: boolean
	can_view_logs: boolean
	can_view_referrals: boolean
	can_view_nurse_details: boolean
	can_view_attendance_details: boolean
}

type StudentGroup = {
	name: string
	abbreviation?: string
	group_based_on?: string
	course?: string | null
	attendance_scope?: string | null
}

type Snapshot = {
	meta: {
		student: string
		student_name: string
		school: string
		program: string
		current_academic_year: string
		view_mode: ViewMode
		permissions: PermissionFlags
	}
	identity: {
		student: string
		full_name: string
		photo?: string | null
		cohort?: string | null
		gender?: string | null
		age?: number | null
		date_of_birth?: string | null
		school?: { name: string; label?: string }
		program_enrollment?: {
			name: string
			program: string
			program_offering?: string
			academic_year?: string
			enrollment_date?: string | null
			archived?: boolean
		}
		student_groups: StudentGroup[]
	}
	kpis: {
		attendance: {
			present_percentage: number
			total_days: number
			present_days: number
			excused_absences: number
			unexcused_absences: number
			late_count: number
		}
		tasks: {
			completion_rate: number
			total_tasks: number
			completed_tasks: number
			overdue_tasks: number
			missed_tasks: number
		}
		academic: {
			latest_overall_label: string | null
			latest_overall_value: number | null
			trend: string | null
		}
		support: {
			student_logs_total: number
			student_logs_open_followups: number
			active_referrals: number
			nurse_visits_this_term: number
		}
	}
	learning: {
		current_courses: {
			course: string
			course_name: string
			student_group?: string | null
			student_group_abbreviation?: string | null
			instructors?: { name: string; full_name: string }[]
			status?: string
			completion_rate?: number | null
			academic_summary?: { latest_grade_label?: string | null; latest_grade_value?: number | null }
		}[]
		task_progress: {
			status_distribution: { status: string; count: number; year_scope?: string; course?: string | null }[]
			by_course_completion: {
				course: string
				course_name: string
				completion_rate: number
				total_tasks?: number
				completed_tasks?: number
				missed_tasks?: number
				academic_year?: string
			}[]
		}
		recent_tasks: {
			task: string
			title: string
			course: string
			course_name: string
			student_group?: string | null
			delivery_type?: string | null
			due_date?: string | null
			status?: string | null
			complete?: boolean
			mark_awarded?: number | null
			total_mark?: number | null
			visible_to_student?: boolean
			visible_to_guardian?: boolean
			is_overdue?: boolean
			is_missed?: boolean
			last_updated_on?: string | null
		}[]
	}
	attendance: {
		summary: {
			present_percentage: number
			total_days: number
			present_days: number
			excused_absences: number
			unexcused_absences: number
			late_count: number
			most_impacted_course?: {
				course: string
				course_name: string
				absent_percentage: number
			} | null
		}
		view_mode: 'all_day' | 'by_course'
		all_day_heatmap: {
			date: string
			attendance_code: string
			attendance_code_name?: string
			count_as_present?: boolean
			color?: string
			academic_year?: string
		}[]
		by_course_heatmap: {
			course: string
			course_name: string
			week_label: string
			present_sessions?: number
			absent_sessions?: number
			unexcused_sessions?: number
			academic_year?: string
		}[]
		by_course_breakdown: {
			course: string
			course_name: string
			present_sessions: number
			excused_absent_sessions: number
			unexcused_absent_sessions: number
			late_sessions: number
			academic_year?: string
		}[]
	}
	wellbeing: {
		timeline: {
			type: 'student_log' | 'referral' | 'nurse_visit' | 'attendance_incident'
			doctype: string
			name: string
			date: string
			title: string
			summary?: string
			status?: string
			severity?: string | null
			is_sensitive?: boolean
		}[]
		metrics: {
			student_logs?: { total?: number; open_followups?: number; recent_30_days?: number }
			referrals?: { total?: number; active?: number }
			nurse_visits?: { total?: number; this_term?: number; last_12_months?: number }
			time_series?: { period: string; student_logs?: number; referrals?: number; nurse_visits?: number }[]
		}
	}
	history: {
		year_options: { key: string; label: string; academic_year?: string; academic_years?: string[] }[]
		selected_year_scope?: string
		academic_trend: {
			academic_year: string
			label: string
			overall_grade_label?: string | null
			overall_grade_value?: number | null
			task_completion_rate?: number | null
		}[]
		attendance_trend: {
			academic_year: string
			label: string
			present_percentage?: number | null
			unexcused_absences?: number | null
		}[]
		reflection_flags: {
			id: string
			category: string
			severity: 'positive' | 'neutral' | 'concern'
			message_staff?: string
			message_student?: string
		}[]
	}
}

type ViewMode = 'staff' | 'admin' | 'counselor' | 'attendance' | 'student' | 'guardian'

const viewModeOptions: { id: ViewMode; label: string }[] = [
	{ id: 'staff', label: 'Staff' },
	{ id: 'student', label: 'Student' },
	{ id: 'guardian', label: 'Guardian' },
]

const filters = ref<{ school: string | null; program: string | null; student: string | null }>({
	school: null,
	program: null,
	student: null,
})

const viewMode = ref<ViewMode>('staff')

const filterMetaResource = createResource({
	url: 'ifitwala_ed.api.student_overview_dashboard.get_filter_meta',
	method: 'GET',
	auto: true,
})

const filterMeta = computed(() => (filterMetaResource.data as any) || {})
const schools = computed(() => filterMeta.value.schools || [])
const programs = computed(() => filterMeta.value.programs || [])


watch(
	filterMeta,
	(meta) => {
		if (meta?.default_school && !filters.value.school) {
			filters.value.school = meta.default_school
		}
	},
	{ immediate: true }
)

watch(
	() => filters.value.school,
	(newSchool, oldSchool) => {
		if (newSchool !== oldSchool) {
			// when school changes, program may no longer be valid
			filters.value.program = null
			clearStudent()
		}
	}
)


const studentSearch = ref('')
const studentSuggestions = ref<{ id: string; name: string }[]>([])
const studentDropdownOpen = ref(false)
let studentSearchTimer: number | undefined

const studentSearchResource = createResource({
	url: 'ifitwala_ed.api.student_overview_dashboard.search_students',
	method: 'GET',
	auto: false,
})

const studentLoading = computed(() => studentSearchResource.loading)

function debounce(fn: () => void, delay = 350) {
	window.clearTimeout(studentSearchTimer)
	studentSearchTimer = window.setTimeout(fn, delay)
}


function openStudentDropdown() {
	// show dropdown with hint when focused but empty
	studentDropdownOpen.value = true
}

async function fetchStudents() {
	const query = studentSearch.value.trim()

	// Empty query: keep dropdown open to show the hint row
	if (!query) {
		studentSuggestions.value = []
		studentDropdownOpen.value = true
		return
	}

	const res = await studentSearchResource.fetch({
		search_text: query,
		school: filters.value.school,
		program: filters.value.program,
	})
	const list = (res as any[]) || []
	studentSuggestions.value = list.map((s: any) => ({
		id: s.student || s.name,
		name: s.student_full_name || s.full_name || s.name,
	}))
	studentDropdownOpen.value = !!studentSuggestions.value.length
}



function selectStudent(s: { id: string; name: string }) {
	filters.value.student = s.id
	studentSearch.value = s.name
	studentDropdownOpen.value = false
}

function clearStudent() {
	filters.value.student = null
	studentSearch.value = ''
	studentSuggestions.value = []
	studentDropdownOpen.value = false
}

const readyForSnapshot = computed(() => Boolean(filters.value.school && filters.value.program && filters.value.student))

const snapshotResource = createResource({
	url: 'ifitwala_ed.api.student_overview_dashboard.get_student_center_snapshot',
	method: 'POST',
	auto: false,
})


const emptySnapshot: Snapshot = {
	meta: {
		student: '',
		student_name: '',
		school: '',
		program: '',
		current_academic_year: '',
		view_mode: 'staff',
		permissions: {
			can_view_tasks: true,
			can_view_task_marks: true,
			can_view_logs: true,
			can_view_referrals: true,
			can_view_nurse_details: false,
			can_view_attendance_details: true,
		},
	},
	identity: {
		student: '',
		full_name: '',
		photo: null,
		cohort: null,
		gender: null,
		age: null,
		date_of_birth: null,
		school: undefined,
		program_enrollment: undefined,
		student_groups: [],
	},
	kpis: {
		attendance: {
			present_percentage: 0,
			total_days: 0,
			present_days: 0,
			excused_absences: 0,
			unexcused_absences: 0,
			late_count: 0,
		},
		tasks: {
			completion_rate: 0,
			total_tasks: 0,
			completed_tasks: 0,
			overdue_tasks: 0,
			missed_tasks: 0,
		},
		academic: {
			latest_overall_label: null,
			latest_overall_value: null,
			trend: null,
		},
		support: {
			student_logs_total: 0,
			student_logs_open_followups: 0,
			active_referrals: 0,
			nurse_visits_this_term: 0,
		},
	},
	learning: {
		current_courses: [],
		task_progress: {
			status_distribution: [],
			by_course_completion: [],
		},
		recent_tasks: [],
	},
	attendance: {
		summary: {
			present_percentage: 0,
			total_days: 0,
			present_days: 0,
			excused_absences: 0,
			unexcused_absences: 0,
			late_count: 0,
			most_impacted_course: null,
		},
		view_mode: 'all_day',
		all_day_heatmap: [],
		by_course_heatmap: [],
		by_course_breakdown: [],
	},
	wellbeing: {
		timeline: [],
		metrics: {},
	},
	history: {
		year_options: [],
		selected_year_scope: 'all',
		academic_trend: [],
		attendance_trend: [],
		reflection_flags: [],
	},
}

const snapshot = computed<Snapshot>(() => (snapshotResource.data as Snapshot) || emptySnapshot)
const loadingSnapshot = computed(() => snapshotResource.loading)

let snapshotDebounce: number | undefined
function debounceSnapshot() {
	window.clearTimeout(snapshotDebounce)
	snapshotDebounce = window.setTimeout(() => {
		if (readyForSnapshot.value) loadSnapshot()
	}, 350)
}

async function loadSnapshot() {
	if (!readyForSnapshot.value) return
	if (snapshotResource.loading) return // small guard to avoid spam

	await snapshotResource.submit({
		student: filters.value.student,
		school: filters.value.school,
		program: filters.value.program,
		view_mode: viewMode.value,
	})
}


watch(
	[filters, viewMode],
	() => {
		debounceSnapshot()
	},
	{ deep: true }
)

onMounted(() => {
	if (readyForSnapshot.value) loadSnapshot()
})

// local UI state
const selectedCourse = ref<string | null>(null)
const taskYearScope = ref<'current' | 'previous' | 'all'>('current')
const attendanceView = ref<'all_day' | 'by_course'>('all_day')
const attendanceScope = ref<'current' | 'last' | 'all'>('current')
const wellbeingScope = ref<'current' | 'last' | 'all'>('current')
const wellbeingFilter = ref<'all' | 'student_log' | 'referral' | 'nurse_visit' | 'attendance_incident'>('all')
const historyScope = ref<'current' | 'previous' | 'two_years' | 'all'>('all')
const attendanceKpiSource = ref<'all_day' | 'by_course'>('all_day')
watch(
	() => snapshot.value.meta?.student,
	() => {
		selectedCourse.value = null
	}
)

watch(
	[() => hasAllDayHeatmap.value, () => hasByCourseHeatmap.value],
	([hasAllDay, hasByCourse]) => {
		if (hasAllDay) {
			attendanceView.value = 'all_day'
			attendanceKpiSource.value = 'all_day'
		} else if (hasByCourse) {
			attendanceView.value = 'by_course'
			attendanceKpiSource.value = 'by_course'
		}
	}
)

const permissions = computed<PermissionFlags>(() => snapshot.value.meta.permissions)
const displayViewMode = computed<ViewMode>(() => snapshot.value.meta.view_mode || viewMode.value)

function formatPct(value: number | null | undefined, digits = 0) {
	if (value == null || Number.isNaN(value)) return '0%'
	return `${Math.round(Number(value) * 100 * 10 ** digits) / 10 ** digits}%`
}

function formatCount(value: number | null | undefined) {
	if (value == null) return '0'
	return new Intl.NumberFormat().format(value)
}

function formatDate(value?: string | null) {
	if (!value) return ''
	return value.slice(0, 10)
}

const hasAllDayHeatmap = computed(() => (snapshot.value.attendance.all_day_heatmap || []).length > 0)
const hasByCourseHeatmap = computed(() => (snapshot.value.attendance.by_course_heatmap || []).length > 0)
const hasAnyHeatmap = computed(() => hasAllDayHeatmap.value || hasByCourseHeatmap.value)

const attendanceSourceLabel = computed(() => {
	if (attendanceKpiSource.value === 'all_day') return 'Whole day'
	if (attendanceKpiSource.value === 'by_course') return 'Course-based'
	return 'No attendance data'
})

const attendanceSourceToggle = computed(() => ({
	active: attendanceKpiSource.value,
	options: [
		{ id: 'all_day', label: 'Whole day' },
		{ id: 'by_course', label: 'Per course' },
	],
}))

function setAttendanceKpiSource(source: 'all_day' | 'by_course') {
	attendanceKpiSource.value = source
	if (source === 'all_day') {
		attendanceView.value = 'all_day'
	} else {
		attendanceView.value = 'by_course'
	}
}

const courses = computed(() => snapshot.value.learning.current_courses || [])
const selectedCourseRow = computed(() => courses.value.find((c) => c.course === selectedCourse.value) || null)

function toggleCourse(courseId: string) {
	selectedCourse.value = selectedCourse.value === courseId ? null : courseId
}

function matchesYearScope(itemYear?: string | null, scope?: string) {
	if (!scope || scope === 'all') return true
	if (!itemYear) return true
	if (scope === 'current') return itemYear === snapshot.value.meta.current_academic_year
	if (scope === 'previous') {
		const prev = snapshot.value.history.year_options.find((y) => y.key === 'previous')?.academic_year
		return prev ? itemYear === prev : true
	}
	if (scope === 'two_years') {
		const yrs = snapshot.value.history.year_options.find((y) => y.key === 'two_years')?.academic_years || []
		return yrs.includes(itemYear)
	}
	if (scope === 'last') {
		const prev = snapshot.value.history.year_options.find((y) => y.key === 'previous')?.academic_year
		return prev ? itemYear === prev : true
	}
	return true
}

const filteredStatusDistribution = computed(() => {
	const list = snapshot.value.learning.task_progress.status_distribution || []
	return list.filter((item) => {
		const yearMatch = matchesYearScope(item.year_scope, taskYearScope.value)
		const courseMatch = selectedCourse.value ? !item.course || item.course === selectedCourse.value : true
		return yearMatch && courseMatch
	})
})

const statusDonutData = computed(() => {
	const total = filteredStatusDistribution.value.reduce((acc, curr) => acc + (curr.count || 0), 0) || 1
	return filteredStatusDistribution.value.map((item) => ({
		name: item.status,
		value: item.count,
		pct: Math.round((item.count / total) * 100),
	}))
})

const taskStatusOption = computed(() => ({
	color: ['#0ea5e9', '#6366f1', '#f97316', '#22c55e', '#ef4444'],
	tooltip: {
		trigger: 'item',
		formatter: (p: any) => `${p.name}: ${p.value} (${p.data?.pct || 0}%)`,
	},
	legend: { show: false },
	series: [
		{
			type: 'pie',
			radius: ['40%', '70%'],
			itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 1 },
			data: statusDonutData.value,
			label: { show: false },
			emphasis: { label: { show: true, fontWeight: 'bold' } },
		},
	],
}))

const filteredCourseCompletion = computed(() => {
	const list = snapshot.value.learning.task_progress.by_course_completion || []
	return list.filter((row) => matchesYearScope(row.academic_year, taskYearScope.value))
})

const completionOption = computed(() => {
	const courses = filteredCourseCompletion.value
	if (!courses.length) return {}
	return {
		grid: { left: 100, right: 20, top: 10, bottom: 20 },
		xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
		yAxis: { type: 'category', data: courses.map((c) => c.course_name || c.course) },
		tooltip: {
			trigger: 'axis',
			axisPointer: { type: 'shadow' },
			formatter: (params: any) => {
				const p = Array.isArray(params) ? params[0] : params
				const row = courses[p.dataIndex]
				return `${row.course_name || row.course}: ${Math.round((row.completion_rate || 0) * 100)}%`
			},
		},
		series: [
			{
				type: 'bar',
				data: courses.map((c) => Math.round((c.completion_rate || 0) * 100)),
				itemStyle: { color: '#0ea5e9' },
				showBackground: true,
				backgroundStyle: { color: '#f8fafc' },
			},
		],
	}
})

const recentTasks = computed(() => {
	const list = snapshot.value.learning.recent_tasks || []
	if (permissions.value.can_view_tasks) return list
	return list.filter((t) => t.visible_to_student || t.visible_to_guardian)
})

const filteredAllDayHeatmap = computed(() => {
	const list = snapshot.value.attendance.all_day_heatmap || []
	return list.filter((row) => matchesYearScope(row.academic_year, attendanceScope.value))
})

const allDayHeatmapOption = computed(() => {
	if (attendanceView.value !== 'all_day') return {}
	const data = filteredAllDayHeatmap.value
	if (!data.length) return {}
	const dates = data.map((d) => d.date)
	const values = data.map((item, idx) => [idx, 0, 1, item])
	return {
		grid: { left: 20, right: 10, top: 10, bottom: 30 },
		xAxis: { type: 'category', data: dates, axisLabel: { show: false }, splitArea: { show: false } },
		yAxis: { type: 'category', data: [''], axisLabel: { show: false }, splitArea: { show: false } },
		tooltip: {
			formatter: (params: any) => {
				const item = params.value?.[3] || {}
				return `${item.date || ''}<br>${item.attendance_code_name || item.attendance_code || ''}`
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
						const row = params.value?.[3] || {}
						if (row.color) return row.color
						if (row.is_late) return palette.clay
						if (row.count_as_present) return palette.leaf
						return palette.flame
					},
				},
			},
		],
	}
})

const filteredByCourseHeatmap = computed(() => {
	const list = snapshot.value.attendance.by_course_heatmap || []
	return list.filter((row) => matchesYearScope(row.academic_year, attendanceScope.value))
})

const byCourseHeatmapOption = computed(() => {
	if (attendanceView.value !== 'by_course') return {}
	const rows = filteredByCourseHeatmap.value
	if (!rows.length) return {}
	const courses = Array.from(new Set(rows.map((r) => r.course_name || r.course)))
	const weeks = Array.from(new Set(rows.map((r) => r.week_label)))
	const data = rows.flatMap((row) => {
		const severity =
			(row.unexcused_sessions || 0) * 2 +
			(row.absent_sessions || 0) +
			(row.late_sessions || 0) +
			1
		return [
			[
				weeks.indexOf(row.week_label),
				courses.indexOf(row.course_name || row.course),
				severity,
				row,
			],
		]
	})
	return {
		grid: { left: 120, right: 10, top: 10, bottom: 70 },
		xAxis: { type: 'category', data: weeks, axisLabel: { rotate: 30 } },
		yAxis: { type: 'category', data: courses },
		tooltip: {
			formatter: (params: any) => {
				const row = params.value?.[3] || {}
				const total = (row.present_sessions || 0) + (row.absent_sessions || 0) + (row.unexcused_sessions || 0)
				return `${row.course_name || row.course} (${row.week_label})<br>${formatCount(
					row.unexcused_sessions
				)} unexcused / ${formatCount(row.absent_sessions)} absent / ${formatCount(row.late_sessions)} late / ${formatCount(row.present_sessions)} present`
			},
		},
		visualMap: {
			min: 1,
			max: Math.max(...data.map((d) => d[2] as number), 1),
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
	}
})

const breakdownRows = computed(() => {
	const list = snapshot.value.attendance.by_course_breakdown || []
	return list
		.filter((row) => matchesYearScope(row.academic_year, attendanceScope.value))
		.map((row) => ({
			category: row.course_name || row.course,
			values: {
				present: row.present_sessions,
				excused: row.excused_absent_sessions,
				unexcused: row.unexcused_absent_sessions,
				late: row.late_sessions,
			},
		}))
})

const attendanceKpi = computed(() => {
	if (attendanceKpiSource.value === 'by_course') {
		const rows = breakdownRows.value
		const totals = rows.reduce(
			(acc, row) => {
				acc.present += row.values.present || 0
				acc.excused += row.values.excused || 0
				acc.unexcused += row.values.unexcused || 0
				acc.late += row.values.late || 0
				return acc
			},
			{ present: 0, excused: 0, unexcused: 0, late: 0 }
		)
		const totalSessions = totals.present + totals.excused + totals.unexcused + totals.late
		return {
			present_percentage: totalSessions ? totals.present / totalSessions : 0,
			excused: totals.excused,
			unexcused: totals.unexcused,
		}
	}

	// Whole-day mode from heatmap rows
	const rows = filteredAllDayHeatmap.value
	const present = rows.filter((r) => r.count_as_present).length
	const total = rows.length
	return {
		present_percentage: total ? present / total : snapshot.value.kpis.attendance.present_percentage,
		excused: snapshot.value.kpis.attendance.excused_absences,
		unexcused: total ? total - present : snapshot.value.kpis.attendance.unexcused_absences,
	}
})

const heatmapStudentOptions = computed(() => {
	if (!snapshot.value.meta.student) return []
	return [
		{
			label: snapshot.value.identity.full_name || snapshot.value.meta.student_name || snapshot.value.meta.student,
			value: snapshot.value.meta.student,
		},
	]
})

const heatmapAttendanceCodes = computed<HeatmapCodeOption[]>(() => {
	const fromServer = (snapshot.value.attendance as any)?.codes || []
	if (fromServer.length) {
		return fromServer.map((c: any) => ({
			label: c.label || c.attendance_code_name || c.value,
			value: c.value || c.attendance_code,
			description: '',
			severity: c.count_as_present ? 'present' : 'unexcused',
			severityScore: c.count_as_present ? 2 : 5,
		}))
	}

	// Fallback palette
	return [
		{ label: 'Present', value: 'P', severity: 'present', severityScore: 2 },
		{ label: 'Unexcused absence', value: 'UNX', severity: 'unexcused', severityScore: 5 },
		{ label: 'Absent', value: 'ABS', severity: 'excused', severityScore: 4 },
		{ label: 'Late', value: 'L', severity: 'late', severityScore: 3 },
		{ label: 'No school', value: 'HOL', severity: 'no_school', severityScore: 0 },
	]
})

const heatmapStatusLegend = computed(() => ({
	P: { severity: 'present', label: 'Present' },
	UNX: { severity: 'unexcused', label: 'Unexcused absence', score: 5 },
	ABS: { severity: 'excused', label: 'Absent', score: 4 },
	L: { severity: 'late', label: 'Late', score: 3 },
	HOL: { severity: 'no_school', label: 'Holiday', score: 0 },
}))

const heatmapWholeDayPoints = computed(() =>
	(snapshot.value.attendance.all_day_heatmap || []).map((row) => ({
		date: row.date,
		academic_year: row.academic_year,
		status_code: row.attendance_code,
		severity_score: deriveSeverityScore(row.attendance_code, row.count_as_present),
		source: 'Student Attendance records',
	}))
)

const heatmapBlockPoints = computed(() => {
	const rows = snapshot.value.attendance.by_course_heatmap || []
	const courseOrder = Array.from(new Set(rows.map((r) => r.course || r.course_name))).filter(Boolean)
	return rows.map((row) => {
		const blockNumber = Math.max(courseOrder.indexOf(row.course || row.course_name) + 1, 1)
		const { statusCode, severityScore } = deriveCourseStatus(row)
		return {
			date: row.week_label || '',
			week_index: parseWeekIndex(row.week_label),
			weekday_index: 0,
			block_number: blockNumber,
			block_label: row.course_name || row.course,
			academic_year: row.academic_year,
			course: row.course_name || row.course,
			status_code: statusCode,
			severity_score: severityScore,
			source: 'Student Attendance records',
		}
	})
})

const heatmapBlockLabels = computed(() => {
	const labels: Record<number, string> = {}
	heatmapBlockPoints.value.forEach((point) => {
		if (point.block_number) {
			labels[point.block_number] = point.block_label || point.course || `Block ${point.block_number}`
		}
	})
	return labels
})

function deriveSeverityScore(code?: string, countAsPresent?: boolean | null) {
	if (countAsPresent === true) return 2
	if (countAsPresent === false) return 5
	const normalized = (code || '').toUpperCase()
	if (normalized === 'P') return 2
	if (normalized === 'L') return 3
	if (normalized === 'E' || normalized === 'EXC') return 4
	if (normalized === 'A' || normalized === 'UNX') return 5
	if (normalized === 'HOL' || normalized === 'NA') return 0
	return undefined
}

function deriveCourseStatus(row: any) {
	const unexcused = row.unexcused_sessions || 0
	const absent = row.absent_sessions || 0
	if (unexcused > 0) return { statusCode: 'UNX', severityScore: 5 }
	if (absent > 0) return { statusCode: 'ABS', severityScore: 4 }
	if ((row.late_sessions || 0) > 0) return { statusCode: 'L', severityScore: 3 }
	return { statusCode: 'P', severityScore: 2 }
}

function parseWeekIndex(label?: string | null) {
	if (!label) return 0
	const match = label.match(/W(\d{1,2})$/i) || label.match(/-(\d{1,2})$/)
	return match ? Number(match[1]) : 0
}

const wellbeingTimeline = computed(() => {
	const events = snapshot.value.wellbeing.timeline || []
	return events.filter((item) => {
		const scopeMatch = matchesYearScope((item as any).academic_year, wellbeingScope.value)
		const typeMatch = wellbeingFilter.value === 'all' ? true : item.type === wellbeingFilter.value
		return scopeMatch && typeMatch
	})
})

const kpiTiles = computed(() => [
	{
		label: 'Attendance',
		value: `${formatPct(attendanceKpi.value.present_percentage)} present`,
		sub: `${formatCount(attendanceKpi.value.unexcused || 0)} unexcused · ${formatCount(
			attendanceKpi.value.excused || 0
		)} excused`,
		meta: attendanceSourceLabel.value,
		clickable: hasAllDayHeatmap.value && hasByCourseHeatmap.value,
		onClick: () => {
			if (hasAllDayHeatmap.value && hasByCourseHeatmap.value) {
				attendanceKpiSource.value = attendanceKpiSource.value === 'all_day' ? 'by_course' : 'all_day'
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
		sub: snapshot.value.kpis.academic.trend ? `Trend: ${snapshot.value.kpis.academic.trend}` : 'Latest overall grade',
	},
	{
		label: 'Support signals',
		value: `${formatCount(snapshot.value.kpis.support.student_logs_total)} logs`,
		sub: `${formatCount(snapshot.value.kpis.support.active_referrals)} referral(s) · ${formatCount(
			snapshot.value.kpis.support.nurse_visits_this_term
		)} nurse visits`,
	},
])

const wellbeingSeriesOption = computed(() => {
	const series = snapshot.value.wellbeing.metrics.time_series || []
	if (!series.length) return {}
	const labels = series.map((s) => s.period)
	return {
		grid: { left: 40, right: 10, top: 10, bottom: 40 },
		tooltip: { trigger: 'axis' },
		legend: { top: 0, data: ['Logs', 'Referrals', 'Nurse visits'] },
		xAxis: { type: 'category', data: labels },
		yAxis: { type: 'value' },
		series: [
			{ name: 'Logs', type: 'bar', stack: 'total', data: series.map((s) => s.student_logs || 0) },
			{ name: 'Referrals', type: 'bar', stack: 'total', data: series.map((s) => s.referrals || 0) },
			{ name: 'Nurse visits', type: 'bar', stack: 'total', data: series.map((s) => s.nurse_visits || 0) },
		],
	}
})

const historyYearOptions = computed(() => snapshot.value.history.year_options || [])
const filteredAcademicTrend = computed(() => {
	const data = snapshot.value.history.academic_trend || []
	return data.filter((row) => matchesYearScope(row.academic_year, historyScope.value))
})

const filteredAttendanceTrend = computed(() => {
	const data = snapshot.value.history.attendance_trend || []
	return data.filter((row) => matchesYearScope(row.academic_year, historyScope.value))
})

const academicTrendOption = computed(() => {
	if (!filteredAcademicTrend.value.length) return {}
	return {
		grid: { left: 40, right: 10, top: 10, bottom: 40 },
		tooltip: { trigger: 'axis' },
		legend: { top: 0, data: ['Overall', 'Task completion'] },
		xAxis: { type: 'category', data: filteredAcademicTrend.value.map((d) => d.label) },
		yAxis: { type: 'value', min: 0 },
		series: [
			{
				name: 'Overall',
				type: 'line',
				smooth: true,
				data: filteredAcademicTrend.value.map((d) => d.overall_grade_value ?? null),
			},
			{
				name: 'Task completion',
				type: 'line',
				smooth: true,
				data: filteredAcademicTrend.value.map((d) =>
					d.task_completion_rate != null ? Math.round(d.task_completion_rate * 100) : null
				),
			},
		],
	}
})

const attendanceTrendOption = computed(() => {
	if (!filteredAttendanceTrend.value.length) return {}
	return {
		grid: { left: 40, right: 10, top: 10, bottom: 40 },
		tooltip: { trigger: 'axis' },
		legend: { top: 0, data: ['Attendance %', 'Unexcused absences'] },
		xAxis: { type: 'category', data: filteredAttendanceTrend.value.map((d) => d.label) },
		yAxis: { type: 'value' },
		series: [
			{
				name: 'Attendance %',
				type: 'line',
				smooth: true,
				data: filteredAttendanceTrend.value.map((d) =>
					d.present_percentage != null ? Math.round(d.present_percentage * 100) : null
				),
			},
			{
				name: 'Unexcused absences',
				type: 'bar',
				data: filteredAttendanceTrend.value.map((d) => d.unexcused_absences || 0),
			},
		],
	}
})

const reflectionFlags = computed(() => {
	const flags = snapshot.value.history.reflection_flags || []
	return flags.map((flag) => ({
		...flag,
		message:
			displayViewMode.value === 'student' || displayViewMode.value === 'guardian'
				? flag.message_student || flag.message_staff
				: flag.message_staff || flag.message_student,
	}))
})
</script>

<template>
	<div
		class="min-h-full px-4 pb-8 pt-8 md:px-6 lg:px-8"
		style="background: var(--portal-gradient-bg);"
	>
		<header class="flex flex-wrap items-center justify-between gap-3">
			<div>
				<h1 class="text-base font-semibold tracking-tight text-slate-900">Student Overview</h1>
				<p class="mt-0.5 text-xs text-slate-500">
					One snapshot per student – identity, learning, attendance, wellbeing, and history.
				</p>
			</div>
			<div class="flex items-center gap-2">
				<select
					v-model="viewMode"
					class="h-8 rounded-md border border-slate-200 px-2 text-xs"
				>
					<option
						v-for="m in viewModeOptions"
						:key="m.id"
						:value="m.id"
					>
						{{ m.label }}
					</option>
				</select>
			</div>
		</header>

		<section class="mt-4 mb-3">
			<div class="toolbar flex flex-wrap items-end gap-3">
				<FiltersBar>
					<div class="flex flex-col gap-1 w-48">
						<label class="type-label">School</label>
						<select
							v-model="filters.school"
							class="h-9 rounded-md border border-border/80 bg-[rgb(var(--surface-rgb)/0.9)] px-2 text-xs focus:outline-none"
						>
							<option value="">Select a school</option>
							<option
								v-for="s in schools"
								:key="s.name"
								:value="s.name"
							>
								{{ s.label || s.name }}
							</option>
						</select>
					</div>

					<div class="flex flex-col gap-1 w-48">
						<label class="type-label">Program</label>
						<select
							v-model="filters.program"
							class="h-9 rounded-md border border-border/80 bg-[rgb(var(--surface-rgb)/0.9)] px-2 text-xs focus:outline-none"
						>
							<option value="">Select</option>
							<option
								v-for="p in programs"
								:key="p.name"
								:value="p.name"
							>
								{{ p.label || p.name }}
							</option>
						</select>
					</div>

					<div class="relative flex w-64 flex-col gap-1">
						<label class="type-label">Student</label>
						<div class="flex h-9 items-center rounded-md border border-border/80 bg-[rgb(var(--surface-rgb)/0.9)] px-2">
							<span class="mr-1 text-[11px] text-ink/60">🔍</span>
							<input
								v-model="studentSearch"
								class="h-full w-full bg-transparent text-xs focus:outline-none"
								placeholder="Search student"
								type="search"
								@focus="openStudentDropdown"
								@input="debounce(fetchStudents)"
							/>
							<button
								v-if="studentSearch"
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
							<div
								v-if="studentLoading"
								class="px-3 py-2 text-xs text-ink/70"
							>
								Searching…
							</div>
							<button
								v-for="s in studentSuggestions"
								:key="s.id"
								type="button"
								class="flex w-full items-start gap-2 px-3 py-2 text-left text-xs hover:bg-[rgb(var(--surface-rgb)/0.9)]"
								@click="selectStudent(s)"
							>
								<span class="font-semibold text-ink">{{ s.name }}</span>
							</button>
							<div
								v-if="!studentLoading && !studentSuggestions.length"
								class="px-3 py-2 text-xs text-ink/60"
							>
								{{ studentSearch
									? 'No matches. Try a different name or ID.'
									: 'Start typing to search for a student.' }}
							</div>
						</div>
					</div>
				</FiltersBar>
			</div>
		</section>

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

				<div v-else class="space-y-6">
					<!-- Band 1: Identity & Snapshot -->
					<section class="rounded-2xl border border-slate-200 bg-[rgb(var(--surface-rgb)/0.92)] px-4 py-5 shadow-sm">
						<div class="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
							<div class="flex gap-4">
								<div
									class="flex h-16 w-16 items-center justify-center overflow-hidden rounded-2xl bg-slate-100 text-lg font-semibold text-slate-600"
								>
									<img
										v-if="snapshot.identity.photo"
										:src="snapshot.identity.photo"
										alt="Student avatar"
										class="h-full w-full object-cover"
									/>
									<span v-else>{{ snapshot.identity.full_name?.[0] || '?' }}</span>
								</div>
								<div class="space-y-1 text-sm text-slate-700">
									<div class="flex flex-wrap items-center gap-2">
										<h2 class="text-lg font-semibold text-slate-900">
											{{ snapshot.identity.full_name || snapshot.meta.student_name || 'Student' }}
										</h2>
										<span
											v-if="snapshot.identity.cohort"
											class="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700"
										>
											{{ snapshot.identity.cohort }}
										</span>
									</div>
									<p class="text-xs text-slate-500">
										{{ snapshot.identity.program_enrollment?.program || snapshot.meta.program }}
										<span v-if="snapshot.identity.school?.label">· {{ snapshot.identity.school?.label }}</span>
									</p>
									<p class="text-xs text-slate-500">
										<span v-if="snapshot.identity.age">Age {{ snapshot.identity.age }}</span>
										<span v-if="snapshot.identity.age && snapshot.identity.gender"> · </span>
										<span v-if="snapshot.identity.gender">{{ snapshot.identity.gender }}</span>
									</p>
								</div>
							</div>
									<div class="flex flex-col gap-2">
								<div class="grid grid-cols-2 gap-3 md:grid-cols-4">
									<div
										v-for="tile in kpiTiles"
										:key="tile.label"
										:class="[
											'flex flex-col rounded-xl border border-border/70 bg-[rgb(var(--surface-rgb))] px-3 py-2 shadow-soft-sm overflow-hidden',
											tile.clickable ? 'cursor-pointer hover:border-[color:rgb(var(--leaf-rgb))] hover:bg-[rgb(var(--surface-soft-rgb))]' : '',
										]"
										@click="tile.onClick && tile.onClick()"
									>
										<div class="flex items-center justify-between gap-2">
											<p class="text-[11px] font-semibold uppercase tracking-wide text-ink/70">
												{{ tile.label }}
											</p>
											<span
												v-if="tile.meta"
												class="inline-flex shrink-0 items-center rounded-full bg-[rgb(var(--surface-soft-rgb))] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-ink/65"
											>
												{{ tile.meta }}
											</span>
										</div>

										<p class="mt-1 text-sm font-semibold text-ink">
											{{ tile.value }}
										</p>

										<div
											v-if="tile.sourceToggle?.active"
											class="mt-1 flex flex-wrap items-center gap-1"
											@click.stop
										>
											<button
												v-for="opt in tile.sourceToggle.options"
												:key="opt.id"
												type="button"
												class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold transition"
												:class="[
													opt.id === tile.sourceToggle.active
														? 'bg-[rgb(var(--ink-rgb))] text-[rgb(var(--surface-rgb))] shadow-soft'
														: 'bg-[rgb(var(--surface-soft-rgb))] text-ink/70 hover:bg-[rgb(var(--surface-rgb))]',
												]"
												@click="setAttendanceKpiSource(opt.id as any)"
											>
												{{ opt.label }}
											</button>
										</div>

										<p class="mt-1 text-[11px] text-ink/70">
											{{ tile.sub }}
										</p>
									</div>
								</div>
								<div class="flex justify-end text-[11px] text-slate-500">
									View mode:
									<span class="ml-1 rounded-full bg-slate-100 px-2 py-0.5 font-semibold text-slate-700">
										{{ displayViewMode }}
									</span>
								</div>
							</div>
						</div>
					</section>

					<!-- Band 2: Learning & Tasks -->
					<section class="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)_minmax(0,2fr)]">
						<!-- Current Courses -->
						<div class="rounded-2xl border border-slate-200 bg-[rgb(var(--surface-rgb)/0.92)] px-4 py-4 shadow-sm">
							<header class="mb-3 flex items-center justify-between">
								<div>
									<h3 class="text-sm font-semibold text-slate-800">Current Courses</h3>
									<p class="text-[11px] text-slate-500">Tap a course to filter task views.</p>
								</div>
							</header>
							<div class="space-y-2">
								<div
									v-for="course in courses"
									:key="course.course"
									:class="[
										'rounded-xl border px-3 py-2 text-sm transition hover:border-slate-300 cursor-pointer',
										selectedCourse === course.course ? 'border-emerald-500 bg-emerald-50/50' : 'border-slate-200 bg-slate-50/70',
									]"
									@click="toggleCourse(course.course)"
								>
									<div class="flex items-center justify-between gap-2">
										<div class="font-semibold text-slate-900">{{ course.course_name || course.course }}</div>
										<span class="text-[11px] uppercase tracking-wide text-slate-500">
											{{ course.status || 'current' }}
										</span>
									</div>
									<div class="mt-1 flex items-center justify-between text-xs text-slate-600">
										<span>{{ course.instructors?.map((i) => i.full_name).join(', ') }}</span>
										<span v-if="course.completion_rate != null">
											{{ Math.round((course.completion_rate || 0) * 100) }}% tasks done
										</span>
									</div>
									<div class="text-[11px] text-slate-500">
										{{ course.academic_summary?.latest_grade_label ? `Latest: ${course.academic_summary.latest_grade_label}` : '' }}
									</div>
								</div>
								<div v-if="!courses.length" class="text-xs text-slate-400">No courses found.</div>
							</div>
						</div>

						<!-- Task progress -->
						<div class="rounded-2xl border border-slate-200 bg-[rgb(var(--surface-rgb)/0.92)] px-4 py-4 shadow-sm">
							<header class="mb-3 flex flex-wrap items-center justify-between gap-3">
								<div>
									<h3 class="text-sm font-semibold text-slate-800">Task Progress</h3>
									<p class="text-[11px] text-slate-500">
										Status distribution and completion by course ({{ taskYearScope }} year scope).
									</p>
								</div>
								<div class="flex items-center gap-2">
									<button
										v-for="scope in ['current', 'previous', 'all']"
										:key="scope"
										type="button"
										:class="[
											'rounded-full px-3 py-1 text-[11px] font-semibold',
											taskYearScope === scope ? 'bg-emerald-500 text-white' : 'bg-slate-100 text-slate-600',
										]"
										@click="taskYearScope = scope as any"
									>
										{{ scope === 'current' ? 'This year' : scope === 'previous' ? 'Last year' : 'All years' }}
									</button>
								</div>
							</header>
							<div class="grid gap-4 lg:grid-cols-5">
								<div class="lg:col-span-2 rounded-xl border border-slate-200 bg-slate-50/70 p-3">
									<h4 class="text-xs font-semibold uppercase tracking-wide text-slate-600">Task status</h4>
									<AnalyticsChart
										v-if="statusDonutData.length"
										:option="taskStatusOption"
									/>
									<p v-else class="text-xs text-slate-400">No task data.</p>
								</div>
								<div class="lg:col-span-3 rounded-xl border border-slate-200 bg-slate-50/70 p-3">
									<div class="mb-1 flex items-center justify-between text-xs text-slate-600">
										<h4 class="font-semibold uppercase tracking-wide">Completion by course</h4>
										<span class="text-[11px] text-slate-500">
											{{ selectedCourseRow ? selectedCourseRow.course_name : 'All courses' }}
										</span>
									</div>
									<AnalyticsChart
										v-if="filteredCourseCompletion.length"
										:option="completionOption"
									/>
									<p v-else class="text-xs text-slate-400">No completion data.</p>
								</div>
							</div>
						</div>

						<!-- Recent tasks -->
						<div class="rounded-2xl border border-slate-200 bg-[rgb(var(--surface-rgb)/0.92)] px-4 py-4 shadow-sm">
							<header class="mb-3 flex items-center justify-between">
								<div>
									<h3 class="text-sm font-semibold text-slate-800">Most recent tasks</h3>
									<p class="text-[11px] text-slate-500">Latest {{ recentTasks.length }} items visible to you.</p>
								</div>
							</header>
							<div class="space-y-2">
								<div
									v-for="task in recentTasks"
									:key="task.task"
									class="rounded-xl border border-slate-200 bg-slate-50/60 px-3 py-2"
								>
									<div class="flex items-center justify-between text-xs text-slate-600">
										<div class="flex flex-wrap items-center gap-2">
											<span
												class="rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold text-slate-700"
											>
												{{ task.course_name || task.course }}
											</span>
											<span class="text-[11px] text-slate-500">{{ task.status || 'Assigned' }}</span>
											<span
												v-if="task.is_overdue || task.is_missed"
												class="rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-semibold text-rose-700"
											>
												Overdue
											</span>
										</div>
										<span class="text-[11px] text-slate-500">{{ formatDate(task.due_date) }}</span>
									</div>
									<div class="text-sm font-semibold text-slate-900">
										{{ task.title }}
									</div>
									<div class="text-[11px] text-slate-500">
										<span v-if="permissions.can_view_task_marks && task.total_mark">
											{{ task.mark_awarded ?? '—' }} / {{ task.total_mark }}
										</span>
										<span v-else-if="!permissions.can_view_task_marks">Marks hidden</span>
										<span v-if="task.visible_to_student === false || task.visible_to_guardian === false" class="ml-2 text-amber-600">
											Restricted
										</span>
									</div>
								</div>
								<div v-if="!recentTasks.length" class="text-xs text-slate-400">
									No recent tasks in this view.
								</div>
							</div>
						</div>
					</section>

					<!-- Band 3: Attendance -->
					<section class="analytics-card palette-card mt-6 space-y-4">
						<div class="flex flex-wrap items-center justify-center gap-2">
							<button
								type="button"
								:class="['chip-toggle', attendanceView === 'all_day' ? 'chip-toggle-active' : 'chip-toggle-muted']"
								@click="setAttendanceKpiSource('all_day')"
							>
								All-day view
							</button>
							<button
								type="button"
								:class="['chip-toggle', attendanceView === 'by_course' ? 'chip-toggle-active' : 'chip-toggle-muted']"
								@click="setAttendanceKpiSource('by_course')"
							>
								By course / activity
							</button>
							<div class="ml-auto flex items-center gap-2">
								<button
									v-for="scope in ['current', 'last', 'all']"
									:key="scope"
									type="button"
									:class="['chip-scope', attendanceScope === scope ? 'chip-scope-active' : 'chip-scope-muted']"
									@click="attendanceScope = scope as any"
								>
									{{ scope === 'current' ? 'This year' : scope === 'last' ? 'Last year' : 'All years' }}
								</button>
							</div>
						</div>

						<div class="grid grid-cols-1 gap-4 2xl:grid-cols-2">
							<div class="attendance-card palette-card">
								<header class="attendance-card-header">
									<div>
										<h3 class="section-header">Attendance heatmap</h3>
										<p class="type-meta">
											{{ attendanceView === 'all_day' ? 'Daily status by code' : 'Course × week patterns' }}
										</p>
									</div>
									<span class="type-chip-muted">
										{{ attendanceView === 'all_day' ? 'Whole-day records' : 'Session-level records' }}
									</span>
								</header>

								<div class="attendance-card-body">
									<AnalyticsChart
										v-if="attendanceView === 'all_day' && filteredAllDayHeatmap.length"
										:option="allDayHeatmapOption"
									/>
									<AnalyticsChart
										v-else-if="attendanceView === 'by_course' && filteredByCourseHeatmap.length"
										:option="byCourseHeatmapOption"
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
												attendanceView === 'by_course'
													? 'Sessions by code and course'
													: 'Switch to “By course” to see breakdown'
											}}
										</p>
									</div>
									<span class="type-chip-muted">
										{{ attendanceSourceLabel }}
									</span>
								</header>

								<div class="attendance-card-body space-y-3">
									<StackedBarChart
										v-if="attendanceView === 'by_course' && breakdownRows.length"
										title=""
										:series="[
											{ key: 'present',   label: 'Present',   color: palette.leaf },
											{ key: 'excused',   label: 'Excused',   color: palette.sand },
											{ key: 'unexcused', label: 'Unexcused', color: palette.flame },
											{ key: 'late',      label: 'Late',      color: palette.clay },
										]"
										:rows="breakdownRows"
									/>
									<p
										v-else
										class="type-empty"
									>
										Switch to course view to see breakdown.
									</p>

									<div class="grid grid-cols-1 gap-2 text-xs sm:grid-cols-3">
										<div class="mini-kpi-card">
											<p class="mini-kpi-label">Total days absent</p>
											<p class="mini-kpi-value">
												{{
													formatCount(
														snapshot.attendance.summary.total_days - snapshot.attendance.summary.present_days
													)
												}}
											</p>
										</div>
										<div class="mini-kpi-card mini-kpi-card-alert">
											<p class="mini-kpi-label">Unexcused absences</p>
											<p class="mini-kpi-value text-[color:rgb(var(--flame-rgb))]">
												{{ formatCount(snapshot.attendance.summary.unexcused_absences) }}
											</p>
										</div>
										<div class="mini-kpi-card">
											<p class="mini-kpi-label">
												{{ displayViewMode === 'student' ? 'Most fragile course' : 'Most impacted course' }}
											</p>
											<p class="mini-kpi-value">
												{{ snapshot.attendance.summary.most_impacted_course?.course_name || '—' }}
											</p>
										</div>
									</div>
								</div>
							</div>
						</div>
					</section>

					<!-- Band 4: Wellbeing & Support -->
					<section class="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
						<div class="rounded-2xl border border-slate-200 bg-[rgb(var(--surface-rgb)/0.92)] px-4 py-4 shadow-sm">
							<header class="mb-3 flex flex-wrap items-center justify-between gap-3">
								<div>
									<h3 class="text-sm font-semibold text-slate-800">Wellbeing timeline</h3>
									<p class="text-[11px] text-slate-500">
										Logs, referrals, nurse visits, and key attendance incidents.
									</p>
								</div>
								<div class="flex items-center gap-2">
									<select
										v-model="wellbeingFilter"
										class="h-8 rounded-md border border-slate-200 px-2 text-[11px]"
									>
										<option value="all">All</option>
										<option value="student_log">Logs</option>
										<option value="referral">Referrals</option>
										<option value="nurse_visit">Nurse</option>
										<option value="attendance_incident">Attendance</option>
									</select>
									<select
										v-model="wellbeingScope"
										class="h-8 rounded-md border border-slate-200 px-2 text-[11px]"
									>
										<option value="current">This year</option>
										<option value="last">Last year</option>
										<option value="all">All years</option>
									</select>
								</div>
							</header>
							<div class="space-y-3">
								<div
									v-for="item in wellbeingTimeline"
									:key="item.name"
									class="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2"
								>
									<div
										class="mt-1 h-2.5 w-2.5 rounded-full"
										:class="{
											'bg-emerald-500': item.type === 'student_log',
											'bg-amber-500': item.type === 'referral',
											'bg-sky-500': item.type === 'nurse_visit',
											'bg-rose-500': item.type === 'attendance_incident',
										}"
									></div>
									<div class="flex-1 text-sm text-slate-700">
										<div class="flex items-center justify-between">
											<div class="font-semibold text-slate-900">{{ item.title }}</div>
											<span class="text-[11px] text-slate-500">{{ formatDate(item.date) }}</span>
										</div>
										<p class="text-xs text-slate-500">{{ item.summary }}</p>
										<div class="mt-1 flex items-center gap-2 text-[11px] text-slate-500">
											<span class="rounded-full bg-white px-2 py-0.5 shadow-sm">
												{{ item.type }}
											</span>
											<span v-if="item.status" class="rounded-full bg-white px-2 py-0.5 shadow-sm">
												{{ item.status }}
											</span>
										</div>
									</div>
								</div>
								<div v-if="!wellbeingTimeline.length" class="text-xs text-slate-400">
									No wellbeing items for this scope.
								</div>
							</div>
						</div>

						<div class="rounded-2xl border border-slate-200 bg-[rgb(var(--surface-rgb)/0.92)] px-4 py-4 shadow-sm">
							<header class="mb-3 flex items-center justify-between">
								<h3 class="text-sm font-semibold text-slate-800">Support metrics & patterns</h3>
							</header>
							<AnalyticsChart
								v-if="snapshot.wellbeing.metrics.time_series?.length"
								:option="wellbeingSeriesOption"
							/>
							<div v-else class="text-xs text-slate-400">No trend data yet.</div>
							<div class="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-600">
								<div class="rounded-lg bg-slate-50/70 px-3 py-2">
									<p class="text-[11px] uppercase tracking-wide text-slate-500">Open log follow-ups</p>
									<p class="text-base font-semibold text-slate-900">
										{{ formatCount(snapshot.wellbeing.metrics.student_logs?.open_followups || 0) }}
									</p>
								</div>
								<div class="rounded-lg bg-slate-50/70 px-3 py-2">
									<p class="text-[11px] uppercase tracking-wide text-slate-500">Active referrals</p>
									<p class="text-base font-semibold text-amber-600">
										{{ formatCount(snapshot.wellbeing.metrics.referrals?.active || 0) }}
									</p>
								</div>
								<div class="rounded-lg bg-slate-50/70 px-3 py-2">
									<p class="text-[11px] uppercase tracking-wide text-slate-500">Nurse visits (this term)</p>
									<p class="text-base font-semibold text-slate-900">
										{{ formatCount(snapshot.wellbeing.metrics.nurse_visits?.this_term || 0) }}
									</p>
								</div>
							</div>
						</div>
					</section>

					<!-- Band 5: History & Reflection -->
					<section class="rounded-2xl border border-slate-200 bg-[rgb(var(--surface-rgb)/0.92)] px-4 py-4 shadow-sm">
						<header class="mb-3 flex flex-wrap items-center justify-between gap-3">
							<div>
								<h3 class="text-sm font-semibold text-slate-800">History & Reflection</h3>
								<p class="text-[11px] text-slate-500">Compare years and surface narrative cues.</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<button
									v-for="opt in historyYearOptions"
									:key="opt.key"
									type="button"
									:class="[
										'rounded-full px-3 py-1 text-[11px] font-semibold',
										historyScope === opt.key ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600',
									]"
									@click="historyScope = opt.key as any"
								>
									{{ opt.label }}
								</button>
							</div>
						</header>
						<div class="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,2fr)_minmax(0,2fr)]">
							<div class="rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-3">
								<h4 class="text-xs font-semibold uppercase tracking-wide text-slate-600">Academic & task trend</h4>
								<AnalyticsChart
									v-if="filteredAcademicTrend.length"
									:option="academicTrendOption"
								/>
								<p v-else class="text-xs text-slate-400">No academic history.</p>
							</div>
							<div class="rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-3">
								<h4 class="text-xs font-semibold uppercase tracking-wide text-slate-600">Attendance trend</h4>
								<AnalyticsChart
									v-if="filteredAttendanceTrend.length"
									:option="attendanceTrendOption"
								/>
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
				</div>
			</div>
		</section>
	</div>

</template>
