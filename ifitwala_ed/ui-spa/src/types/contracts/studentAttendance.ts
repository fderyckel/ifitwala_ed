// ui-spa/src/types/contracts/studentAttendance.ts

// ------------------------------------------------------------
// Student Attendance (SPA) — Backend-owned contracts
// ------------------------------------------------------------

export type AttendanceBlockNumber = number

export type StudentAttendanceCodeRow = {
	name: string
	attendance_code: string
	attendance_code_name: string
	display_order?: number
	color?: string | null
}

export type FetchSchoolFilterContextRequest = Record<string, never>

export type FetchSchoolFilterContextResponse = {
	default_school: string | null
	schools: Array<{
		name: string
		school_name?: string | null
	}>
}

export type FetchActiveProgramsRequest = Record<string, never>

export type FetchActiveProgramsResponse = Array<{
	name: string
	program_name?: string | null
}>

export type AttendanceLedgerContextRequest = {
	school?: string | null
	program?: string | null
	academic_year?: string | null
	term?: string | null
	student_group?: string | null
}

export type AttendanceLedgerContextResponse = {
	schools: FetchSchoolFilterContextResponse['schools']
	default_school: string | null
	programs: FetchActiveProgramsResponse
	default_program: string | null
	academic_years: FetchPortalAcademicYearsResponse
	default_academic_year: string | null
	terms: FetchPortalTermsResponse
	default_term: string | null
	student_groups: FetchPortalStudentGroupsResponse
	default_student_group: string | null
}

export type FetchPortalAcademicYearsRequest = {
	school: string | null
}

export type FetchPortalAcademicYearsResponse = Array<{
	name: string
	year_start_date?: string | null
	year_end_date?: string | null
	school?: string | null
}>

export type FetchPortalTermsRequest = {
	school: string | null
	academic_year: string | null
}

export type FetchPortalTermsResponse = Array<{
	name: string
	academic_year?: string | null
	school?: string | null
	term_start_date?: string | null
	term_end_date?: string | null
}>

export type FetchPortalStudentGroupsRequest = {
	school: string | null
	program: string | null
}

export type FetchPortalStudentGroupsResponse = Array<{
	name: string
	student_group_name?: string | null
	program?: string | null
	school?: string | null
	course?: string | null
	cohort?: string | null
	academic_year?: string | null
	status?: string | null
}>

export type ListAttendanceCodesRequest = {
	show_in_attendance_tool?: 0 | 1 | null
}

export type ListAttendanceCodesResponse = StudentAttendanceCodeRow[]

export type AttendanceToolBootstrapRequest = {
	school?: string | null
	program?: string | null
	student_group?: string | null
}

export type AttendanceToolBootstrapResponse = {
	schools: FetchSchoolFilterContextResponse['schools']
	default_school: string | null
	programs: FetchActiveProgramsResponse
	default_program: string | null
	student_groups: FetchPortalStudentGroupsResponse
	default_student_group: string | null
	attendance_codes: ListAttendanceCodesResponse
	default_code: string | null
}

export type GetWeekendDaysRequest = {
	student_group: string | null
}

export type GetWeekendDaysResponse = number[]

export type AttendanceToolGroupContextRequest = {
	student_group: string
}

export type AttendanceToolGroupContextResponse = {
	weekend_days: GetWeekendDaysResponse
	meeting_dates: GetMeetingDatesResponse
	recorded_dates: AttendanceRecordedDatesResponse
	default_selected_date: string | null
}

export type GetMeetingDatesRequest = {
	student_group: string
}

export type GetMeetingDatesResponse = string[]

export type AttendanceRecordedDatesRequest = {
	student_group: string
}

export type AttendanceRecordedDatesResponse = string[]

export type FetchStudentsRequest = {
	student_group: string
	start?: number
	page_length?: number
}

export type FetchStudentsResponse = {
	students: Array<{
		student: string
		student_name: string
		preferred_name?: string | null
		student_image?: string | null
		birth_date?: string | null
		medical_info?: string | null
	}>
	start: number
	total: number
	group_info: {
		name?: string | null
		program?: string | null
		course?: string | null
		cohort?: string | null
	}
}

export type PreviousStatusMapRequest = {
	student_group: string
	attendance_date: string
}

export type PreviousStatusMapResponse = Record<string, string>

export type FetchExistingAttendanceRequest = {
	student_group: string
	attendance_date: string
}

export type FetchExistingAttendanceResponse = Record<
	string,
	Record<AttendanceBlockNumber, { code: string; remark: string }>
>

export type FetchBlocksForDayRequest = {
	student_group: string
	attendance_date: string
}

export type FetchBlocksForDayResponse = AttendanceBlockNumber[]

export type AttendanceToolRosterContextRequest = {
	student_group: string
	attendance_date: string
}

export type AttendanceToolRosterContextResponse = {
	roster: FetchStudentsResponse
	prev_map: PreviousStatusMapResponse
	existing_map: FetchExistingAttendanceResponse
	blocks: FetchBlocksForDayResponse
}

export type BulkUpsertAttendanceRow = {
	student: string
	student_group: string
	attendance_date: string
	block_number: AttendanceBlockNumber
	attendance_code: string
	remark: string
}

export type BulkUpsertAttendanceRequest = {
	payload: BulkUpsertAttendanceRow[]
}

export type BulkUpsertAttendanceResponse = {
	created: number
	updated: number
}
