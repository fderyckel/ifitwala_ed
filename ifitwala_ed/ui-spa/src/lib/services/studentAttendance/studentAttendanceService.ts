// ui-spa/src/lib/services/studentAttendance/studentAttendanceService.ts

import { createResource } from 'frappe-ui'

import { uiSignals, SIGNAL_ATTENDANCE_INVALIDATE } from '@/lib/uiSignals'

import type {
	AttendanceRecordedDatesRequest,
	AttendanceRecordedDatesResponse,
	BulkUpsertAttendanceRequest,
	BulkUpsertAttendanceResponse,
	FetchActiveProgramsRequest,
	FetchActiveProgramsResponse,
	FetchPortalAcademicYearsRequest,
	FetchPortalAcademicYearsResponse,
	FetchBlocksForDayRequest,
	FetchBlocksForDayResponse,
	FetchExistingAttendanceRequest,
	FetchExistingAttendanceResponse,
	FetchPortalTermsRequest,
	FetchPortalTermsResponse,
	GetMeetingDatesRequest,
	GetMeetingDatesResponse,
	GetWeekendDaysRequest,
	GetWeekendDaysResponse,
	FetchPortalStudentGroupsRequest,
	FetchPortalStudentGroupsResponse,
	FetchSchoolFilterContextRequest,
	FetchSchoolFilterContextResponse,
	FetchStudentsRequest,
	FetchStudentsResponse,
	ListAttendanceCodesRequest,
	ListAttendanceCodesResponse,
	PreviousStatusMapRequest,
	PreviousStatusMapResponse,
} from '@/types/contracts/studentAttendance'

/**
 * Student Attendance Service (A+)
 * ------------------------------------------------------------
 * - Uses frappe-ui createResource
 * - Returns domain payloads only (contracts)
 * - No toast here
 * - Emits invalidation signals after confirmed mutations
 */
