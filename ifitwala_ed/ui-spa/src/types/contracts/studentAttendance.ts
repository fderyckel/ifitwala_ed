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

export type GetWeekendDaysRequest = {
	student_group: string | null
}

export type GetWeekendDaysResponse = number[]

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
