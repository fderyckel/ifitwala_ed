// ifitwala_ed/ui-spa/src/utils/orgCommunication.ts

export type OrgCommunicationInteractionSource = {
	interaction_mode?: string | null
	allow_public_thread?: 0 | 1 | boolean | string | null
}

export type OrgCommunicationInteractionCapabilities = {
	canReact: boolean
	canComment: boolean
	hasVisibleActions: boolean
}

function isCheckedValue(raw: unknown): boolean {
	if (raw === true || raw === 1) return true
	if (raw === false || raw === 0 || raw == null) return false

	if (typeof raw === 'string') {
		const normalized = raw.trim().toLowerCase()
		if (!normalized) return false
		if (['0', 'false', 'no', 'n', 'off'].includes(normalized)) return false
		if (['1', 'true', 'yes', 'y', 'on'].includes(normalized)) return true
	}

	return Boolean(raw)
}

// Centralize the current shipped SPA affordance rule until the backend exposes
// actor-specific capabilities directly.
//
// Terms:
// - "comment" means recipient-visible shared thread access
// - "react" means a surface may show the reaction affordance
// - "audience" means the resolved recipients of this communication, not public web visibility
export function getAudienceInteractionCapabilities(
	item: OrgCommunicationInteractionSource | null | undefined
): OrgCommunicationInteractionCapabilities {
	if (!item) {
		return {
			canReact: false,
			canComment: false,
			hasVisibleActions: false,
		}
	}

	const mode = String(item.interaction_mode || 'None').trim() || 'None'
	const canReact = mode !== 'None'
	const canComment = canReact && isCheckedValue(item.allow_public_thread)

	return {
		canReact,
		canComment,
		hasVisibleActions: canReact || canComment,
	}
}
