// ifitwala_ed/ui-spa/src/types/contracts/portfolio/set_showcase_state.ts

export type Request = {
	item_name: string
	is_showcase: 0 | 1
}

export type Response = {
	item_name: string
	is_showcase: boolean
	moderation_state: string
}
