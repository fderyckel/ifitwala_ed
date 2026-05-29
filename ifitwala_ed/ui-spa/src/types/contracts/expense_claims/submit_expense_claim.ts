import type { ExpenseClaimBoard, ExpenseClaimRow } from './shared'

export type Request = {
	expense_claim: string
}

export type Response = {
	expense_claim: ExpenseClaimRow
	board: ExpenseClaimBoard
}
