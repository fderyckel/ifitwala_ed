// ui-spa/src/types/studentLogDashboard.ts

export type StudentLogDashboardFilters = {
	school: string | null
	academic_year: string | null
	program: string | null
	author: string | null
	from_date: string | null
	to_date: string | null
	student: string | null
}

export type StudentLogFilterMeta = {
	default_school?: string | null
	schools: { name: string; label?: string }[]
	academic_years: {
		name: string
		label?: string
		year_start_date?: string | null
		year_end_date?: string | null
		school?: string | null
	}[]
	programs: { name: string; label?: string }[]
	authors: { user_id: string; label: string }[]
}

export type StudentLogDashboardMeta = StudentLogFilterMeta

export type StudentLogChartSeries = { label: string; value: number }

export type StudentLogStudentRow = {
	date: string
	log_type: string
	content?: string | null
	author: string
}

export type StudentLogDashboardData = {
	openFollowUps: number
	logTypeCount: StudentLogChartSeries[]
	logsByCohort: StudentLogChartSeries[]
	logsByProgram: StudentLogChartSeries[]
	logsByAuthor: StudentLogChartSeries[]
	nextStepTypes: StudentLogChartSeries[]
	incidentsOverTime: StudentLogChartSeries[]
	studentLogs: StudentLogStudentRow[]
}

export type StudentLogDashboardSummary = StudentLogDashboardData

export type StudentLogRecentRow = {
	date: string
	student: string
	student_full_name: string | null
	program?: string | null
	log_type: string
	content?: string | null
	author: string
	requires_follow_up: 0 | 1 | boolean
}

export type StudentSearchResult = {
	student: string
	student_full_name: string
}
