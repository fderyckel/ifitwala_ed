// ifitwala_ed/ui-spa/src/types/focusItem.ts

export type FocusKind = 'action' | 'review'

export type FocusPermissions = {
	can_open?: boolean
	// v1: read-only list. no dismiss/snooze/complete here.
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

	payload?: Record<string, any> | null
	permissions?: FocusPermissions | null
}
