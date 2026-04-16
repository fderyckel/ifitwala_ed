import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetGuardianCommunicationCenterRequest,
	Response as GetGuardianCommunicationCenterResponse,
} from '@/types/contracts/guardian/get_guardian_communication_center'

const METHOD = 'ifitwala_ed.api.guardian_communications.get_guardian_communication_center'

export async function getGuardianCommunicationCenter(
	payload: GetGuardianCommunicationCenterRequest = {}
): Promise<GetGuardianCommunicationCenterResponse> {
	return apiMethod<GetGuardianCommunicationCenterResponse>(METHOD, payload)
}
