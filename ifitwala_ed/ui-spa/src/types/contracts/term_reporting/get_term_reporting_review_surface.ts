export type ReportingCycleOption = {
	name: string
	school: string | null
	academic_year: string | null
	term: string | null
	program: string | null
	assessment_scheme: string | null
	assessment_calculation_method: string | null
	name_label: string | null
	task_cutoff_date: string | null
	status: string | null
}

export type TermReportingCycleSummary = {
	reporting_cycle: string | null
	school: string | null
	academic_year: string | null
	term: string | null
	program: string | null
	status: string | null
	assessment_scheme: string | null
	assessment_calculation_method: string | null
	name_label: string | null
	task_cutoff_date: string | null
	course_term_results: number
}

export type TermReportingReadiness = {
	status: 'ready' | 'attention' | 'blocked'
	ready: boolean
	counts: {
		total_results: number
		zero_task_results: number
		missing_score_results: number
		missing_grade_results: number
		override_results: number
		missing_teacher_comment_results: number
		missing_component_results: number
	}
	blocked_reasons: string[]
	warnings: string[]
	actions: {
		can_recalculate: boolean
		recalculate_block_reason: string | null
		can_generate_reports: boolean
		generate_reports_block_reason: string | null
	}
}

export type CourseTermResultComponent = {
	component_type: string | null
	component_key: string | null
	label: string | null
	assessment_category: string | null
	assessment_criteria: string | null
	weight: number | null
	raw_score: number | null
	weighted_score: number | null
	grade_value: string | null
	evidence_count: number | null
	included_outcome_count: number | null
	excluded_outcome_count: number | null
	calculation_note: string | null
}

export type CourseTermResultRow = {
	name: string
	student: string | null
	program_enrollment: string | null
	course: string | null
	program: string | null
	academic_year: string | null
	term: string | null
	assessment_scheme: string | null
	assessment_calculation_method: string | null
	grade_scale: string | null
	numeric_score: number | null
	grade_value: string | null
	override_grade_value: string | null
	task_counted: number | null
	total_weight: number | null
	internal_note: string | null
	components: CourseTermResultComponent[]
}

export type Request = {
	reporting_cycle?: string | null
	course?: string | null
	student?: string | null
	program?: string | null
	limit?: number
	start?: number
}

export type QueueReviewActionRequest = {
	reporting_cycle: string
	action: 'recalculate_course_results' | 'generate_student_reports'
}

export type QueueReviewActionResponse = {
	queued: boolean
	action: QueueReviewActionRequest['action']
	reporting_cycle: string
}

export type Response = {
	cycles: ReportingCycleOption[]
	selected_reporting_cycle: string | null
	cycle: TermReportingCycleSummary | null
	filters: {
		reporting_cycle: string | null
		course: string | null
		student: string | null
		program: string | null
	}
	results: {
		rows: CourseTermResultRow[]
		total_count: number
		page_count: number
		start: number
		limit: number
	}
	readiness: TermReportingReadiness
}
