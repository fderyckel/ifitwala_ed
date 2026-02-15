// ifitwala_ed/ui-spa/src/types/contracts/portfolio/export_portfolio_pdf.ts

import type { Request as GetPortfolioFeedRequest } from './get_portfolio_feed'

export type Request = GetPortfolioFeedRequest

export type Response = {
	file_url: string
	file_name: string
	student: string
}
