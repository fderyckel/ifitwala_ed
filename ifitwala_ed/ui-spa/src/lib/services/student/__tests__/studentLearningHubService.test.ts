// ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts

import { describe, expect, it, vi } from 'vitest'

const { apiMethodMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

import {
	getStudentCourseDetail,
	getStudentHubHome,
} from '@/lib/services/student/studentLearningHubService'

describe('studentLearningHubService', () => {
	it('uses canonical method + empty payload for home', async () => {
		apiMethodMock.mockResolvedValue({ learning: { today_classes: [] } })

		await getStudentHubHome()

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.courses.get_student_hub_home',
			{}
		)
	})

	it('uses canonical method + direct payload for course detail', async () => {
		apiMethodMock.mockResolvedValue({ curriculum: { units: [] } })

		await getStudentCourseDetail({
			course_id: 'COURSE-1',
			lesson: 'LESSON-1',
			lesson_instance: 'LI-1',
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.courses.get_student_course_detail',
			{
				course_id: 'COURSE-1',
				lesson: 'LESSON-1',
				lesson_instance: 'LI-1',
			}
		)
	})
})
