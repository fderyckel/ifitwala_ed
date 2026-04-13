import { describe, expect, it } from 'vitest'

import {
	MISSING_CLASS_COURSE_MESSAGE,
	getPlanSessionBlockedReason,
	hasLinkedCourse,
	normalizePlanningSurfaceError,
} from '@/lib/planning/planningActionGuards'

describe('planningActionGuards', () => {
	it('blocks planning when the class has no linked course', () => {
		expect(hasLinkedCourse('')).toBe(false)
		expect(getPlanSessionBlockedReason(null)).toBe(MISSING_CLASS_COURSE_MESSAGE)
	})

	it('allows planning when the class has a linked course', () => {
		expect(hasLinkedCourse('COURSE-1')).toBe(true)
		expect(getPlanSessionBlockedReason('COURSE-1')).toBe('')
	})

	it('normalizes the missing-course bootstrap error into an actionable message', () => {
		const error = new Error(
			'/api/method/ifitwala_ed.api.teaching_plans.get_staff_class_planning_surface ValidationError: This class is not linked to a course.'
		)

		expect(normalizePlanningSurfaceError(error)).toBe(MISSING_CLASS_COURSE_MESSAGE)
	})

	it('passes through unrelated planning errors', () => {
		expect(normalizePlanningSurfaceError(new Error('Request timed out.'))).toBe(
			'Request timed out.'
		)
	})
})
