import type { GovernedAttachmentRow } from '@/types/contracts/attachments/shared'

export type ExpenseClaimItemRow = {
	row_name?: string | null
	expense_date: string
	expense_category: string
	description: string
	claimed_amount: number
	sanctioned_amount?: number
	expense_account?: string | null
}

export type ExpenseClaimReceiptRow = {
	row_name: string
	kind: 'file' | 'link'
	title: string
	description?: string | null
	file_name?: string | null
	file_size?: number | string | null
	external_url?: string | null
	attachment?: GovernedAttachmentRow | null
}

export type ExpenseClaimRow = {
	name: string
	employee: string
	employee_name?: string | null
	organization: string
	school?: string | null
	department?: string | null
	claim_title: string
	claim_date: string
	currency?: string | null
	expense_approver?: string | null
	purpose?: string | null
	claimed_total: number
	sanctioned_total: number
	status: string
	submitted_by?: string | null
	submitted_on?: string | null
	decision_by?: string | null
	decision_on?: string | null
	decision_notes?: string | null
	payable_account?: string | null
	payable_posted_by?: string | null
	payable_posted_on?: string | null
	paid_amount: number
	outstanding_amount: number
	payment_entry?: string | null
	paid_on?: string | null
	remarks?: string | null
	modified?: string | null
	items: ExpenseClaimItemRow[]
	receipts: ExpenseClaimReceiptRow[]
}

export type ExpenseClaimAccountOption = {
	value: string
	label: string
	account_number?: string | null
	organization?: string | null
	root_type?: string | null
	account_type?: string | null
}

export type ExpenseClaimBoard = {
	viewer: {
		user: string
		employee: string
		employee_name?: string | null
		organization?: string | null
		school?: string | null
		department?: string | null
		expense_approver?: string | null
		can_decide: boolean
		can_finance: boolean
	}
	defaults: {
		claim_date: string
	}
	options: {
		categories: string[]
		expense_accounts: ExpenseClaimAccountOption[]
		payable_accounts: ExpenseClaimAccountOption[]
		bank_accounts: ExpenseClaimAccountOption[]
	}
	my_claims: ExpenseClaimRow[]
	approval_queue: ExpenseClaimRow[]
	finance_queue: ExpenseClaimRow[]
	stats: {
		draft: number
		submitted: number
		approved: number
		outstanding: number
	}
}
