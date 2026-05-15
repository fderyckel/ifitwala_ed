// ifitwala_ed/ui-spa/src/types/contracts/portfolio/add_portfolio_item.ts

export type Request = {
	portfolio?: string
	student?: string
	academic_year?: string
	school?: string
	item_type: 'Task Submission' | 'Student Reflection Entry' | 'External Artefact' | string
	task_submission?: string
	student_reflection_entry?: string
	artefact_file?: string
	evidence_date?: string
	program_enrollment?: string
	caption?: string
	reflection_summary?: string
	display_order?: number
	is_showcase?: 0 | 1
	show_tags?: 0 | 1
	moderation_state?: string
}

export type Response = {
	portfolio: string
	item_name: string
	moderation_state: string
}
