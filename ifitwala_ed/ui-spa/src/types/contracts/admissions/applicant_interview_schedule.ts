// ifitwala_ed/ui-spa/src/types/contracts/admissions/applicant_interview_schedule.ts

export interface InterviewScheduleRoomOption {
	value: string
	label: string
	school?: string | null
	parent_location?: string | null
	location_type?: string | null
	location_type_name?: string | null
	max_capacity?: number | null
}

export interface InterviewScheduleOptionsResponse {
	ok: boolean
	applicant: {
		name: string
		display_name?: string | null
		school?: string | null
	}
	defaults: {
		date: string
		start_time: string
		duration_minutes: number
		window_start_time: string
		window_end_time: string
		current_user?: string | null
	}
	rooms: InterviewScheduleRoomOption[]
	interview_types: string[]
	modes: string[]
	confidentiality_levels: string[]
}

export interface InterviewScheduleConflict {
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

export interface InterviewScheduleSuggestion {
	start: string
	end: string
	label: string
}

export interface ScheduleApplicantInterviewRequest {
	student_applicant: string
	interview_start: string
	duration_minutes?: number | string | null
	interview_end?: string | null
	interview_type?: string | null
	mode?: string | null
	location?: string | null
	confidentiality_level?: string | null
	notes?: string | null
	primary_interviewer?: string | null
	interviewer_users?: string[] | string | null
	suggestion_window_start_time?: string | null
	suggestion_window_end_time?: string | null
	suggestion_limit?: number | string | null
}

export interface ScheduleApplicantInterviewResponse {
	ok: boolean
	code?: 'EMPLOYEE_CONFLICT' | 'ROOM_CONFLICT' | 'SCHEDULING_CONFLICT' | string
	message?: string | null
	interview?: string | null
	school_event?: string | null
	conflicts?: InterviewScheduleConflict[]
	employee_conflicts?: InterviewScheduleConflict[]
	room_conflicts?: InterviewScheduleConflict[]
	suggestions?: InterviewScheduleSuggestion[]
	window?: {
		start?: string | null
		end?: string | null
		location?: string | null
	}
}

export interface SuggestInterviewSlotsRequest {
	student_applicant?: string | null
	interview_date?: string | null
	primary_interviewer?: string | null
	interviewer_users?: string[] | string | null
	mode?: string | null
	location?: string | null
	duration_minutes?: number | string | null
	window_start_time?: string | null
	window_end_time?: string | null
	limit?: number | string | null
}

export interface SuggestInterviewSlotsResponse {
	ok: boolean
	slots: InterviewScheduleSuggestion[]
	window?: {
		start?: string | null
		end?: string | null
		duration_minutes?: number | null
		step_minutes?: number | null
		location?: string | null
	}
}
