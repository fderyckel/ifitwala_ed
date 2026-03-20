export type Request = {
	budget_name?: string | null
}

export type Response = {
	viewer: {
		user: string
		employee: string
		employee_name?: string | null
		organization: string
		school: string
		academic_year?: string | null
		department?: string | null
	}
	defaults: {
		professional_development_budget?: string | null
		professional_development_theme?: string | null
	}
	options: {
		themes: Array<{ value: string; label: string; school?: string | null }>
		budgets: Array<{
			value: string
			label: string
			budget_mode: string
			professional_development_theme?: string | null
			available_amount: number
		}>
		pgp_plans: Array<{
			value: string
			label: string
			goals: Array<{ value: string; label: string }>
		}>
		types: string[]
	}
	settings: {
		budget_mode?: string | null
	}
}
