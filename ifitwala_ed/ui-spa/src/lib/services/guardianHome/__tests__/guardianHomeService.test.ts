// ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts

import { describe, expect, it, vi } from 'vitest'

const { apiMethodMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

import {
	getGuardianHomeSnapshot,
	getGuardianStudentLearningBrief,
} from '@/lib/services/guardianHome/guardianHomeService'

describe('guardianHomeService', () => {
	it('uses canonical method + payload shape', async () => {
		apiMethodMock.mockResolvedValue({ zones: {} })

		await getGuardianHomeSnapshot({ anchor_date: '2026-02-12' } as any)

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.guardian_home.get_guardian_home_snapshot',
			{ anchor_date: '2026-02-12' }
		)
	})

	it('defaults to empty payload', async () => {
		apiMethodMock.mockResolvedValue({ zones: {} })

		await getGuardianHomeSnapshot()

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.guardian_home.get_guardian_home_snapshot',
			{}
		)
	})

	it('calls the guardian student learning brief endpoint with the expected payload', async () => {
		apiMethodMock.mockResolvedValue({ course_briefs: [] })

		await getGuardianStudentLearningBrief({ student_id: 'STU-1' } as any)

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.guardian_home.get_guardian_student_learning_brief',
			{ student_id: 'STU-1' }
		)
	})
})
