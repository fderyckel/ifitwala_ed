// ifitwala_ed/ui-spa/src/types/contracts/calendar/create_school_event_quick.ts

export type Request = {
	client_request_id: string
	subject: string
	school: string
	starts_on: string
	ends_on: string
	audience_type: string
	event_category?: string | null
	all_day?: number
	location?: string | null
	description?: string | null
	audience_team?: string | null
	audience_student_group?: string | null
	include_guardians?: number
	include_students?: number
	reference_type?: string | null
	reference_name?: string | null
	custom_participants?: string[] | null
}

export type Response = {
	ok: boolean
	status: 'created' | 'already_processed'
	idempotent: boolean
	doctype: 'School Event'
	name: string
	title: string
	start: string | null
	end: string | null
	target_doctype: 'School Event'
	target_name: string
	target_url: string
	target_label: string
}
