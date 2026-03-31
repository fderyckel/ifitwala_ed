// ui-spa/src/lib/services/student/studentLearningHubService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetStudentHubHomeRequest,
	Response as GetStudentHubHomeResponse,
} from '@/types/contracts/student_hub/get_student_hub_home'
import type {
	Request as GetStudentLearningSpaceRequest,
	Response as GetStudentLearningSpaceResponse,
} from '@/types/contracts/student_learning/get_student_learning_space'

const HOME_METHOD = 'ifitwala_ed.api.courses.get_student_hub_home'
const LEARNING_SPACE_METHOD = 'ifitwala_ed.api.teaching_plans.get_student_learning_space'

export async function getStudentHubHome(
	payload: GetStudentHubHomeRequest = {}
): Promise<GetStudentHubHomeResponse> {
	return apiMethod<GetStudentHubHomeResponse>(HOME_METHOD, payload)
}

export async function getStudentLearningSpace(
	payload: GetStudentLearningSpaceRequest
): Promise<GetStudentLearningSpaceResponse> {
	return apiMethod<GetStudentLearningSpaceResponse>(LEARNING_SPACE_METHOD, payload)
}
