// ifitwala_ed/ui-spa/src/types/contracts/portfolio/list_reflection_entries.ts

export type Request = {
	student_ids?: string[]
	school?: string
	academic_year?: string
	program_enrollment?: string
	date_from?: string
	date_to?: string
	page?: number
	page_length?: number
}

export type ReflectionEntryRow = {
	name: string
	student: string
	academic_year?: string
	school?: string
	entry_date?: string
	entry_type?: string
	visibility?: string
	moderation_state?: string
	body?: string
	body_preview?: string
}

export type Response = {
	items: ReflectionEntryRow[]
	total: number
	page: number
	page_length: number
}
