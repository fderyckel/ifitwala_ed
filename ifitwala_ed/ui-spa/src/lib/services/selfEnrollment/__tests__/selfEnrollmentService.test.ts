// ui-spa/src/lib/services/selfEnrollment/__tests__/selfEnrollmentService.test.ts

import { describe, expect, it, vi } from 'vitest'

const { apiMethodMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

import {
	getSelfEnrollmentChoiceState,
	getSelfEnrollmentPortalBoard,
	saveSelfEnrollmentChoices,
	submitSelfEnrollmentChoices,
} from '@/lib/services/selfEnrollment/selfEnrollmentService'

describe('selfEnrollmentService', () => {
	it('uses the canonical board method + flat payload', async () => {
		apiMethodMock.mockResolvedValue({ windows: [] })

		await getSelfEnrollmentPortalBoard({ include_closed: 1 } as any)

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.self_enrollment.get_self_enrollment_portal_board',
			{ include_closed: 1 }
		)
	})

	it('uses the canonical choice-state method', async () => {
		apiMethodMock.mockResolvedValue({ request: { name: 'PER-1' } })

		await getSelfEnrollmentChoiceState({ selection_window: 'SEW-1', student: 'STU-1' })

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.self_enrollment.get_self_enrollment_choice_state',
			{ selection_window: 'SEW-1', student: 'STU-1' }
		)
	})

	it('uses the canonical save + submit methods', async () => {
		apiMethodMock.mockResolvedValue({ request: { name: 'PER-1' } })

		await saveSelfEnrollmentChoices({
			selection_window: 'SEW-1',
			student: 'STU-1',
			courses: [{ course: 'COURSE-1' }],
		} as any)
		await submitSelfEnrollmentChoices({
			selection_window: 'SEW-1',
			student: 'STU-1',
			courses: [{ course: 'COURSE-1' }],
		} as any)

		expect(apiMethodMock).toHaveBeenNthCalledWith(
			1,
			'ifitwala_ed.api.self_enrollment.save_self_enrollment_choices',
			{
				selection_window: 'SEW-1',
				student: 'STU-1',
				courses: [{ course: 'COURSE-1' }],
			}
		)
		expect(apiMethodMock).toHaveBeenNthCalledWith(
			2,
			'ifitwala_ed.api.self_enrollment.submit_self_enrollment_choices',
			{
				selection_window: 'SEW-1',
				student: 'STU-1',
				courses: [{ course: 'COURSE-1' }],
			}
		)
	})
})
