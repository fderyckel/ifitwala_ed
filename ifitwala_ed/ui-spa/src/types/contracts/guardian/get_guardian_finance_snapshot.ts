// ui-spa/src/types/contracts/guardian/get_guardian_finance_snapshot.ts

export type Request = Record<string, never>

export type Response = {
	meta: {
		generated_at: string
		guardian: { name: string | null }
		finance_access: boolean
		access_reason: string
	}
	family: {
		children: FinanceChildRef[]
	}
	account_holders: AccountHolderSummary[]
	invoices: GuardianInvoice[]
	payments: GuardianPayment[]
	counts: {
		total_invoices: number
		open_invoices: number
		overdue_invoices: number
		payment_history_count: number
		total_outstanding: number
		total_paid: number
	}
}

export type FinanceChildRef = {
	student: string
	full_name: string
	school: string
	account_holder: string
}

export type AccountHolderStudent = {
	student: string
	full_name: string
	school: string
}

export type AccountHolderSummary = {
	account_holder: string
	label: string
	organization: string
	status: string
	primary_email: string
	primary_phone: string
	students: AccountHolderStudent[]
}

export type InvoiceStudentRef = {
	student: string
	full_name: string
}

export type GuardianInvoice = {
	sales_invoice: string
	account_holder: string
	organization: string
	school: string
	program: string
	posting_date: string
	due_date: string
	grand_total: number
	paid_amount: number
	outstanding_amount: number
	status: string
	remarks: string
	students: InvoiceStudentRef[]
}

export type PaymentReference = {
	sales_invoice: string
	allocated_amount: number
}

export type GuardianPayment = {
	payment_entry: string
	account_holder: string
	organization: string
	school: string
	program: string
	posting_date: string
	paid_amount: number
	unallocated_amount: number
	remarks: string
	references: PaymentReference[]
}
