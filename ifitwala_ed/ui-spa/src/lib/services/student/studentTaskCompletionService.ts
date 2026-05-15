import { apiMethod } from '@/resources/frappe'

import type {
	Request as MarkStudentTaskCompleteRequest,
	Response as MarkStudentTaskCompleteResponse,
} from '@/types/contracts/student_learning/mark_student_task_complete'

const MARK_ASSIGN_ONLY_COMPLETE_METHOD = 'ifitwala_ed.api.task_completion.mark_assign_only_complete'

export async function markStudentTaskComplete(
	payload: MarkStudentTaskCompleteRequest
): Promise<MarkStudentTaskCompleteResponse> {
	return apiMethod<MarkStudentTaskCompleteResponse>(MARK_ASSIGN_ONLY_COMPLETE_METHOD, payload)
}
