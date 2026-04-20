import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetStudentTaskSubmissionRequest,
	Response as GetStudentTaskSubmissionResponse,
} from '@/types/contracts/student_learning/get_student_task_submission'
import type {
	Request as SubmitStudentTaskSubmissionRequest,
	Response as SubmitStudentTaskSubmissionResponse,
} from '@/types/contracts/student_learning/submit_student_task_submission'

const GET_LATEST_SUBMISSION_METHOD = 'ifitwala_ed.api.task_submission.get_latest_submission'
const SUBMIT_TASK_SUBMISSION_METHOD = 'ifitwala_ed.api.task_submission.create_or_resubmit'

export async function getStudentTaskSubmission(
	payload: GetStudentTaskSubmissionRequest,
): Promise<GetStudentTaskSubmissionResponse> {
	return apiMethod<GetStudentTaskSubmissionResponse>(GET_LATEST_SUBMISSION_METHOD, {
		outcome_id: payload.outcome_id,
	})
}

export async function submitStudentTaskSubmission(
	payload: SubmitStudentTaskSubmissionRequest,
): Promise<SubmitStudentTaskSubmissionResponse> {
	return apiMethod<SubmitStudentTaskSubmissionResponse>(SUBMIT_TASK_SUBMISSION_METHOD, payload)
}
