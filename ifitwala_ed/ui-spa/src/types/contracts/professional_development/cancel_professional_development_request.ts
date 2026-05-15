import type { Response as BoardResponse } from './get_professional_development_board'

export type Request = {
	request_name: string
	notes?: string | null
}

export type Response = {
	request: Record<string, unknown>
	board: BoardResponse
}
