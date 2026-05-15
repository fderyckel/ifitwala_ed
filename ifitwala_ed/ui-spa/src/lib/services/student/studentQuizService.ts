import { apiMethod } from '@/resources/frappe'

import type {
	Request as OpenStudentQuizSessionRequest,
	Response as OpenStudentQuizSessionResponse,
} from '@/types/contracts/student_quiz/open_student_quiz_session'
import type {
	Request as SaveStudentQuizAttemptRequest,
	Response as SaveStudentQuizAttemptResponse,
} from '@/types/contracts/student_quiz/save_student_quiz_attempt'
import type {
	Request as SubmitStudentQuizAttemptRequest,
	Response as SubmitStudentQuizAttemptResponse,
} from '@/types/contracts/student_quiz/submit_student_quiz_attempt'

const OPEN_METHOD = 'ifitwala_ed.api.quiz.open_session'
const SAVE_METHOD = 'ifitwala_ed.api.quiz.save_attempt'
const SUBMIT_METHOD = 'ifitwala_ed.api.quiz.submit_attempt'

export async function openStudentQuizSession(
	payload: OpenStudentQuizSessionRequest
): Promise<OpenStudentQuizSessionResponse> {
	return apiMethod<OpenStudentQuizSessionResponse>(OPEN_METHOD, payload)
}

export async function saveStudentQuizAttempt(
	payload: SaveStudentQuizAttemptRequest
): Promise<SaveStudentQuizAttemptResponse> {
	return apiMethod<SaveStudentQuizAttemptResponse>(SAVE_METHOD, payload)
}

export async function submitStudentQuizAttempt(
	payload: SubmitStudentQuizAttemptRequest
): Promise<SubmitStudentQuizAttemptResponse> {
	return apiMethod<SubmitStudentQuizAttemptResponse>(SUBMIT_METHOD, payload)
}
