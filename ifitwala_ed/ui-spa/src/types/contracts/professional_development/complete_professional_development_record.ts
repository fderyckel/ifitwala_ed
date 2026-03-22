import type { Response as BoardResponse } from './get_professional_development_board'

export type Request = {
	record_name: string
	actual_total: number
	completion_date: string
	reflection?: string | null
	evidence?: Array<{
		evidence_label: string
		attachment?: string | null
		notes?: string | null
	}>
	liquidation_ready?: 0 | 1
}

export type Response = {
	outcome: Record<string, unknown>
	board: BoardResponse
}
