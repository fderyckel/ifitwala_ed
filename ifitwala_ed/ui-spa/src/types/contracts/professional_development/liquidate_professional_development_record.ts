import type { Response as BoardResponse } from './get_professional_development_board'

export type Request = {
	record_name: string
	actual_total?: number | null
	liquidation_date?: string | null
}

export type Response = {
	record: Record<string, unknown>
	board: BoardResponse
}