export function createStudentAttendanceService() {
	const schoolContextResource = createResource<FetchSchoolFilterContextResponse>({
		url: 'ifitwala_ed.api.student_attendance.fetch_school_filter_context',
		method: 'POST',
		auto: false,
	})

	const programResource = createResource<FetchActiveProgramsResponse>({
		url: 'ifitwala_ed.api.student_attendance.fetch_active_programs',
		method: 'POST',
		auto: false,
	})

	const academicYearResource = createResource<FetchPortalAcademicYearsResponse>({
		url: 'ifitwala_ed.api.student_attendance.fetch_portal_academic_years',
		method: 'POST',
		auto: false,
	})

	const termResource = createResource<FetchPortalTermsResponse>({
		url: 'ifitwala_ed.api.student_attendance.fetch_portal_terms',
		method: 'POST',
		auto: false,
	})

	const groupResource = createResource<FetchPortalStudentGroupsResponse>({
		url: 'ifitwala_ed.api.student_attendance.fetch_portal_student_groups',
		method: 'POST',
		auto: false,
	})

	const attendanceCodesResource = createResource<ListAttendanceCodesResponse>({
		url: 'ifitwala_ed.schedule.attendance_utils.list_attendance_codes',
		method: 'POST',
		auto: false,
	})

	const weekendDaysResource = createResource<GetWeekendDaysResponse>({
		url: 'ifitwala_ed.api.student_attendance.get_weekend_days',
		method: 'POST',
		auto: false,
	})

	const meetingDatesResource = createResource<GetMeetingDatesResponse>({
		url: 'ifitwala_ed.schedule.attendance_utils.get_meeting_dates',
		method: 'POST',
		auto: false,
	})

	const recordedDatesResource = createResource<AttendanceRecordedDatesResponse>({
		url: 'ifitwala_ed.schedule.attendance_utils.attendance_recorded_dates',
		method: 'POST',
		auto: false,
	})

	const fetchStudentsResource = createResource<FetchStudentsResponse>({
		url: 'ifitwala_ed.schedule.attendance_utils.fetch_students',
		method: 'POST',
		auto: false,
	})

	const previousStatusResource = createResource<PreviousStatusMapResponse>({
		url: 'ifitwala_ed.schedule.attendance_utils.previous_status_map',
		method: 'POST',
		auto: false,
	})

	const existingAttendanceResource = createResource<FetchExistingAttendanceResponse>({
		url: 'ifitwala_ed.schedule.attendance_utils.fetch_existing_attendance',
		method: 'POST',
		auto: false,
	})

	const blocksForDayResource = createResource<FetchBlocksForDayResponse>({
		url: 'ifitwala_ed.schedule.attendance_utils.fetch_blocks_for_day',
		method: 'POST',
		auto: false,
	})

	const bulkUpsertResource = createResource<BulkUpsertAttendanceResponse>({
		url: 'ifitwala_ed.schedule.attendance_utils.bulk_upsert_attendance',
		method: 'POST',
		auto: false,
	})

	async function fetchSchoolContext(
		payload: FetchSchoolFilterContextRequest = {},
	): Promise<FetchSchoolFilterContextResponse> {
		return schoolContextResource.submit(payload)
	}

	async function fetchPrograms(
		payload: FetchActiveProgramsRequest = {},
	): Promise<FetchActiveProgramsResponse> {
		return programResource.submit(payload)
	}

	async function fetchAcademicYears(
		payload: FetchPortalAcademicYearsRequest,
	): Promise<FetchPortalAcademicYearsResponse> {
		return academicYearResource.submit(payload)
	}

	async function fetchTerms(
		payload: FetchPortalTermsRequest,
	): Promise<FetchPortalTermsResponse> {
		return termResource.submit(payload)
	}

	async function fetchStudentGroups(
		payload: FetchPortalStudentGroupsRequest,
	): Promise<FetchPortalStudentGroupsResponse> {
		return groupResource.submit(payload)
	}

	async function listAttendanceCodes(
		payload: ListAttendanceCodesRequest = { show_in_attendance_tool: 1 },
	): Promise<ListAttendanceCodesResponse> {
		return attendanceCodesResource.submit(payload)
	}

	async function getWeekendDays(payload: GetWeekendDaysRequest): Promise<GetWeekendDaysResponse> {
		return weekendDaysResource.submit(payload)
	}

	async function getMeetingDates(payload: GetMeetingDatesRequest): Promise<GetMeetingDatesResponse> {
		return meetingDatesResource.submit(payload)
	}

	async function getRecordedDates(
		payload: AttendanceRecordedDatesRequest,
	): Promise<AttendanceRecordedDatesResponse> {
		return recordedDatesResource.submit(payload)
	}

	async function fetchRosterContext(payload: { student_group: string; attendance_date: string }) {
		const reqStudents: FetchStudentsRequest = {
			student_group: payload.student_group,
			start: 0,
			page_length: 500,
		}
		const reqPrev: PreviousStatusMapRequest = payload
		const reqExisting: FetchExistingAttendanceRequest = payload
		const reqBlocks: FetchBlocksForDayRequest = payload

		const [roster, prevMap, existingMap, blocks] = await Promise.all([
			fetchStudentsResource.submit(reqStudents),
			previousStatusResource.submit(reqPrev),
			existingAttendanceResource.submit(reqExisting),
			blocksForDayResource.submit(reqBlocks),
		])

		return { roster, prevMap, existingMap, blocks }
	}

	async function bulkUpsertAttendance(
		payload: BulkUpsertAttendanceRequest,
	): Promise<BulkUpsertAttendanceResponse> {
		const result = await bulkUpsertResource.submit(payload)

		// A+ invalidation: mutation can affect multiple mounted attendance surfaces (counts, calendars, dashboards).
		uiSignals.emit(SIGNAL_ATTENDANCE_INVALIDATE)

		return result
	}

	return {
		fetchSchoolContext,
		fetchPrograms,
		fetchAcademicYears,
		fetchTerms,
		fetchStudentGroups,
		listAttendanceCodes,
		getWeekendDays,
		getMeetingDates,
		getRecordedDates,
		fetchRosterContext,
		bulkUpsertAttendance,
	}
}
