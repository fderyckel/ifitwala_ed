import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetStudentReleasedFeedbackDetailRequest,
	Response as GetStudentReleasedFeedbackDetailResponse,
} from '@/types/contracts/assessment/get_student_released_feedback_detail'
import type {
	Request as GetGuardianReleasedFeedbackDetailRequest,
	Response as GetGuardianReleasedFeedbackDetailResponse,
} from '@/types/contracts/assessment/get_guardian_released_feedback_detail'
import type {
	Request as SaveStudentFeedbackReplyRequest,
	Response as SaveStudentFeedbackReplyResponse,
} from '@/types/contracts/assessment/save_student_feedback_reply'
import type {
	Request as SaveStudentFeedbackThreadStateRequest,
	Response as SaveStudentFeedbackThreadStateResponse,
} from '@/types/contracts/assessment/save_student_feedback_thread_state'

const GET_STUDENT_RELEASED_FEEDBACK_DETAIL =
	'ifitwala_ed.api.released_feedback.get_student_released_feedback_detail'
const GET_GUARDIAN_RELEASED_FEEDBACK_DETAIL =
	'ifitwala_ed.api.released_feedback.get_guardian_released_feedback_detail'
const SAVE_STUDENT_FEEDBACK_REPLY = 'ifitwala_ed.api.released_feedback.save_student_feedback_reply'
const SAVE_STUDENT_FEEDBACK_THREAD_STATE =
	'ifitwala_ed.api.released_feedback.save_student_feedback_thread_state'

export async function getStudentReleasedFeedbackDetail(
	payload: GetStudentReleasedFeedbackDetailRequest,
): Promise<GetStudentReleasedFeedbackDetailResponse> {
	return apiMethod<GetStudentReleasedFeedbackDetailResponse>(GET_STUDENT_RELEASED_FEEDBACK_DETAIL, {
		outcome_id: payload.outcome_id,
	})
}

export async function getGuardianReleasedFeedbackDetail(
	payload: GetGuardianReleasedFeedbackDetailRequest,
): Promise<GetGuardianReleasedFeedbackDetailResponse> {
	return apiMethod<GetGuardianReleasedFeedbackDetailResponse>(GET_GUARDIAN_RELEASED_FEEDBACK_DETAIL, {
		outcome_id: payload.outcome_id,
	})
}

export async function saveStudentFeedbackReply(
	payload: SaveStudentFeedbackReplyRequest,
): Promise<SaveStudentFeedbackReplyResponse> {
	return apiMethod<SaveStudentFeedbackReplyResponse>(SAVE_STUDENT_FEEDBACK_REPLY, payload)
}

export async function saveStudentFeedbackThreadState(
	payload: SaveStudentFeedbackThreadStateRequest,
): Promise<SaveStudentFeedbackThreadStateResponse> {
	return apiMethod<SaveStudentFeedbackThreadStateResponse>(SAVE_STUDENT_FEEDBACK_THREAD_STATE, payload)
}
