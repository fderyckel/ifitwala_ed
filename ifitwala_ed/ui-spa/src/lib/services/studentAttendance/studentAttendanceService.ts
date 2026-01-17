// ui-spa/src/lib/services/studentAttendance/studentAttendanceService.ts

import { createResource } from 'frappe-ui'

import { uiSignals, SIGNAL_CALENDAR_INVALIDATE } from '@/lib/uiSignals'

import type { AttendanceCode, BlockKey } from '@/pages/staff/schedule/student-attendance-tool/types'

export type SchoolFilterContext = {
	default_school: string | null
	schools: Array<{ name: string; school_name?: string | null }>
}

export type ProgramRow = {
	name: string
	program_name?: string | null
}

export type StudentGroupRow = {
	name: string
	student_group_name?: string | null
	program?: string | null
	school?: string | null
	course?: string | null
	cohort?: string | null
	academic_year?: string | null
	status?: string | null
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

export type ExistingAttendanceMap = Record<string, Record<number, { code: string; remark: string }>>

export type BulkUpsertRow = {
	student: string
	student_group: string
	attendance_date: string
	block_number: number
	attendance_code: string
	remark: string
}

export type BulkUpsertResult = {
	created: number
	updated: number
}

/**
 * Student Attendance Service (A+)
 * ------------------------------------------------------------
 * Rules:
 * - Uses frappe-ui createResource (transport handled by lib/frappe.ts resourceFetcher)
 * - Returns domain payloads only
 * - No toast here
 * - Emits invalidation signals after confirmed mutations
 */
export function createStudentAttendanceService() {
	const schoolContextResource = createResource<SchoolFilterContext>({
		url: 'ifitwala_ed.api.student_attendance.fetch_school_filter_context',
		method: 'POST',
		auto: false,
	})

	const programResource = createResource<ProgramRow[]>({
		url: 'ifitwala_ed.api.student_attendance.fetch_active_programs',
		method: 'POST',
		auto: false,
	})

	const groupResource = createResource<StudentGroupRow[]>({
		url: 'ifitwala_ed.api.student_attendance.fetch_portal_student_groups',
		method: 'POST',
		auto: false,
	})

	const attendanceCodesResource = createResource<AttendanceCode[]>({
		url: 'ifitwala_ed.schedule.attendance_utils.list_attendance_codes',
		method: 'POST',
		auto: false,
	})

	const weekendDaysResource = createResource<number[]>({
		url: 'ifitwala_ed.api.student_attendance.get_weekend_days',
		method: 'POST',
		auto: false,
	})

	const meetingDatesResource = createResource<string[]>({
		url: 'ifitwala_ed.schedule.attendance_utils.get_meeting_dates',
		method: 'POST',
		auto: false,
	})

	const recordedDatesResource = createResource<string[]>({
		url: 'ifitwala_ed.schedule.attendance_utils.attendance_recorded_dates',
		method: 'POST',
		auto: false,
	})

	const fetchStudentsResource = createResource<FetchStudentsResponse>({
		url: 'ifitwala_ed.schedule.attendance_utils.fetch_students',
		method: 'POST',
		auto: false,
	})

	const previousStatusResource = createResource<Record<string, string>>({
		url: 'ifitwala_ed.schedule.attendance_utils.previous_status_map',
		method: 'POST',
		auto: false,
	})

	const existingAttendanceResource = createResource<ExistingAttendanceMap>({
		url: 'ifitwala_ed.schedule.attendance_utils.fetch_existing_attendance',
		method: 'POST',
		auto: false,
	})

	const blocksForDayResource = createResource<BlockKey[]>({
		url: 'ifitwala_ed.schedule.attendance_utils.fetch_blocks_for_day',
		method: 'POST',
		auto: false,
	})

	const bulkUpsertResource = createResource<BulkUpsertResult>({
		url: 'ifitwala_ed.schedule.attendance_utils.bulk_upsert_attendance',
		method: 'POST',
		auto: false,
	})

	async function fetchSchoolContext(): Promise<SchoolFilterContext> {
		return schoolContextResource.submit({})
	}

	async function fetchPrograms(): Promise<ProgramRow[]> {
		return programResource.submit({})
	}

	async function fetchStudentGroups(payload: {
		school: string | null
		program: string | null
	}): Promise<StudentGroupRow[]> {
		return groupResource.submit(payload)
	}

	async function listAttendanceCodes(): Promise<AttendanceCode[]> {
		return attendanceCodesResource.submit({ show_in_attendance_tool: 1 })
	}

	async function getWeekendDays(payload: { student_group: string | null }): Promise<number[]> {
		return weekendDaysResource.submit(payload)
	}

	async function getMeetingDates(payload: { student_group: string }): Promise<string[]> {
		return meetingDatesResource.submit(payload)
	}

	async function getRecordedDates(payload: { student_group: string }): Promise<string[]> {
		return recordedDatesResource.submit(payload)
	}

	async function fetchRosterContext(payload: { student_group: string; attendance_date: string }) {
		const [roster, prevMap, existingMap, blocks] = await Promise.all([
			fetchStudentsResource.submit({ student_group: payload.student_group, start: 0, page_length: 500 }),
			previousStatusResource.submit(payload),
			existingAttendanceResource.submit(payload),
			blocksForDayResource.submit(payload),
		])

		return { roster, prevMap, existingMap, blocks }
	}

	async function bulkUpsertAttendance(payload: { payload: BulkUpsertRow[] }): Promise<BulkUpsertResult> {
		const result = await bulkUpsertResource.submit(payload)

		// A+ invalidation: a mutation that can affect calendars/dashboards elsewhere
		uiSignals.emit(SIGNAL_CALENDAR_INVALIDATE)

		return result
	}

	return {
		fetchSchoolContext,
		fetchPrograms,
		fetchStudentGroups,
		listAttendanceCodes,
		getWeekendDays,
		getMeetingDates,
		getRecordedDates,
		fetchRosterContext,
		bulkUpsertAttendance,
	}
}
