import { afterEach, describe, expect, it, vi } from 'vitest'

const { apiMethodMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

import { markStudentTaskComplete } from '@/lib/services/student/studentTaskCompletionService'

afterEach(() => {
	apiMethodMock.mockReset()
})

describe('studentTaskCompletionService', () => {
	it('uses the canonical assign-only completion method', async () => {
		apiMethodMock.mockResolvedValue({
			task_outcome: 'OUT-1',
			is_complete: 1,
			completed_on: '2026-04-22 09:15:00',
		})

		await markStudentTaskComplete({
			task_outcome: 'OUT-1',
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.task_completion.mark_assign_only_complete',
			{
				task_outcome: 'OUT-1',
			}
		)
	})
})
