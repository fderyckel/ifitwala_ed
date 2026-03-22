import type { Response as BoardResponse } from './get_professional_development_board'

export type Request = {
	request_name?: string | null
	professional_development_budget: string
	professional_development_theme?: string | null
	pgp_plan?: string | null
	pgp_goal?: string | null
	title: string
	professional_development_type: string
	provider_name?: string | null
	location?: string | null
	start_datetime: string
	end_datetime: string
	absence_days?: number | null
	requires_substitute?: 0 | 1
	sharing_commitment?: 0 | 1
	learning_outcomes?: string | null
	costs: Array<{
		cost_type: string
		amount: number
		notes?: string | null
	}>
	override_reason?: string | null
	override_approved?: 0 | 1
}

export type Response = {
	request: Record<string, unknown>
	board: BoardResponse
}
