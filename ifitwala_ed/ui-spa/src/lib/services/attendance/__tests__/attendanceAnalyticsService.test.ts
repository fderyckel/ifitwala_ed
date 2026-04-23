import { beforeEach, describe, expect, it, vi } from 'vitest'

type ResourceRecord = {
	config: {
		url?: string
		method?: string
		auto?: boolean
	}
	submit: ReturnType<typeof vi.fn>
}

const { createResourceMock, resourceRecords } = vi.hoisted(() => {
	const resourceRecords: ResourceRecord[] = []
	const createResourceMock = vi.fn((config: ResourceRecord['config']) => {
		const record: ResourceRecord = {
			config,
			submit: vi.fn(),
		}
		resourceRecords.push(record)
		return {
			submit: record.submit,
		}
	})
	return { createResourceMock, resourceRecords }
})

vi.mock('frappe-ui', () => ({
	createResource: createResourceMock,
}))

import { createAttendanceAnalyticsService } from '@/lib/services/attendance/attendanceAnalyticsService'

describe('attendanceAnalyticsService', () => {
	beforeEach(() => {
		createResourceMock.mockClear()
		resourceRecords.length = 0
	})

	it('uses only the canonical attendance analytics endpoint', () => {
		createAttendanceAnalyticsService()

		expect(resourceRecords).toHaveLength(6)
		expect(resourceRecords.every(record => record.config.url === 'ifitwala_ed.api.attendance.get')).toBe(true)
		expect(resourceRecords.every(record => record.config.method === 'POST')).toBe(true)
		expect(resourceRecords.every(record => record.config.auto === false)).toBe(true)
	})

	it('submits ledger requests through the canonical ledger resource', async () => {
		const service = createAttendanceAnalyticsService()
		const ledgerResource = resourceRecords[5]
		const response = {
			meta: {
				role_class: 'admin',
				school_scope: ['SCH-1'],
				date_from: '2026-03-01',
				date_to: '2026-03-31',
				window_source: 'selected_term',
				whole_day: 1,
				activity_only: 0,
			},
			columns: [],
			rows: [],
			codes: [],
			pagination: { page: 1, page_length: 80, total_rows: 0, total_pages: 1 },
			summary: {
				raw_records: 0,
				total_students: 0,
				total_present: 0,
				total_late_present: 0,
				total_attendance: 0,
				percentage_present: 0,
				percentage_late: 0,
			},
			filter_options: {
				courses: [],
				instructors: [],
				students: [],
			},
		}
		const payload = {
			mode: 'ledger' as const,
			school: 'SCH-1',
			academic_year: 'AY-2026',
			whole_day: 1 as const,
			page: 1,
			page_length: 80,
		}
		ledgerResource.submit.mockResolvedValue(response)

		const result = await service.getLedger(payload)

		expect(ledgerResource.submit).toHaveBeenCalledWith(payload)
		expect(result).toEqual(response)
	})
})
