// ui-spa/src/lib/services/guardianHome/guardianHomeService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetGuardianHomeSnapshotRequest,
	Response as GetGuardianHomeSnapshotResponse,
} from '@/types/contracts/guardian/get_guardian_home_snapshot'
import type {
	Request as GetGuardianStudentLearningBriefRequest,
	Response as GetGuardianStudentLearningBriefResponse,
} from '@/types/contracts/guardian/get_guardian_student_learning_brief'

const METHOD = 'ifitwala_ed.api.guardian_home.get_guardian_home_snapshot'
const STUDENT_LEARNING_BRIEF_METHOD =
	'ifitwala_ed.api.guardian_home.get_guardian_student_learning_brief'

export async function getGuardianHomeSnapshot(
	payload: GetGuardianHomeSnapshotRequest = {}
): Promise<GetGuardianHomeSnapshotResponse> {
	return apiMethod<GetGuardianHomeSnapshotResponse>(METHOD, payload)
}

export async function getGuardianStudentLearningBrief(
	payload: GetGuardianStudentLearningBriefRequest
): Promise<GetGuardianStudentLearningBriefResponse> {
	return apiMethod<GetGuardianStudentLearningBriefResponse>(STUDENT_LEARNING_BRIEF_METHOD, payload)
}
