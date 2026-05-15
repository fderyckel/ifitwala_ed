import type { OrgCommunicationQuickReferenceStudentGroup } from './get_org_communication_quick_create_options'

export type Request = {
	query: string
	organization?: string | null
	school?: string | null
	limit?: number | null
}

export type Response = {
	results: OrgCommunicationQuickReferenceStudentGroup[]
}
