import { apiUpload } from '@/lib/client'
import { apiMethod } from '@/resources/frappe'
import type { UploadProgressCallback } from '@/lib/uploadProgress'

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
	options: { onProgress?: UploadProgressCallback } = {}
): Promise<SubmitStudentTaskSubmissionResponse> {
	const files = (payload.files || []).filter(Boolean)
	if (files.length) {
		const formData = new FormData()
		formData.append('task_outcome', payload.task_outcome.trim())
		if (payload.text_content?.trim()) {
			formData.append('text_content', payload.text_content.trim())
		}
		if (payload.link_url?.trim()) {
			formData.append('link_url', payload.link_url.trim())
		}
		for (const file of files) {
			formData.append('files', file, file.name)
		}
		return apiUpload<SubmitStudentTaskSubmissionResponse>(SUBMIT_TASK_SUBMISSION_METHOD, formData, options)
	}

	return apiMethod<SubmitStudentTaskSubmissionResponse>(SUBMIT_TASK_SUBMISSION_METHOD, payload)
}
