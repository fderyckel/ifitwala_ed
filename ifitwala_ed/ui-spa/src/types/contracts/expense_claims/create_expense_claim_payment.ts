import type { ExpenseClaimBoard } from './shared'

export type Request = {
	expense_claim: string
	paid_to: string
	paid_amount?: number | null
	posting_date?: string | null
	remarks?: string | null
}

export type Response = {
	payment_entry: Record<string, unknown>
	board: ExpenseClaimBoard
}
