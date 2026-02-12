// ifitwala_ed/ui-spa/src/types/contracts/portfolio/get_portfolio_feed.ts

export type Request = {
	date_from?: string
	date_to?: string
	student_ids?: string[]
	program_enrollment?: string
	academic_year?: string
	tag_ids?: string[]
	page?: number
	page_length?: number
	show_showcase_only?: 0 | 1
	school?: string
}

export type PortfolioTag = {
	name?: string
	tag_taxonomy: string
	title: string
	tagged_by_type: 'Student' | 'Employee' | 'System' | string
	tagged_by_id: string
}

export type PortfolioEvidence = {
	kind?: 'task_submission' | 'reflection' | 'external_file' | string
	submitted_on?: string
	entry_date?: string
	entry_type?: string
	visibility?: string
	text_preview?: string
	link_url?: string
	file_name?: string
	file_url?: string
	file_size?: number
}

export type PortfolioFeedItem = {
	item_name: string
	portfolio: string
	student: string
	student_name: string
	academic_year: string
	school: string
	item_type: 'Task Submission' | 'Student Reflection Entry' | 'External Artefact' | string
	task_submission?: string | null
	student_reflection_entry?: string | null
	artefact_file?: string | null
	evidence_date?: string | null
	program_enrollment?: string | null
	caption?: string | null
	reflection_summary?: string | null
	display_order: number
	is_showcase: boolean
	moderation_state: string
	tags: PortfolioTag[]
	evidence: PortfolioEvidence
}

export type Response = {
	items: PortfolioFeedItem[]
	total: number
	page: number
	page_length: number
}
