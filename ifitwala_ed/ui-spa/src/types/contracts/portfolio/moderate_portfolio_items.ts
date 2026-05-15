// ifitwala_ed/ui-spa/src/types/contracts/portfolio/moderate_portfolio_items.ts

export type ModerationAction = 'approve' | 'return_for_edit' | 'hide'

export type Request = {
	action: ModerationAction
	item_names: string[]
	moderation_comment?: string
}

export type ModerationResult = {
	item_name: string
	ok: boolean
	moderation_state?: string
	error?: string
}

export type Response = {
	action: string
	moderation_state: string
	updated: number
	results: ModerationResult[]
}
