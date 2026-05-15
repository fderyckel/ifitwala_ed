// ui-spa/src/overlays/student/studentLogOverlayRules.ts

export type StudentLogOverlayMode = 'attendance' | 'home'
export type StudentLogOverlayCloseReason = 'backdrop' | 'esc' | 'programmatic'

export type StudentLogDraftState = {
	log_type?: string | null
	log?: string | null
	requires_follow_up?: boolean
	next_step?: string | null
	follow_up_person?: string | null
	visible_to_student?: boolean
	visible_to_guardians?: boolean
}

export function normalizeStudentLogOverlayMode(mode: unknown): StudentLogOverlayMode {
	return mode === 'attendance' ? 'attendance' : 'home'
}

export function hasStudentLogDraftContent(state: StudentLogDraftState): boolean {
	return Boolean(
		(state.log || '').trim() ||
			(state.log_type || '').trim() ||
			Boolean(state.requires_follow_up) ||
			(state.next_step || '').trim() ||
			(state.follow_up_person || '').trim() ||
			Boolean(state.visible_to_student) ||
			Boolean(state.visible_to_guardians)
	)
}

export function shouldPromptStudentLogDiscard(
	reason: StudentLogOverlayCloseReason,
	hasDraftContent: boolean
): boolean {
	return reason !== 'programmatic' && hasDraftContent
}
