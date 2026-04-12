// ifitwala_ed/ui-spa/src/types/interactions.ts

// Shared types for interaction / reactions (used across all surfaces)

export type InteractionMode =
	| 'None'
	| 'Staff Comments'
	| 'Structured Feedback'
	| 'Student Q&A'

export type AudienceType = 'Staff' | 'Student' | 'Guardian' | 'Community' | null

// Server-owned visibility terms:
// - "Public to audience" means shared with the communication's resolved recipient audience,
//   not public internet visibility.
// - "Private to school" is school-side visibility rather than audience-shared visibility.
export type InteractionVisibility =
	| 'Public to audience'
	| 'Private to school'
	| 'Hidden'
	| null

export type InteractionIntentType =
	| 'Acknowledged'
	| 'Comment'
	| 'Appreciated'
	| 'Support'
	| 'Positive'
	| 'Celebration'
	| 'Question'
	| 'Concern'
	| 'Other'

export const REACTION_CODES = [
	'like',
	'thank',
	'heart',
	'smile',
	'applause',
	'question',
	'concern',
] as const

export type ReactionCode = (typeof REACTION_CODES)[number]

export type ReactionCounts = Record<string, number>

export type InteractionCounts = Partial<Record<InteractionIntentType, number>>
