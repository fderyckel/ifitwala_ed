import type { ExpenseClaimReceiptRow } from './shared'

export type Response = {
	ok: boolean
	expense_claim: string
	receipt: ExpenseClaimReceiptRow
}
