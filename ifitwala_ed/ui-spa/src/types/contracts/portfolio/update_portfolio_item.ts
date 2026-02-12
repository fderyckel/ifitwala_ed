// ifitwala_ed/ui-spa/src/types/contracts/portfolio/update_portfolio_item.ts

export type Request = {
	item_name: string
	caption?: string
	reflection_summary?: string
	display_order?: number
	show_tags?: 0 | 1
	program_enrollment?: string
	evidence_date?: string
	moderation_comment?: string
	is_showcase?: 0 | 1
}

export type Response = {
	portfolio: string
	item_name: string
	moderation_state: string
	is_showcase: boolean
}
