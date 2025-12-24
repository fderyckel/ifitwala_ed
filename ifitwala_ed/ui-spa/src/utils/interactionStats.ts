// Shared helper for interaction aggregates (legacy + future summary shapes).

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

const INTENT_TO_REACTION: Record<string, string> = {
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

	const reaction_counts = summary?.reaction_counts ?? fallbackReactionCounts
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
