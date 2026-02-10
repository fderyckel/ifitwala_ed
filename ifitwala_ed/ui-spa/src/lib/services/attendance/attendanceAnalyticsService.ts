// ui-spa/src/lib/services/attendance/attendanceAnalyticsService.ts

import { createResource } from 'frappe-ui'

import type {
	AttendanceBaseParams,
	AttendanceCodeUsageParams,
	AttendanceCodeUsageResponse,
	AttendanceHeatmapParams,
	AttendanceHeatmapResponse,
	AttendanceLedgerParams,
	AttendanceLedgerResponse,
	AttendanceMyGroupsParams,
	AttendanceMyGroupsResponse,
	AttendanceOverviewParams,
	AttendanceOverviewResponse,
	AttendanceRiskParams,
	AttendanceRiskResponse,
} from '@/types/contracts/attendance'

const METHOD = 'ifitwala_ed.api.attendance.get'

/**
 * Attendance Analytics Service (A+)
 * ------------------------------------------------------------
 * - Single backend endpoint with strict modes.
 * - POST only.
 * - Flat payload via submit(payload).
 * - No UI side effects (no toast, no signals).
 */
export function createAttendanceAnalyticsService() {
	const overviewResource = createResource<AttendanceOverviewResponse>({
		url: METHOD,
		method: 'POST',
		auto: false,
	})

	const heatmapResource = createResource<AttendanceHeatmapResponse>({
		url: METHOD,
		method: 'POST',
		auto: false,
	})

	const riskResource = createResource<AttendanceRiskResponse>({
		url: METHOD,
		method: 'POST',
		auto: false,
	})

	const codeUsageResource = createResource<AttendanceCodeUsageResponse>({
		url: METHOD,
		method: 'POST',
		auto: false,
	})

	const myGroupsResource = createResource<AttendanceMyGroupsResponse>({
		url: METHOD,
		method: 'POST',
		auto: false,
	})

	const ledgerResource = createResource<AttendanceLedgerResponse>({
		url: METHOD,
		method: 'POST',
		auto: false,
	})

	const legacyAttendanceReportResource = createResource<{
		columns?: Array<{
			fieldname?: string
			label?: string
			fieldtype?: string
			options?: string
		}>
		result?: Array<Record<string, string | number | null>>
		data?: Array<Record<string, string | number | null>>
		message?: {
			columns?: Array<{
				fieldname?: string
				label?: string
				fieldtype?: string
				options?: string
			}>
			result?: Array<Record<string, string | number | null>>
			data?: Array<Record<string, string | number | null>>
		}
	}>({
		url: 'frappe.desk.query_report.run',
		method: 'POST',
		auto: false,
	})

	async function getOverview(payload: AttendanceOverviewParams): Promise<AttendanceOverviewResponse> {
		return overviewResource.submit(payload)
	}

	async function getHeatmap(payload: AttendanceHeatmapParams): Promise<AttendanceHeatmapResponse> {
		return heatmapResource.submit(payload)
	}

	async function getRisk(payload: AttendanceRiskParams): Promise<AttendanceRiskResponse> {
		return riskResource.submit(payload)
	}

	async function getCodeUsage(payload: AttendanceCodeUsageParams): Promise<AttendanceCodeUsageResponse> {
		return codeUsageResource.submit(payload)
	}

	async function getMyGroups(payload: AttendanceMyGroupsParams): Promise<AttendanceMyGroupsResponse> {
		return myGroupsResource.submit(payload)
	}

	async function getLedger(payload: AttendanceLedgerParams): Promise<AttendanceLedgerResponse> {
		try {
			return await ledgerResource.submit(payload)
		} catch (error) {
			if (!isLedgerModeUnavailable(error)) throw error
			const reportResponse = await legacyAttendanceReportResource.submit({
				report_name: 'Attendance Report',
				filters: buildLegacyReportFilters(payload),
				ignore_prepared_report: 1,
			})
			return mapLegacyReportToLedger(payload, reportResponse)
		}
	}

	return {
		getOverview,
		getHeatmap,
		getRisk,
		getCodeUsage,
		getMyGroups,
		getLedger,
	}
}

function isLedgerModeUnavailable(error: unknown): boolean {
	const message = extractErrorMessage(error).toLowerCase()
	return message.includes('invalid attendance mode: ledger')
}

function extractErrorMessage(error: unknown): string {
	if (error instanceof Error && error.message) return error.message
	if (typeof error === 'string') return error
	if (!error || typeof error !== 'object') return ''

	const maybe = error as {
		message?: string
		_messages?: string
		exception?: string
		exc?: string
	}
	return maybe.message || maybe._messages || maybe.exception || maybe.exc || ''
}

function buildLegacyReportFilters(payload: AttendanceLedgerParams): Record<string, unknown> {
	const { fromDate, toDate } = resolveDateRange(payload)

	const filters: Record<string, unknown> = {
		school: payload.school || '',
		academic_year: payload.academic_year || '',
		from_date: fromDate,
		to_date: toDate,
		whole_day: payload.whole_day ? 1 : 0,
	}
	if (payload.term) filters.term = payload.term
	if (payload.program) filters.program = payload.program
	if (payload.student_group) filters.student_group = payload.student_group
	if (payload.course) filters.course = payload.course
	if (payload.instructor) filters.instructor = payload.instructor
	if (payload.student) filters.student = payload.student
	return filters
}

