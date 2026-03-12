// ifitwala_ed/ui-spa/src/lib/studentCourseDetail.ts

import type {
	Lesson,
	LearningUnit,
	Response as StudentCourseDetailResponse,
} from '@/types/contracts/student_hub/get_student_course_detail'

export type CourseLessonRef = {
	unit: LearningUnit
	lesson: Lesson
}

type RequestedContext = {
	learning_unit?: string
	lesson?: string
}

function asKey(value?: string | null): string {
	return typeof value === 'string' ? value.trim() : ''
}

export function buildLessonSequence(units: LearningUnit[]): CourseLessonRef[] {
	const sequence: CourseLessonRef[] = []

	for (const unit of units) {
		for (const lesson of unit.lessons || []) {
			sequence.push({ unit, lesson })
		}
	}

	return sequence
}

export function findUnitForLesson(
	units: LearningUnit[],
	lessonName?: string | null
): LearningUnit | null {
	const target = asKey(lessonName)
	if (!target) return null

	for (const unit of units) {
		if ((unit.lessons || []).some(lesson => lesson.name === target)) {
			return unit
		}
	}

	return null
}

function findUnitByName(units: LearningUnit[], unitName?: string | null): LearningUnit | null {
	const target = asKey(unitName)
	if (!target) return null
	return units.find(unit => unit.name === target) || null
}

function findLessonByName(unit: LearningUnit | null, lessonName?: string | null): Lesson | null {
	const target = asKey(lessonName)
	if (!unit || !target) return null
	return (unit.lessons || []).find(lesson => lesson.name === target) || null
}

export function resolveActiveContext(
	detail: StudentCourseDetailResponse | null,
	requested: RequestedContext = {}
): { activeUnit: LearningUnit | null; activeLesson: Lesson | null } {
	const units = detail?.curriculum?.units || []
	if (!units.length) {
		return { activeUnit: null, activeLesson: null }
	}

	const requestedUnit =
		asKey(requested.learning_unit) ||
		asKey(detail?.deep_link?.requested?.learning_unit) ||
		asKey(detail?.deep_link?.resolved?.learning_unit)
	const requestedLesson =
		asKey(requested.lesson) ||
		asKey(detail?.deep_link?.requested?.lesson) ||
		asKey(detail?.deep_link?.resolved?.lesson)

	let activeUnit =
		findUnitByName(units, requestedUnit) ||
		findUnitForLesson(units, requestedLesson) ||
		units[0] ||
		null

	let activeLesson =
		findLessonByName(activeUnit, requestedLesson) ||
		(activeUnit?.lessons || [])[0] ||
		null

	if (!activeLesson && requestedLesson) {
		const fallbackRef = buildLessonSequence(units).find(ref => ref.lesson.name === requestedLesson) || null
		if (fallbackRef) {
			activeUnit = fallbackRef.unit
			activeLesson = fallbackRef.lesson
		}
	}

	return { activeUnit, activeLesson }
}

export function getAdjacentLessonRefs(
	units: LearningUnit[],
	activeLessonName?: string | null
): { previous: CourseLessonRef | null; next: CourseLessonRef | null } {
	const target = asKey(activeLessonName)
	if (!target) {
		return { previous: null, next: null }
	}

	const sequence = buildLessonSequence(units)
	const index = sequence.findIndex(ref => ref.lesson.name === target)
	if (index === -1) {
		return { previous: null, next: null }
	}

	return {
		previous: index > 0 ? sequence[index - 1] : null,
		next: index < sequence.length - 1 ? sequence[index + 1] : null,
	}
}
