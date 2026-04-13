export type Request = {
	framework_name?: string | null
	program?: string | null
	strand?: string | null
	substrand?: string | null
	search_text?: string | null
}

export type StaffLearningStandardPickerRow = {
	learning_standard: string
	framework_name?: string | null
	framework_version?: string | null
	subject_area?: string | null
	program?: string | null
	strand?: string | null
	substrand?: string | null
	standard_code?: string | null
	standard_description?: string | null
	alignment_type?: string | null
}

export type Response = {
	filters: {
		framework_name?: string | null
		program?: string | null
		strand?: string | null
		substrand?: string | null
		search_text?: string | null
	}
	options: {
		frameworks: string[]
		programs: string[]
		strands: string[]
		substrands: string[]
		has_blank_substrand?: boolean
	}
	standards: StaffLearningStandardPickerRow[]
}
