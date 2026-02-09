// ui-spa/src/types/contracts/attendance.ts

export type AttendanceMode =
	| 'overview'
	| 'heatmap'
	| 'risk'
	| 'code_usage'
	| 'my_groups'

export type AttendanceHeatmapMode = 'block' | 'day'

export type AttendanceDatePreset =
	| 'today'
	| 'last_week'
	| 'last_2_weeks'
	| 'last_month'
	| 'last_3_months'

export type AttendanceRoleClass = 'admin' | 'counselor' | 'instructor'

export interface AttendanceThresholds {
	warning: number
	critical: number
}

export interface AttendanceBaseParams {
	mode: AttendanceMode
	school?: string
	academic_year?: string
	term?: string
	start_date?: string
	end_date?: string
	date_preset?: AttendanceDatePreset
	whole_day?: 0 | 1
	program?: string
	student_group?: string
	activity_only?: 0 | 1
}

export interface AttendanceOverviewParams extends AttendanceBaseParams {
	mode: 'overview'
}

export interface AttendanceHeatmapParams extends AttendanceBaseParams {
	mode: 'heatmap'
	heatmap_mode?: AttendanceHeatmapMode
}

export interface AttendanceRiskParams extends AttendanceBaseParams {
	mode: 'risk'
	thresholds?: AttendanceThresholds
	include_context?: 0 | 1
	context_student?: string
}

export interface AttendanceCodeUsageParams extends AttendanceBaseParams {
	mode: 'code_usage'
}

export interface AttendanceMyGroupsParams extends AttendanceBaseParams {
	mode: 'my_groups'
	thresholds?: AttendanceThresholds
}

export type AttendanceRequest =
	| AttendanceOverviewParams
	| AttendanceHeatmapParams
	| AttendanceRiskParams
	| AttendanceCodeUsageParams
	| AttendanceMyGroupsParams

export interface AttendanceMeta {
	role_class: AttendanceRoleClass
	school_scope: string[]
	date_from: string
	date_to: string
	window_source: string
	whole_day: 0 | 1
	activity_only: 0 | 1
}

export interface AttendanceOverviewResponse {
	meta: AttendanceMeta
	kpis: {
		expected_sessions: number
		present_sessions: number
		absent_sessions: number
		late_sessions: number
		unexplained_absent_sessions: number
		attendance_rate: number
	}
	trend: {
		previous_rate: number
		delta: number
	}
}

export interface AttendanceHeatmapCell {
	x: string
	y: number
	present: number
	expected: number
}

export interface AttendanceHeatmapResponse {
	meta: AttendanceMeta
	axis: {
		x: string[]
		y: number[]
	}
	cells: AttendanceHeatmapCell[]
}

export interface AttendanceRiskStudent {
	student: string
	student_name: string
	attendance_rate: number
	absent_count: number
	late_count: number
	unexplained_absences: number
	mismatch_days: number
}

export interface AttendanceDecliningTrend {
	student: string
	student_name: string
	current_rate: number
	previous_rate: number
	delta: number
}

export interface AttendanceUnexplainedRisk {
	student: string
	student_name: string
	unexplained_absences: number
	attendance_rate: number
}

export interface AttendanceMismatchStudent {
	student: string
	student_name: string
	mismatch_days: number
}

export interface AttendanceImprovingTrend {
	student: string
	student_name: string
	previous_rate: number
	current_rate: number
	delta: number
}

export interface AttendanceContextPoint {
	day: string
}

export interface AttendanceContextSparkline {
	student: string
	attendance: Array<AttendanceContextPoint & { expected: number; present: number }>
	academic_standing: Array<AttendanceContextPoint & { average_value: number; samples: number }>
	behaviour_incidents: Array<AttendanceContextPoint & { total_logs: number; follow_up_logs: number }>
}

export interface AttendanceRiskResponse {
	meta: AttendanceMeta
	thresholds: AttendanceThresholds
	buckets: {
		critical: number
		warning: number
		ok: number
	}
	top_critical: AttendanceRiskStudent[]
	declining_trend: AttendanceDecliningTrend[]
	frequent_unexplained: AttendanceUnexplainedRisk[]
	mismatch_students: AttendanceMismatchStudent[]
	improving_trends: AttendanceImprovingTrend[]
	compliance_by_scope: Array<{
		school: string
		school_label: string
		program: string
		expected_sessions: number
		present_sessions: number
		attendance_rate: number
	}>
	method_mix: Array<{
		attendance_method: string
		count: number
		share: number
	}>
	context_sparkline: AttendanceContextSparkline | null
}

export interface AttendanceCodeUsageRow {
	attendance_code: string
	attendance_code_name: string
	count: number
	count_as_present: 0 | 1
	is_late: 0 | 1
	is_excused: 0 | 1
	usage_share: number
}

export interface AttendanceCodeUsageResponse {
	meta: AttendanceMeta
	codes: AttendanceCodeUsageRow[]
	summary: {
		total_records: number
		unused_codes: number
		dominant_absence_code: string | null
	}
}

export interface AttendanceGroupSnapshot {
	student_group: string
	student_group_abbreviation: string
	student_group_name: string
	group_based_on: string | null
	expected: number
	present: number
	absent: number
	late: number
}

export interface AttendanceEmergingPattern {
	student: string
	student_name: string
	absent_count: number
	late_count: number
	pattern_absent_block_1: number
	attendance_rate: number
}

export interface AttendanceExceptionRow {
	student_group: string
	student_group_abbreviation: string
	student: string
	student_name: string
	status: 'Absent' | 'Late' | 'No record'
}

export interface AttendanceMyGroupsResponse {
	meta: AttendanceMeta
	groups: AttendanceGroupSnapshot[]
	emerging_patterns: AttendanceEmergingPattern[]
	exceptions: AttendanceExceptionRow[]
	improving_trends: AttendanceImprovingTrend[]
}

export type AttendanceResponse =
	| AttendanceOverviewResponse
	| AttendanceHeatmapResponse
	| AttendanceRiskResponse
	| AttendanceCodeUsageResponse
	| AttendanceMyGroupsResponse
