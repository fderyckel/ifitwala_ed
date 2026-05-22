// ifitwala_ed/ui-spa/src/types/contracts/admissions/admission_visit_schedule.ts

export interface AdmissionVisitLocationOption {
	value: string
	label: string
	school?: string | null
	parent_location?: string | null
	location_type?: string | null
	location_type_name?: string | null
	is_group?: number | boolean | null
	max_capacity?: number | null
}

export interface AdmissionVisitScheduleContext {
	conversation?: string | null
	inquiry?: string | null
	student_applicant?: string | null
	organization?: string | null
	school?: string | null
	visitor_name?: string | null
	visitor_email?: string | null
	visitor_phone?: string | null
	requested_grade_level?: string | null
	program_interest?: string | null
}

export interface AdmissionVisitScheduleOptionsResponse {
	ok: boolean
	context: AdmissionVisitScheduleContext
	defaults: {
		date: string
		start_time: string
		duration_minutes: number
		window_start_time: string
		window_end_time: string
		lead_user?: string | null
		visit_type?: string | null
		visit_mode?: string | null
	}
	rooms: AdmissionVisitLocationOption[]
	buildings: AdmissionVisitLocationOption[]
	visit_types: string[]
	visit_modes: string[]
}

export interface AdmissionVisitScheduleConflict {
	kind?: 'employee' | 'room' | string
	employee?: string | null
	employee_name?: string | null
	location?: string | null
	location_label?: string | null
	booking_type?: string | null
	occupancy_type?: string | null
	source_doctype?: string | null
	source_name?: string | null
	start?: string | null
	end?: string | null
	start_label?: string | null
	end_label?: string | null
}

export interface AdmissionVisitScheduleSuggestion {
	start: string
	end: string
	label: string
}

export interface AdmissionVisitRecord {
	name: string
	visit_title?: string | null
	organization?: string | null
	school?: string | null
	status?: string | null
	conversation?: string | null
	inquiry?: string | null
	student_applicant?: string | null
	visit_type?: string | null
	visit_mode?: string | null
	starts_on?: string | null
	ends_on?: string | null
	building?: string | null
	location?: string | null
	party_size?: number | null
	visitor_name?: string | null
	visitor_email?: string | null
	visitor_phone?: string | null
	relationship_to_student?: string | null
	requested_grade_level?: string | null
	program_interest?: string | null
	lead_user?: string | null
	staff_users?: string[]
	informed_users?: string[]
	internal_notes?: string | null
	school_event?: string | null
	cancelled_at?: string | null
	cancelled_by?: string | null
	cancellation_reason?: string | null
}

export interface AdmissionVisitDetailResponse {
	ok: boolean
	can_write: boolean
	visit: AdmissionVisitRecord
	options: AdmissionVisitScheduleOptionsResponse
}

export interface AdmissionVisitScheduleBaseRequest {
	conversation?: string | null
	inquiry?: string | null
	student_applicant?: string | null
	organization?: string | null
	school?: string | null
	starts_on: string
	ends_on?: string | null
	duration_minutes?: number | string | null
	visit_type?: string | null
	visit_mode?: string | null
	building?: string | null
	location?: string | null
	lead_user?: string | null
	staff_users?: string[] | string | null
	informed_users?: string[] | string | null
	visitor_name?: string | null
	visitor_email?: string | null
	visitor_phone?: string | null
	relationship_to_student?: string | null
	requested_grade_level?: string | null
	program_interest?: string | null
	party_size?: number | string | null
	internal_notes?: string | null
	suggestion_window_start_time?: string | null
	suggestion_window_end_time?: string | null
	suggestion_limit?: number | string | null
}

export interface ScheduleAdmissionVisitRequest extends AdmissionVisitScheduleBaseRequest {}

export interface RescheduleAdmissionVisitRequest extends AdmissionVisitScheduleBaseRequest {
	admission_visit: string
}

export interface AdmissionVisitScheduleResponse {
	ok: boolean
	code?: 'EMPLOYEE_CONFLICT' | 'ROOM_CONFLICT' | 'SCHEDULING_CONFLICT' | string
	message?: string | null
	admission_visit?: string | null
	school_event?: string | null
	conversation?: string | null
	conflicts?: AdmissionVisitScheduleConflict[]
	employee_conflicts?: AdmissionVisitScheduleConflict[]
	room_conflicts?: AdmissionVisitScheduleConflict[]
	suggestions?: AdmissionVisitScheduleSuggestion[]
	window?: {
		start?: string | null
		end?: string | null
		location?: string | null
		building?: string | null
	}
}

export interface SuggestAdmissionVisitSlotsRequest {
	conversation?: string | null
	inquiry?: string | null
	student_applicant?: string | null
	organization?: string | null
	school?: string | null
	visit_date?: string | null
	lead_user?: string | null
	staff_users?: string[] | string | null
	visit_mode?: string | null
	building?: string | null
	location?: string | null
	duration_minutes?: number | string | null
	window_start_time?: string | null
	window_end_time?: string | null
	limit?: number | string | null
}

export interface SuggestAdmissionVisitSlotsResponse {
	ok: boolean
	slots: AdmissionVisitScheduleSuggestion[]
	window?: {
		start?: string | null
		end?: string | null
		duration_minutes?: number | null
		step_minutes?: number | null
		location?: string | null
	}
}

export interface AdmissionVisitWorkflowResponse {
	ok: boolean
	admission_visit?: string | null
	status?: string | null
	notified_users?: string[]
}
