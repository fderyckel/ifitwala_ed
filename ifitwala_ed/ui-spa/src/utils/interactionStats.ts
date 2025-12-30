// ifitwala_ed/ui-spa/src/utils/interactionStats.ts
// Shared helper for interaction aggregates (legacy + future summary shapes).

import { REACTION_CODES, type ReactionCode } from '@/types/morning_brief'

export type InteractionSummaryLike = {
	counts?: Record<string, number>
	reaction_counts?: Record<string, number>
	reactions_total?: number
	comments_total?: number
}

export type InteractionStats = {
	reactions_total: number
	comments_total: number
	reaction_counts: Record<string, number>
}

const INTENT_TO_REACTION: Record<string, ReactionCode> = {
	Acknowledged: 'like',
	Appreciated: 'thank',
	Support: 'heart',
	Positive: 'smile',
	Celebration: 'applause',
	Question: 'question',
	Concern: 'concern',
	Other: 'other'
}

function sumCounts(counts: Record<string, number>): number {
	return Object.values(counts).reduce((total, value) => total + (Number(value) || 0), 0)
}

function withDefaultReactionCounts(
	counts?: Record<string, number> | null
): Record<string, number> {
	const normalized: Record<string, number> = {}

	for (const code of REACTION_CODES) {
		normalized[code] = 0
	}

	if (counts) {
		for (const [key, value] of Object.entries(counts)) {
			normalized[key] = Number(value) || 0
		}
	}

	return normalized
}

export function getInteractionStats(summary?: InteractionSummaryLike | null): InteractionStats {
	const counts = summary?.counts ?? {}
	const fallbackComments = (counts.Comment || 0) + (counts.Question || 0)

	const fallbackReactionCounts: Record<string, number> = {}
	for (const [intent, value] of Object.entries(counts)) {
		const reactionCode = INTENT_TO_REACTION[intent]
		if (!reactionCode) continue
		fallbackReactionCounts[reactionCode] =
			(fallbackReactionCounts[reactionCode] || 0) + (Number(value) || 0)
	}

	const reaction_counts = withDefaultReactionCounts(
		summary?.reaction_counts ?? fallbackReactionCounts
	)
	const reactions_total =
		typeof summary?.reactions_total === 'number'
			? summary.reactions_total
			: sumCounts(reaction_counts)
	const comments_total =
		typeof summary?.comments_total === 'number'
			? summary.comments_total
			: fallbackComments

	return {
		reactions_total,
		comments_total,
		reaction_counts
	}
}
