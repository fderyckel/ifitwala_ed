// ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts

import { describe, expect, it, vi } from 'vitest'

const { apiMethodMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

import {
	getStaffClassPlanningSurface,
	saveClassSession,
} from '@/lib/services/staff/staffTeachingService'

describe('staffTeachingService', () => {
	it('uses the canonical method for the staff planning surface', async () => {
		apiMethodMock.mockResolvedValue({ curriculum: { units: [], session_count: 0 } })

		await getStaffClassPlanningSurface({
			student_group: 'GROUP-1',
			class_teaching_plan: 'CLASS-PLAN-1',
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.teaching_plans.get_staff_class_planning_surface',
			{
				student_group: 'GROUP-1',
				class_teaching_plan: 'CLASS-PLAN-1',
			}
		)
	})

	it('serializes activities when saving a class session', async () => {
		apiMethodMock.mockResolvedValue({ class_session: 'CLASS-SESSION-1' })

		await saveClassSession({
			class_teaching_plan: 'CLASS-PLAN-1',
			unit_plan: 'UNIT-1',
			title: 'Evidence walk',
			activities: [
				{
					title: 'Observe',
					activity_type: 'Discuss',
					estimated_minutes: 10,
				},
			],
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.teaching_plans.save_class_session',
			{
				class_teaching_plan: 'CLASS-PLAN-1',
				unit_plan: 'UNIT-1',
				title: 'Evidence walk',
				activities_json: JSON.stringify([
					{
						title: 'Observe',
						activity_type: 'Discuss',
						estimated_minutes: 10,
					},
				]),
			}
		)
	})
})
