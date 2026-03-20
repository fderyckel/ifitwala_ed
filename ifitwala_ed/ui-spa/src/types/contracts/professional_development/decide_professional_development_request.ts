import type { Response as BoardResponse } from './get_professional_development_board'

export type Request = {
	request_name: string
	decision: 'approve' | 'reject'
	override_reason?: string | null
	override_approved?: 0 | 1
	notes?: string | null
}

export type Response = {
	request: Record<string, unknown>
	board: BoardResponse
}
