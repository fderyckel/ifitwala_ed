// ifitwala_ed/ui-spa/src/utils/orgCommunication.ts
import type { OrgCommunicationListItem } from '@/types/orgCommunication'

export function canShowPublicInteractions(
	item: OrgCommunicationListItem | null | undefined
): boolean {
	if (!item) return false

	const mode = (item.interaction_mode || 'None').trim()

	// Only these modes allow comments + emoji
	const interactiveModes = [
		'Staff Comments',
		'Structured Feedback',
		'Student Q&A'
	]

	if (!interactiveModes.includes(mode)) {
		return false
	}

	// Frappe booleans can be 0/1, '0'/'1', true/false
	const raw = item.allow_public_thread as unknown
	const publicEnabled =
		raw === 1 ||
		raw === true ||
		raw === '1'

	return publicEnabled
}