function resolveDateRange(payload: AttendanceBaseParams): { fromDate: string; toDate: string } {
	if (payload.start_date && payload.end_date) {
		return { fromDate: payload.start_date, toDate: payload.end_date }
	}

	const today = new Date()
	const end = toIsoDate(today)
	const presetDays: Record<string, number> = {
		today: 0,
		last_week: 7,
		last_2_weeks: 14,
		last_month: 30,
		last_3_months: 90,
	}

	const days = payload.date_preset ? presetDays[payload.date_preset] ?? 0 : 0
	const start = new Date(today)
	start.setDate(today.getDate() - days)
	return { fromDate: toIsoDate(start), toDate: end }
}

function toIsoDate(value: Date): string {
	return value.toISOString().slice(0, 10)
}

function mapLegacyReportToLedger(
	payload: AttendanceLedgerParams,
	reportData: {
		columns?: Array<{ fieldname?: string; label?: string; fieldtype?: string; options?: string }>
		result?: Array<Record<string, string | number | null>>
		message?: {
			columns?: Array<{ fieldname?: string; label?: string; fieldtype?: string; options?: string }>
			result?: Array<Record<string, string | number | null>>
		}
	},
): AttendanceLedgerResponse {
	const { fromDate, toDate } = resolveDateRange(payload)
	const rawColumns = reportData.columns || reportData.message?.columns || []
	const rawRows = reportData.result || reportData.data || reportData.message?.result || reportData.message?.data || []
	const filteredRows = applyLegacyRowFilters(rawRows, payload)
	const sortedRows = applyLegacySort(filteredRows, payload.sort_by || 'student_label', payload.sort_order || 'asc')

	const page = Math.max(payload.page || 1, 1)
	const pageLength = Math.max(payload.page_length || 80, 1)
	const totalRows = sortedRows.length
	const totalPages = Math.max(Math.ceil(totalRows / pageLength), 1)
	const clampedPage = Math.min(page, totalPages)
	const startIndex = (clampedPage - 1) * pageLength
	const pageRows = sortedRows.slice(startIndex, startIndex + pageLength)

	const columns: AttendanceLedgerResponse['columns'] = rawColumns
		.filter((column) => !!column.fieldname)
		.map((column) => ({
			fieldname: column.fieldname as string,
			label: column.label || column.fieldname || '',
			fieldtype: normalizeLedgerFieldtype(column.fieldtype),
			options: column.options,
		}))

	const totalPresent = sortedRows.reduce((sum, row) => sum + Number(row.present_count_debug || 0), 0)
	const totalAttendance = sortedRows.reduce((sum, row) => sum + Number(row.total_count_debug || 0), 0)
	const totalStudents = new Set(sortedRows.map((row) => String(row.student || ''))).size

	const studentsByLabel = new Map<string, string>()
	for (const row of sortedRows) {
		const student = String(row.student || '')
		if (!student) continue
		const studentName = String(row.student_label || student)
		studentsByLabel.set(student, studentName)
	}

	return {
		meta: {
			role_class: 'admin',
			school_scope: payload.school ? [payload.school] : [],
			date_from: fromDate,
			date_to: toDate,
			window_source: 'legacy_report_fallback',
			whole_day: payload.whole_day ? 1 : 0,
			activity_only: 0,
		},
		columns,
		rows: pageRows,
		codes: [],
		pagination: {
			page: clampedPage,
			page_length: pageLength,
			total_rows: totalRows,
			total_pages: totalPages,
		},
		summary: {
			raw_records: totalAttendance,
			total_students: totalStudents,
			total_present: totalPresent,
			total_attendance: totalAttendance,
			percentage_present: totalAttendance > 0 ? Number(((totalPresent / totalAttendance) * 100).toFixed(2)) : 0,
		},
		filter_options: {
			courses: Array.from(
				new Set(
					sortedRows
						.map((row) => row.course)
						.filter((value): value is string => typeof value === 'string' && value.trim().length > 0),
				),
			).sort(),
			instructors: [],
			students: Array.from(studentsByLabel.entries())
				.map(([student, student_name]) => ({ student, student_name }))
				.sort((a, b) => a.student_name.localeCompare(b.student_name)),
		},
	}
}

function normalizeLedgerFieldtype(fieldtype?: string): 'Data' | 'Int' | 'Percent' | 'Link' {
	const value = (fieldtype || '').toLowerCase()
	if (value === 'int' || value === 'float' || value === 'currency') return 'Int'
	if (value === 'percent') return 'Percent'
	if (value === 'link' || value === 'dynamic link') return 'Link'
	return 'Data'
}

function applyLegacySort(
	rows: Array<Record<string, string | number | null>>,
	sortBy: string,
	sortOrder: 'asc' | 'desc' | string,
): Array<Record<string, string | number | null>> {
	const direction = (sortOrder || '').toLowerCase() === 'desc' ? -1 : 1
	return [...rows].sort((left, right) => {
		const a = left[sortBy]
		const b = right[sortBy]
		if (a === b) return 0
		if (a === null || a === undefined || a === '') return 1
		if (b === null || b === undefined || b === '') return -1

		const numA = Number(a)
		const numB = Number(b)
		const bothNumeric = !Number.isNaN(numA) && !Number.isNaN(numB)
		if (bothNumeric) return (numA - numB) * direction
		return String(a).localeCompare(String(b)) * direction
	})
}

function applyLegacyRowFilters(
	rows: Array<Record<string, string | number | null>>,
	payload: AttendanceLedgerParams,
): Array<Record<string, string | number | null>> {
	const expectedType = payload.whole_day ? 'Whole Day' : 'Course'
	return rows.filter((row) => {
		if (String(row.attendance_type || '') !== expectedType) return false
		if (payload.attendance_code) {
			const codeValue = Number(row[payload.attendance_code] || 0)
			if (codeValue <= 0) return false
		}
		return true
	})
}
