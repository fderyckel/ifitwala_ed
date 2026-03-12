// ui-spa/src/lib/services/student/studentLearningHubService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetStudentCourseDetailRequest,
	Response as GetStudentCourseDetailResponse,
} from '@/types/contracts/student_hub/get_student_course_detail'
import type {
	Request as GetStudentHubHomeRequest,
	Response as GetStudentHubHomeResponse,
} from '@/types/contracts/student_hub/get_student_hub_home'

const HOME_METHOD = 'ifitwala_ed.api.courses.get_student_hub_home'
const COURSE_DETAIL_METHOD = 'ifitwala_ed.api.courses.get_student_course_detail'

export async function getStudentHubHome(
	payload: GetStudentHubHomeRequest = {}
): Promise<GetStudentHubHomeResponse> {
	return apiMethod<GetStudentHubHomeResponse>(HOME_METHOD, payload)
}

export async function getStudentCourseDetail(
	payload: GetStudentCourseDetailRequest
): Promise<GetStudentCourseDetailResponse> {
	return apiMethod<GetStudentCourseDetailResponse>(COURSE_DETAIL_METHOD, payload)
}
