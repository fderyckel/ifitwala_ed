// ui-spa/src/lib/services/guardianPolicy/guardianPolicyService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as AcknowledgeGuardianPolicyRequest,
	Response as AcknowledgeGuardianPolicyResponse,
} from '@/types/contracts/guardian/acknowledge_guardian_policy'
import type {
	Request as GetGuardianPolicyOverviewRequest,
	Response as GetGuardianPolicyOverviewResponse,
} from '@/types/contracts/guardian/get_guardian_policy_overview'

const GET_METHOD = 'ifitwala_ed.api.guardian_policy.get_guardian_policy_overview'
const ACK_METHOD = 'ifitwala_ed.api.guardian_policy.acknowledge_guardian_policy'

export async function getGuardianPolicyOverview(
	payload: GetGuardianPolicyOverviewRequest = {}
): Promise<GetGuardianPolicyOverviewResponse> {
	return apiMethod<GetGuardianPolicyOverviewResponse>(GET_METHOD, payload)
}

export async function acknowledgeGuardianPolicy(
	payload: AcknowledgeGuardianPolicyRequest
): Promise<AcknowledgeGuardianPolicyResponse> {
	return apiMethod<AcknowledgeGuardianPolicyResponse>(ACK_METHOD, payload)
}
