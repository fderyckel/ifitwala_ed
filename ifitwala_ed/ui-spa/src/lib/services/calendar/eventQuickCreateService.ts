// ifitwala_ed/ui-spa/src/lib/services/calendar/eventQuickCreateService.ts

import { createResource } from 'frappe-ui'

import { SIGNAL_CALENDAR_INVALIDATE, uiSignals } from '@/lib/uiSignals'

import type {
	Request as CreateMeetingQuickRequest,
	Response as CreateMeetingQuickResponse,
} from '@/types/contracts/calendar/create_meeting_quick'
import type {
	Request as CreateSchoolEventQuickRequest,
	Response as CreateSchoolEventQuickResponse,
} from '@/types/contracts/calendar/create_school_event_quick'
import type {
	Request as GetEventQuickCreateOptionsRequest,
	Response as GetEventQuickCreateOptionsResponse,
} from '@/types/contracts/calendar/get_event_quick_create_options'

const getOptionsResource = createResource<GetEventQuickCreateOptionsResponse>({
	url: 'ifitwala_ed.api.calendar.get_event_quick_create_options',
	method: 'POST',
	auto: false,
})

const createMeetingQuickResource = createResource<CreateMeetingQuickResponse>({
	url: 'ifitwala_ed.api.calendar.create_meeting_quick',
	method: 'POST',
	auto: false,
})

const createSchoolEventQuickResource = createResource<CreateSchoolEventQuickResponse>({
	url: 'ifitwala_ed.api.calendar.create_school_event_quick',
	method: 'POST',
	auto: false,
})

function isSemanticSuccess(status: string | null | undefined, ok: boolean | null | undefined): boolean {
	if (!ok) return false
	return status === 'created' || status === 'already_processed'
}

export async function getEventQuickCreateOptions(
	payload: GetEventQuickCreateOptionsRequest = {}
): Promise<GetEventQuickCreateOptionsResponse> {
	return getOptionsResource.submit(payload)
}

export async function createMeetingQuick(
	payload: CreateMeetingQuickRequest
): Promise<CreateMeetingQuickResponse> {
	const response = await createMeetingQuickResource.submit(payload)
	if (isSemanticSuccess(response?.status, response?.ok)) {
		uiSignals.emit(SIGNAL_CALENDAR_INVALIDATE)
	}
	return response
}

export async function createSchoolEventQuick(
	payload: CreateSchoolEventQuickRequest
): Promise<CreateSchoolEventQuickResponse> {
	const response = await createSchoolEventQuickResource.submit(payload)
	if (isSemanticSuccess(response?.status, response?.ok)) {
		uiSignals.emit(SIGNAL_CALENDAR_INVALIDATE)
	}
	return response
}
