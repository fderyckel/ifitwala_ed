import { describe, expect, it, vi } from 'vitest'

const { apiMethodMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

import {
	openStudentQuizSession,
	saveStudentQuizAttempt,
	submitStudentQuizAttempt,
} from '@/lib/services/student/studentQuizService'

describe('studentQuizService', () => {
	it('opens quiz session with direct payload', async () => {
		apiMethodMock.mockResolvedValue({ mode: 'attempt', session: { attempt_id: 'QAT-1' } })

		await openStudentQuizSession({ task_delivery: 'TDL-QUIZ-1' })

		expect(apiMethodMock).toHaveBeenCalledWith('ifitwala_ed.api.quiz.open_session', {
			task_delivery: 'TDL-QUIZ-1',
		})
	})

	it('saves quiz attempt with direct payload', async () => {
		apiMethodMock.mockResolvedValue({ attempt: 'QAT-1', status: 'In Progress' })

		await saveStudentQuizAttempt({
			attempt_id: 'QAT-1',
			responses: [{ item_id: 'QAI-1', selected_option_ids: ['OPT-1'] }],
		})

		expect(apiMethodMock).toHaveBeenCalledWith('ifitwala_ed.api.quiz.save_attempt', {
			attempt_id: 'QAT-1',
			responses: [{ item_id: 'QAI-1', selected_option_ids: ['OPT-1'] }],
		})
	})

	it('submits quiz attempt with direct payload', async () => {
		apiMethodMock.mockResolvedValue({ attempt: { name: 'QAT-1', status: 'Submitted' } })

		await submitStudentQuizAttempt({
			attempt_id: 'QAT-1',
			responses: [{ item_id: 'QAI-1', response_text: 'mitosis' }],
		})

		expect(apiMethodMock).toHaveBeenCalledWith('ifitwala_ed.api.quiz.submit_attempt', {
			attempt_id: 'QAT-1',
			responses: [{ item_id: 'QAI-1', response_text: 'mitosis' }],
		})
	})
})
