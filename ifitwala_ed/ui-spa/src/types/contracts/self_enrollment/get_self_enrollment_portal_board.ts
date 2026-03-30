// ui-spa/src/types/contracts/self_enrollment/get_self_enrollment_portal_board.ts

export type Request = {
	students?: string[] | null
	include_closed?: 0 | 1 | null
}

export type PortalStudentRef = {
	student: string
	full_name: string
	preferred_name?: string | null
	cohort?: string | null
	student_image?: string | null
	account_holder?: string | null
	anchor_school?: string | null
}

export type PortalSelectionRequestSummary = {
	name?: string | null
	status: string
	validation_status: string
	submitted_on?: string | null
	submitted_by?: string | null
	can_edit: 0 | 1
	locked_reason?: string | null
}

export type PortalSelectionStudent = PortalStudentRef & {
	request?: PortalSelectionRequestSummary | null
}

export type PortalSelectionWindow = {
	selection_window: string
	program_offering: string
	program: string
	program_label: string
	program_abbreviation?: string | null
	school: string
	school_label: string
	school_abbr?: string | null
	title: string
	academic_year: string
	audience: 'Guardian' | 'Student'
	status: string
	open_from?: string | null
	due_on?: string | null
	is_open_now: 0 | 1
	instructions?: string | null
	summary: {
		total_students: number
		submitted_count: number
		pending_count: number
		invalid_count: number
		approved_count: number
	}
	students: PortalSelectionStudent[]
}

export type Response = {
	generated_at: string
	viewer: {
		actor_type: 'Guardian' | 'Student'
		user: string
	}
	students: PortalStudentRef[]
	windows: PortalSelectionWindow[]
}
