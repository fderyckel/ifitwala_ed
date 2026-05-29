import type { ExpenseClaimBoard, ExpenseClaimItemRow, ExpenseClaimRow } from './shared'

export type Request = {
	expense_claim: string
	decision: 'approve' | 'reject' | 'request_info'
	notes?: string | null
	sanctioned_items?: ExpenseClaimItemRow[]
}

export type Response = {
	expense_claim: ExpenseClaimRow
	board: ExpenseClaimBoard
}
