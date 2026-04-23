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

import { createClassHubService } from '@/lib/classHubService'

describe('classHubService', () => {
	beforeEach(() => {
		for (const record of resourceRecords) {
			record.submit.mockReset()
		}
	})

	it('returns the canonical staff-home entry payload from the shared resource boundary', async () => {
		const service = createClassHubService()
		const staffHomeEntry = resourceRecords.find(
			record => record.config.url === 'ifitwala_ed.api.class_hub.resolve_staff_home_entry'
		)

		if (!staffHomeEntry) throw new Error('staffHomeEntryResource was not created')

		staffHomeEntry.submit.mockResolvedValue({
			status: 'choose',
			message: 'Choose the class hub you want to open.',
			groups: [
				{
					student_group: 'SG-IMS-COURSE',
					student_group_name: 'IMS Grade 5',
					title: 'IMS Grade 5 - Science',
					academic_year: '2026-2027',
					course: 'Science',
				},
			],
		})

		const payload = await service.resolveStaffHomeEntry()

		expect(staffHomeEntry.submit).toHaveBeenCalledWith({})
		expect(payload).toEqual({
			status: 'choose',
			message: 'Choose the class hub you want to open.',
			groups: [
				{
					student_group: 'SG-IMS-COURSE',
					student_group_name: 'IMS Grade 5',
					title: 'IMS Grade 5 - Science',
					academic_year: '2026-2027',
					course: 'Science',
				},
			],
		})
	})
})
