export const MISSING_CLASS_COURSE_MESSAGE =
	'This class is not linked to a course yet. Link the class to a course first, then return here to plan this session.'

export function hasLinkedCourse(course?: string | null): boolean {
	return Boolean(String(course || '').trim())
}

export function getPlanSessionBlockedReason(course?: string | null): string {
	return hasLinkedCourse(course) ? '' : MISSING_CLASS_COURSE_MESSAGE
}

export function normalizePlanningSurfaceError(error: unknown): string {
	const rawMessage = error instanceof Error ? error.message : String(error || '')

	if (rawMessage.includes('This class is not linked to a course.')) {
		return MISSING_CLASS_COURSE_MESSAGE
	}

	return rawMessage || 'Could not load the class planning surface.'
}
