// ifitwala_ed/ui-spa/src/types/contracts/portfolio/create_portfolio_share_link.ts

export type Request = {
	portfolio: string
	expires_on: string
	allowed_viewer_email?: string
	allow_download?: 0 | 1
	idempotency_key?: string
}

export type Response = {
	name: string
	share_url: string
	token: string
	expires_on: string
	allow_download: boolean
}
