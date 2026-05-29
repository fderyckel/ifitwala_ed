import type { ExpenseClaimBoard, ExpenseClaimRow } from './shared'

export type Request = {
	expense_claim: string
	payable_account: string
	expense_account?: string | null
	item_accounts?: Array<{ row_name: string; expense_account: string }>
	posting_date?: string | null
	remarks?: string | null
}

export type Response = {
	expense_claim: ExpenseClaimRow
	board: ExpenseClaimBoard
}
