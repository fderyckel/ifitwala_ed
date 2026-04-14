// ifitwala_ed/ui-spa/src/utils/orgCommunication.ts

export type OrgCommunicationInteractionSource = {
	interaction_mode?: string | null
	allow_public_thread?: 0 | 1 | boolean | string | null
}

export const ORG_COMMUNICATION_VIEWERS = {
	STAFF: 'staff',
	RECIPIENT: 'recipient',
} as const

export type OrgCommunicationInteractionViewer =
	(typeof ORG_COMMUNICATION_VIEWERS)[keyof typeof ORG_COMMUNICATION_VIEWERS]

export const ORG_COMMUNICATION_COMMENT_MODES = {
	NONE: 'none',
	SHARED_THREAD: 'shared_thread',
	PRIVATE_NOTE: 'private_note',
	STAFF_THREAD: 'staff_thread',
} as const

export type OrgCommunicationCommentMode =
	(typeof ORG_COMMUNICATION_COMMENT_MODES)[keyof typeof ORG_COMMUNICATION_COMMENT_MODES]

export type OrgCommunicationInteractionCapabilities = {
	canReact: boolean
	canComment: boolean
	hasVisibleActions: boolean
	commentMode: OrgCommunicationCommentMode
}

export type OrgCommunicationCommentUi = {
	actionLabel: string
	titleLabel: string
	submitLabel: string
	placeholder: string
	emptyMessage: string
	unavailableMessage: string
	loadErrorMessage: string
	postErrorMessage: string
	postSuccessMessage: string
	requiredMessage: string
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
// - "comment" means the currently supported note/thread affordance on that surface
// - "react" means a surface may show the reaction affordance
// - "recipient" means a recipient-facing surface (student / guardian / community)
// - "audience" means the resolved recipients of this communication, not public web visibility
export function getAudienceInteractionCapabilities(
	item: OrgCommunicationInteractionSource | null | undefined,
	options?: {
		viewer?: OrgCommunicationInteractionViewer
	}
): OrgCommunicationInteractionCapabilities {
	if (!item) {
		return {
			canReact: false,
			canComment: false,
			hasVisibleActions: false,
			commentMode: ORG_COMMUNICATION_COMMENT_MODES.NONE,
		}
	}

	const mode = String(item.interaction_mode || 'None').trim() || 'None'
	const viewer = options?.viewer ?? ORG_COMMUNICATION_VIEWERS.RECIPIENT
	const sharedThreadEnabled = isCheckedValue(item.allow_public_thread)

	let canReact = false
	let commentMode: OrgCommunicationCommentMode = ORG_COMMUNICATION_COMMENT_MODES.NONE

	if (viewer === ORG_COMMUNICATION_VIEWERS.STAFF) {
		if (mode === 'Staff Comments') {
			canReact = true
			commentMode = ORG_COMMUNICATION_COMMENT_MODES.STAFF_THREAD
		} else if (mode === 'Structured Feedback') {
			canReact = true
		} else if (mode === 'Student Q&A') {
			commentMode = ORG_COMMUNICATION_COMMENT_MODES.STAFF_THREAD
		}
	} else if (mode === 'Structured Feedback') {
		canReact = true
	} else if (mode === 'Student Q&A') {
		commentMode = sharedThreadEnabled
			? ORG_COMMUNICATION_COMMENT_MODES.SHARED_THREAD
			: ORG_COMMUNICATION_COMMENT_MODES.PRIVATE_NOTE
	}

	const canComment = commentMode !== ORG_COMMUNICATION_COMMENT_MODES.NONE

	return {
		canReact,
		canComment,
		hasVisibleActions: canReact || canComment,
		commentMode,
	}
}

export function getInteractionCommentUi(
	commentMode: OrgCommunicationCommentMode
): OrgCommunicationCommentUi {
	if (commentMode === ORG_COMMUNICATION_COMMENT_MODES.PRIVATE_NOTE) {
		return {
			actionLabel: 'Ask School',
			titleLabel: 'Ask School',
			submitLabel: 'Send to School',
			placeholder: 'Write a private question or note to school staff',
			emptyMessage: 'Your private questions to school staff will appear here.',
			unavailableMessage: 'Private questions to school staff are not enabled for this update.',
			loadErrorMessage: 'Could not load messages to school staff.',
			postErrorMessage: 'Could not send your message to school staff.',
			postSuccessMessage: 'Message sent to school staff.',
			requiredMessage: 'Please add a question or note before sending.',
		}
	}

	if (commentMode === ORG_COMMUNICATION_COMMENT_MODES.STAFF_THREAD) {
		return {
			actionLabel: 'Comments',
			titleLabel: 'Comments',
			submitLabel: 'Send',
			placeholder: 'Add a short comment (max 300 characters)',
			emptyMessage: 'No comments yet. Start the conversation!',
			unavailableMessage: 'Comments are not available for this announcement.',
			loadErrorMessage: 'Could not load comment thread.',
			postErrorMessage: 'Could not post comment.',
			postSuccessMessage: 'Comment posted.',
			requiredMessage: 'Please add a comment before posting.',
		}
	}

	return {
		actionLabel: 'Comments',
		titleLabel: 'Comments',
		submitLabel: 'Send',
		placeholder: 'Write a comment...',
		emptyMessage: 'No comments yet. Start the conversation!',
		unavailableMessage: 'Comments are not enabled for this update.',
		loadErrorMessage: 'Could not load comment thread.',
		postErrorMessage: 'Could not post comment.',
		postSuccessMessage: 'Comment posted.',
		requiredMessage: 'Please add a comment before posting.',
	}
}
