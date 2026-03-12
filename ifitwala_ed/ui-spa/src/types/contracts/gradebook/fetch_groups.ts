// ui-spa/src/types/contracts/gradebook/fetch_groups.ts

export type Request = {
	search?: string | null
	limit?: number | null
	school?: string | null
	academic_year?: string | null
	program?: string | null
	course?: string | null
}

export type GroupSummary = {
	name: string
	label: string
	school?: string | null
	program?: string | null
	course?: string | null
	cohort?: string | null
	academic_year?: string | null
}

export type Response = GroupSummary[]
