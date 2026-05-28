export type StudentInsightNote = {
	name: string
	category: string
	summary: string
	source?: string | null
	effective_from?: string | null
	review_on?: string | null
	status?: 'Active' | 'Needs Review' | 'Archived' | string | null
	visibility?: 'Teachers' | 'Learning Support' | 'Counselor' | 'Admissions/Admin' | string | null
}

export type StudentInsightSummary = {
	active_count: number
	needs_review_count: number
	categories: string[]
	latest_summary?: string | null
	notes: StudentInsightNote[]
}
