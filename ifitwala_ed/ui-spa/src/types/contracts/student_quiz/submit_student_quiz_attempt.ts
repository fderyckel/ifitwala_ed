import type { StudentQuizReview } from './open_student_quiz_session'
import type { StudentQuizAttemptResponse } from './save_student_quiz_attempt'

export type Request = {
	attempt_id: string
	responses: StudentQuizAttemptResponse[]
}

export type Response = {
	attempt: {
		name: string
		status: string
		score?: number | null
		percentage?: number | null
		passed: number
		requires_manual_review: number
		submitted_on?: string | null
	}
	review: StudentQuizReview
}
