// ui-spa/src/types/contracts/org_communication_quick_create/create_org_communication_quick.ts

export type OrgCommunicationQuickAudienceRow = {
	target_mode: string
	school?: string | null
	team?: string | null
	student_group?: string | null
	include_descendants?: 0 | 1
	to_staff?: 0 | 1
	to_students?: 0 | 1
	to_guardians?: 0 | 1
	to_community?: 0 | 1
	note?: string | null
}

export type Request = {
	name?: string | null
	title: string
	communication_type: string
	status: string
	priority: string
	portal_surface: string
	publish_from?: string | null
	publish_to?: string | null
	brief_start_date?: string | null
	brief_end_date?: string | null
	brief_order?: number | null
	organization?: string | null
	school?: string | null
	message?: string | null
	internal_note?: string | null
	interaction_mode?: string | null
	allow_private_notes?: 0 | 1
	allow_public_thread?: 0 | 1
	audiences: OrgCommunicationQuickAudienceRow[]
	client_request_id: string
}

export type Response = {
	ok: boolean
	status: 'created' | 'updated' | 'already_processed'
	name: string
	title: string
}
