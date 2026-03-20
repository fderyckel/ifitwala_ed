export type Request = Record<string, never>

export type ProfessionalDevelopmentBudgetOption = {
	value: string
	label: string
	budget_mode: string
	professional_development_theme?: string | null
	available_amount: number
}

export type ProfessionalDevelopmentRequestRow = {
	name: string
	title: string
	professional_development_type: string
	status: string
	professional_development_theme?: string | null
	professional_development_budget?: string | null
	start_datetime: string
	end_datetime: string
	estimated_total: number
	validation_status: string
	requires_override: 0 | 1
}

export type ProfessionalDevelopmentRecordRow = {
	name: string
	professional_development_request?: string | null
	title: string
	professional_development_type: string
	status: string
	start_datetime: string
	end_datetime: string
	estimated_total: number
	actual_total: number
	professional_development_outcome?: string | null
}

export type ProfessionalDevelopmentBoard = {
	generated_at: string
	viewer: {
		user: string
		employee: string
		employee_name?: string | null
		organization: string
		school: string
		academic_year?: string | null
	}
	settings: {
		budget_mode?: string | null
		require_completion_evidence: 0 | 1
		require_liquidation_reflection: 0 | 1
	}
	summary: {
		open_requests: number
		upcoming_records: number
		completion_backlog: number
		available_budget_total: number
	}
	request_options: {
		themes: Array<{ value: string; label: string; school?: string | null }>
		budgets: ProfessionalDevelopmentBudgetOption[]
		pgp_plans: Array<{
			value: string
			label: string
			goals: Array<{ value: string; label: string }>
		}>
		types: string[]
	}
	requests: ProfessionalDevelopmentRequestRow[]
	records: ProfessionalDevelopmentRecordRow[]
	completion_backlog: ProfessionalDevelopmentRecordRow[]
	budget_rows: ProfessionalDevelopmentBudgetOption[]
	expiring_items: Array<Record<string, unknown>>
}

export type Response = ProfessionalDevelopmentBoard
