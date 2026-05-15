import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetGuardianCalendarOverlayRequest,
	Response as GetGuardianCalendarOverlayResponse,
} from '@/types/contracts/guardian/get_guardian_calendar_overlay'

const METHOD = 'ifitwala_ed.api.guardian_calendar.get_guardian_calendar_overlay'

export async function getGuardianCalendarOverlay(
	payload: GetGuardianCalendarOverlayRequest = {}
): Promise<GetGuardianCalendarOverlayResponse> {
	return apiMethod<GetGuardianCalendarOverlayResponse>(METHOD, payload)
}
