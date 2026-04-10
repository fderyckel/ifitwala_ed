// ui-spa/src/lib/services/student/studentLearningHubService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetStudentCoursesDataRequest,
	Response as GetStudentCoursesDataResponse,
} from '@/types/contracts/student_hub/get_student_courses_data'
import type {
	Request as GetStudentHubHomeRequest,
	Response as GetStudentHubHomeResponse,
} from '@/types/contracts/student_hub/get_student_hub_home'
import type {
	Request as GetStudentCommunicationCenterRequest,
	Response as GetStudentCommunicationCenterResponse,
} from '@/types/contracts/student_communication/get_student_communication_center'
import type {
	Request as GetStudentCourseCommunicationDrawerRequest,
	Response as GetStudentCourseCommunicationDrawerResponse,
} from '@/types/contracts/student_communication/get_student_course_communication_drawer'
import type {
	Request as GetStudentLearningSpaceRequest,
	Response as GetStudentLearningSpaceResponse,
} from '@/types/contracts/student_learning/get_student_learning_space'

const HOME_METHOD = 'ifitwala_ed.api.courses.get_student_hub_home'
const COURSES_METHOD = 'ifitwala_ed.api.courses.get_courses_data'
const LEARNING_SPACE_METHOD = 'ifitwala_ed.api.teaching_plans.get_student_learning_space'
const COMMUNICATION_CENTER_METHOD = 'ifitwala_ed.api.student_communications.get_student_communication_center'
const COURSE_COMMUNICATION_DRAWER_METHOD =
	'ifitwala_ed.api.student_communications.get_student_course_communication_drawer'

export async function getStudentCoursesData(
	payload: GetStudentCoursesDataRequest = {}
): Promise<GetStudentCoursesDataResponse> {
	return apiMethod<GetStudentCoursesDataResponse>(COURSES_METHOD, payload)
}

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

export async function getStudentCommunicationCenter(
	payload: GetStudentCommunicationCenterRequest = {}
): Promise<GetStudentCommunicationCenterResponse> {
	return apiMethod<GetStudentCommunicationCenterResponse>(COMMUNICATION_CENTER_METHOD, payload)
}

export async function getStudentCourseCommunicationDrawer(
	payload: GetStudentCourseCommunicationDrawerRequest
): Promise<GetStudentCourseCommunicationDrawerResponse> {
	return apiMethod<GetStudentCourseCommunicationDrawerResponse>(
		COURSE_COMMUNICATION_DRAWER_METHOD,
		payload
	)
}
