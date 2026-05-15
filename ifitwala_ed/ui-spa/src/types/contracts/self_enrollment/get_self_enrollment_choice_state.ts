// ui-spa/src/types/contracts/self_enrollment/get_self_enrollment_choice_state.ts

export type Request = {
	selection_window: string
	student?: string | null
}

export type SelfEnrollmentChoiceCourse = {
	course: string
	course_name: string
	required: boolean
	basket_groups: string[]
	applied_basket_group?: string | null
	choice_rank?: number | null
	is_selected: boolean
	requires_basket_group_selection: boolean
	is_explicit_choice: boolean
	has_choice_rank: boolean
}

export type Response = {
	generated_at: string
	viewer: {
		actor_type: 'Guardian' | 'Student'
		user: string
	}
	window: {
		selection_window: string
		program_offering: string
		title: string
		program: string
		program_label: string
		program_abbreviation?: string | null
		school: string
		school_label: string
		school_abbr?: string | null
		academic_year: string
		status: string
		open_from?: string | null
		due_on?: string | null
		is_open_now: 0 | 1
		instructions?: string | null
	}
	student: {
		student: string
		full_name: string
		preferred_name?: string | null
		cohort?: string | null
		student_image?: string | null
	}
	permissions: {
		can_edit: 0 | 1
		can_submit: 0 | 1
		locked_reason?: string | null
	}
	request: {
		name: string
		status: string
		academic_year: string
		program: string
		program_offering: string
		validation_status: string
		submitted_on?: string | null
		submitted_by?: string | null
		can_edit_choices: boolean
		can_submit_choices: boolean
	}
	summary: {
		has_request: boolean
		has_courses: boolean
		has_selectable_courses: boolean
		can_edit_choices: boolean
		ready_for_submit: boolean
		required_course_count: number
		optional_course_count: number
		selected_optional_count: number
	}
	validation: {
		status?: string | null
		ready_for_submit: boolean
		reasons: string[]
		violations: string[]
		missing_required_courses: string[]
		ambiguous_courses: string[]
		group_summary: Record<string, unknown>
	}
	required_basket_groups: string[]
	courses: SelfEnrollmentChoiceCourse[]
}
