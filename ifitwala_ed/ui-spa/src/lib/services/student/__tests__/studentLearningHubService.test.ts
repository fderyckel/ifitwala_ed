// ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts

import { describe, expect, it, vi } from 'vitest'

const { apiMethodMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

import {
	getStudentCommunicationCenter,
	getStudentCoursesData,
	getStudentHubHome,
	getStudentLearningSpace,
} from '@/lib/services/student/studentLearningHubService'

describe('studentLearningHubService', () => {
	it('uses canonical method + direct payload for courses', async () => {
		apiMethodMock.mockResolvedValue({ courses: [] })

		await getStudentCoursesData({
			academic_year: '2025-2026',
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.courses.get_courses_data',
			{
				academic_year: '2025-2026',
			}
		)
	})

	it('uses canonical method + empty payload for home', async () => {
		apiMethodMock.mockResolvedValue({ learning: { today_classes: [] } })

		await getStudentHubHome()

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.courses.get_student_hub_home',
			{}
		)
	})

	it('uses canonical method + direct payload for learning space', async () => {
		apiMethodMock.mockResolvedValue({ curriculum: { units: [] } })

		await getStudentLearningSpace({
			course_id: 'COURSE-1',
			student_group: 'GROUP-1',
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.teaching_plans.get_student_learning_space',
			{
				course_id: 'COURSE-1',
				student_group: 'GROUP-1',
			}
		)
	})

	it('uses canonical method + direct payload for the communication center', async () => {
		apiMethodMock.mockResolvedValue({ items: [] })

		await getStudentCommunicationCenter({
			source: 'course',
			course_id: 'COURSE-1',
			student_group: 'GROUP-1',
			item: 'org::COMM-1',
			start: 0,
			page_length: 24,
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.student_communications.get_student_communication_center',
			{
				source: 'course',
				course_id: 'COURSE-1',
				student_group: 'GROUP-1',
				item: 'org::COMM-1',
				start: 0,
				page_length: 24,
			}
		)
	})
})
