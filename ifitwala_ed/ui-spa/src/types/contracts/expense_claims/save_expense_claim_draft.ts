import type { ExpenseClaimBoard, ExpenseClaimItemRow, ExpenseClaimRow } from './shared'

export type Request = {
	expense_claim?: string | null
	claim_title: string
	claim_date: string
	purpose?: string | null
	items: ExpenseClaimItemRow[]
}

export type Response = {
	expense_claim: ExpenseClaimRow
	board: ExpenseClaimBoard
}
