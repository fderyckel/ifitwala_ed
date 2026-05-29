import { beforeEach, describe, expect, it, vi } from 'vitest'

type ResourceRecord = {
	config: {
		url?: string
		method?: string
		auto?: boolean
	}
	submit: ReturnType<typeof vi.fn>
}

const { apiMethodMock, apiMock, createResourceMock, emitMock, resourceRecords } = vi.hoisted(() => {
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
	const apiMethodMock = vi.fn()
	const apiMock = vi.fn()
	const emitMock = vi.fn()
	return { apiMethodMock, apiMock, createResourceMock, emitMock, resourceRecords }
})

vi.mock('frappe-ui', () => ({
	createResource: createResourceMock,
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

vi.mock('@/lib/client', () => ({
	api: apiMock,
}))

vi.mock('@/lib/uiSignals', () => ({
	uiSignals: {
		emit: emitMock,
	},
	SIGNAL_CALENDAR_INVALIDATE: 'calendar:invalidate',
	SIGNAL_ORG_COMMUNICATION_INVALIDATE: 'org_communication:invalidate',
}))

import {
	createMeetingQuick,
	createSchoolEventQuick,
	getEventQuickCreateOptions,
	searchMeetingAttendees,
} from '@/lib/services/calendar/eventQuickCreateService'

describe('eventQuickCreateService', () => {
	beforeEach(() => {
		apiMethodMock.mockReset()
		apiMock.mockReset()
		emitMock.mockClear()
		for (const record of resourceRecords) {
			record.submit.mockReset()
		}
	})

	it('keeps option loading on the calendar options endpoint', async () => {
		resourceRecords[0].submit.mockResolvedValue({ can_create_meeting: true })

		await getEventQuickCreateOptions()

		expect(resourceRecords[0].config).toMatchObject({
			url: 'ifitwala_ed.api.calendar.get_event_quick_create_options',
			method: 'POST',
			auto: false,
		})
		expect(resourceRecords[0].submit).toHaveBeenCalledWith({})
	})

	it('submits meeting quick create as a flat apiMethod payload and invalidates calendars', async () => {
		apiMethodMock.mockResolvedValue({
			ok: true,
			status: 'created',
			idempotent: false,
			doctype: 'Meeting',
			name: 'MTG-26-05-0001',
			title: 'Weekly Check-in',
			start: '2026-05-29T08:00:00+07:00',
			end: '2026-05-29T09:00:00+07:00',
			target_doctype: 'Meeting',
			target_name: 'MTG-26-05-0001',
			target_url: '/desk/meeting/MTG-26-05-0001',
			target_label: 'Weekly Check-in',
		})

		const payload = {
			client_request_id: 'meeting-req-1',
			meeting_name: 'Weekly Check-in',
			date: '2026-05-29',
			start_time: '08:00',
			end_time: '09:00',
			school: 'ISS',
			team: null,
			location: null,
			meeting_category: null,
			virtual_meeting_link: null,
			agenda: null,
			visibility_scope: null,
			participants: [{ user: 'teacher@example.com', kind: 'employee' as const, label: 'Teacher' }],
		}

		await createMeetingQuick(payload)

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.calendar.create_meeting_quick',
			payload
		)
		expect(emitMock).toHaveBeenCalledWith('calendar:invalidate')
	})

	it('submits school event quick create through the same canonical request wrapper', async () => {
		apiMethodMock.mockResolvedValue({
			ok: true,
			status: 'created',
			idempotent: false,
			doctype: 'School Event',
			name: 'SE-26-05-0001',
			title: 'Parent Workshop',
			start: '2026-05-29T08:00:00+07:00',
			end: '2026-05-29T09:00:00+07:00',
			target_doctype: 'School Event',
			target_name: 'SE-26-05-0001',
			target_url: '/desk/school-event/SE-26-05-0001',
			target_label: 'Parent Workshop',
			published_communication: {
				name: 'COMM-1',
				title: 'Parent Workshop',
				status: 'created',
			},
		})

		const payload = {
			client_request_id: 'event-req-1',
			subject: 'Parent Workshop',
			school: 'ISS',
			starts_on: '2026-05-29T08:00',
			ends_on: '2026-05-29T09:00',
			audience_type: 'All Guardians',
			event_category: 'Parent Engagement',
			all_day: 0,
			location: null,
			description: null,
			audience_team: null,
			audience_student_group: null,
			include_guardians: 0,
			include_students: 0,
			publish_announcement: 1,
			announcement_message: 'Workshop details',
			custom_participants: null,
		}

		await createSchoolEventQuick(payload)

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.calendar.create_school_event_quick',
			payload
		)
		expect(emitMock).toHaveBeenCalledWith('calendar:invalidate')
		expect(emitMock).toHaveBeenCalledWith('org_communication:invalidate', {
			names: ['COMM-1'],
			reason: 'school_event_quick_publish',
		})
	})

	it('keeps attendee search on the existing attendee endpoint', async () => {
		apiMock.mockResolvedValue({ results: [] })

		await searchMeetingAttendees({ query: 'tea', attendee_kinds: ['employee'], limit: 8 })

		expect(apiMock).toHaveBeenCalledWith('ifitwala_ed.api.calendar.search_meeting_attendees', {
			query: 'tea',
			attendee_kinds: ['employee'],
			limit: 8,
		})
	})
})
