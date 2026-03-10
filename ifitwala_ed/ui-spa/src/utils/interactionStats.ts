// ifitwala_ed/ui-spa/src/utils/interactionStats.ts
// Shared helper for canonical interaction aggregates.

import { REACTION_CODES } from '@/types/interactions'

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
	const reaction_counts = withDefaultReactionCounts(summary?.reaction_counts)
	const reactions_total = Number(summary?.reactions_total || 0)
	const comments_total = Number(summary?.comments_total || 0)

	return {
		reactions_total,
		comments_total,
		reaction_counts
	}
}
