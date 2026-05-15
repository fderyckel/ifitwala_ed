// ifitwala_ed/ui-spa/src/types/contracts/portfolio/apply_evidence_tag.ts

export type Request = {
	target_doctype: 'Task Submission' | 'Student Reflection Entry' | 'Student Portfolio Item' | string
	target_name: string
	tag_taxonomy: string
	scope?: 'private' | 'course' | 'portfolio' | string
}

export type Response = {
	name: string
	target_doctype: string
	target_name: string
	tag_taxonomy: string
}
