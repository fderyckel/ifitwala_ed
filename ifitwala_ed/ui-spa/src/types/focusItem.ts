// ifitwala_ed/ui-spa/src/types/focusItem.ts

export type FocusKind = 'action' | 'review'

export type FocusPermissions = {
	can_open?: boolean
	// v1: read-only list. no dismiss/snooze/complete here.
}

/**
 * Focus payload contract.
 * Keep this small: only the fields the UI actively uses.
 * Allow extension without breaking by adding an index signature.
 */
export type StudentLogFocusPayload = {
	student_name?: string | null
	next_step?: string | null

	// Assignee items (from ToDo)
	assigned_by?: string | null
	assigned_by_name?: string | null
	subject_name?: string | null
	school?: string | null
	organization?: string | null
	applicant_name?: string | null
	student_applicant?: string | null
	target_type?: string | null
	target_name?: string | null

	// Allow future enrichment without TS fights
	[k: string]: any
}

export type FocusItem = {
	id: string
	kind: FocusKind
	title: string
	subtitle: string
	badge?: string | null
	priority?: number | null
	due_date?: string | null

	action_type: string
	reference_doctype: string
	reference_name: string

	payload?: StudentLogFocusPayload | null
	permissions?: FocusPermissions | null
}
