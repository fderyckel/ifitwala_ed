// ifitwala_ed/ui-spa/src/lib/__tests__/studentCourseDetail.test.ts

import { describe, expect, it } from 'vitest'

import {
	buildLessonSequence,
	getAdjacentLessonRefs,
	resolveActiveContext,
} from '@/lib/studentCourseDetail'
import type { Response as StudentCourseDetailResponse } from '@/types/contracts/student_hub/get_student_course_detail'

function buildDetail(
	overrides: Partial<StudentCourseDetailResponse> = {}
): StudentCourseDetailResponse {
	return {
		meta: {
			generated_at: '2026-03-12T10:00:00',
			course_id: 'COURSE-1',
		},
		course: {
			course: 'COURSE-1',
			course_name: 'Biology',
			is_published: 1,
		},
		access: {
			student: 'STU-001',
			academic_years: ['2025-2026'],
			student_groups: [],
		},
		deep_link: {
			requested: {},
			resolved: {
				learning_unit: 'UNIT-1',
				lesson: 'LESSON-2',
				source: 'lesson',
			},
		},
		curriculum: {
			counts: {
				units: 2,
				lessons: 3,
				activities: 0,
				course_tasks: 0,
				unit_tasks: 0,
				lesson_tasks: 0,
				deliveries: 0,
			},
			course_tasks: [],
			units: [
				{
					name: 'UNIT-1',
					unit_name: 'Unit 1',
					is_published: 1,
					linked_tasks: [],
					lessons: [
						{
							name: 'LESSON-1',
							learning_unit: 'UNIT-1',
							title: 'Lesson 1',
							is_published: 1,
							linked_tasks: [],
							lesson_activities: [],
						},
						{
							name: 'LESSON-2',
							learning_unit: 'UNIT-1',
							title: 'Lesson 2',
							is_published: 1,
							linked_tasks: [],
							lesson_activities: [],
						},
					],
				},
				{
					name: 'UNIT-2',
					unit_name: 'Unit 2',
					is_published: 1,
					linked_tasks: [],
					lessons: [
						{
							name: 'LESSON-3',
							learning_unit: 'UNIT-2',
							title: 'Lesson 3',
							is_published: 1,
							linked_tasks: [],
							lesson_activities: [],
						},
					],
				},
			],
		},
		...overrides,
	}
}

describe('studentCourseDetail helpers', () => {
	it('builds a flattened lesson sequence in curriculum order', () => {
		const detail = buildDetail()

		expect(buildLessonSequence(detail.curriculum.units).map(ref => ref.lesson.name)).toEqual([
			'LESSON-1',
			'LESSON-2',
			'LESSON-3',
		])
	})

	it('resolves active context from deep-link lesson', () => {
		const detail = buildDetail()

		const resolved = resolveActiveContext(detail)

		expect(resolved.activeUnit?.name).toBe('UNIT-1')
		expect(resolved.activeLesson?.name).toBe('LESSON-2')
	})

	it('prefers explicit route overrides over payload deep-link context', () => {
		const detail = buildDetail()

		const resolved = resolveActiveContext(detail, {
			learning_unit: 'UNIT-2',
			lesson: 'LESSON-3',
		})

		expect(resolved.activeUnit?.name).toBe('UNIT-2')
		expect(resolved.activeLesson?.name).toBe('LESSON-3')
	})

	it('falls back to the first lesson of the requested unit when lesson is absent', () => {
		const detail = buildDetail({
			deep_link: {
				requested: {
					learning_unit: 'UNIT-2',
				},
				resolved: {
					learning_unit: 'UNIT-2',
					source: 'learning_unit',
				},
			},
		})

		const resolved = resolveActiveContext(detail)

		expect(resolved.activeUnit?.name).toBe('UNIT-2')
		expect(resolved.activeLesson?.name).toBe('LESSON-3')
	})

	it('returns adjacent lessons across unit boundaries', () => {
		const detail = buildDetail()

		const adjacent = getAdjacentLessonRefs(detail.curriculum.units, 'LESSON-2')

		expect(adjacent.previous?.lesson.name).toBe('LESSON-1')
		expect(adjacent.next?.lesson.name).toBe('LESSON-3')
	})
})
