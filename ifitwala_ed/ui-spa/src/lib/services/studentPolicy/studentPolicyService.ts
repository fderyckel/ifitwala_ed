// ui-spa/src/lib/services/studentPolicy/studentPolicyService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as AcknowledgeStudentPolicyRequest,
	Response as AcknowledgeStudentPolicyResponse,
} from '@/types/contracts/student/acknowledge_student_policy'
import type {
	Request as GetStudentPolicyOverviewRequest,
	Response as GetStudentPolicyOverviewResponse,
} from '@/types/contracts/student/get_student_policy_overview'

const GET_METHOD = 'ifitwala_ed.api.student_policy.get_student_policy_overview'
const ACK_METHOD = 'ifitwala_ed.api.student_policy.acknowledge_student_policy'

export async function getStudentPolicyOverview(
	payload: GetStudentPolicyOverviewRequest = {}
): Promise<GetStudentPolicyOverviewResponse> {
	return apiMethod<GetStudentPolicyOverviewResponse>(GET_METHOD, payload)
}

export async function acknowledgeStudentPolicy(
	payload: AcknowledgeStudentPolicyRequest
): Promise<AcknowledgeStudentPolicyResponse> {
	return apiMethod<AcknowledgeStudentPolicyResponse>(ACK_METHOD, payload)
}
