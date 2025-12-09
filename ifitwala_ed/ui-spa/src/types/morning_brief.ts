// Types for Morning Brief endpoints (derived from api-samples/morning_brief/schema.md)

// Domain unions and constants
export const ORG_PRIORITIES = {
	CRITICAL: 'Critical',
	HIGH: 'High',
	NORMAL: 'Normal',
	LOW: 'Low'
} as const
export type OrgPriority = (typeof ORG_PRIORITIES)[keyof typeof ORG_PRIORITIES] | null

export const ORG_SURFACES = {
	DESK: 'Desk',
	MORNING_BRIEF: 'Morning Brief',
	PORTAL_FEED: 'Portal Feed',
	STUDENT_PORTAL: 'Student Portal',
	GUARDIAN_PORTAL: 'Guardian Portal',
	EVERYWHERE: 'Everywhere',
	OTHER: 'Other'
} as const
export type OrgSurface = (typeof ORG_SURFACES)[keyof typeof ORG_SURFACES]

export type InteractionMode =
	| 'None'
	| 'Staff Comments'
	| 'Structured Feedback'
	| 'Student Q&A'
	| string

export type InteractionIntentType =
	| 'Acknowledged'
	| 'Comment'
	| 'Appreciated'
	| 'Support'
	| 'Positive'
	| 'Celebration'
	| 'Question'
	| 'Concern'
	| 'Other'
	| string
export type ReactionCode =
	| 'like'
	| 'thank'
	| 'heart'
	| 'smile'
	| 'applause'
	| 'question'
	| 'other'

// Widgets: announcement + analytics payloads
export interface Announcement {
	name: string
	title: string
	content: string
	type:
		| 'Logistics'
		| 'Reminder'
		| 'Information'
		| 'Policy Procedure'
		| 'Celebration'
		| 'Call to Action'
		| 'Event Announcement'
		| 'Class Announcement'
		| 'Urgent'
		| 'Alert'
	priority: OrgPriority
	interaction_mode: InteractionMode
	allow_public_thread: 0 | 1
	allow_private_notes: 0 | 1
}

export interface StaffBirthday {
	name: string
	image: string | null
	date_of_birth: string
}

export interface ClinicVolumePoint {
	date: string
	count: number
}

export interface AdmissionsPulseBreakdown {
	application_status: 'Applied' | 'Approved' | 'Rejected' | 'Admitted'
	count: number
}

export interface AdmissionsPulse {
	total_new_weekly: number
	breakdown: AdmissionsPulseBreakdown[]
}

export interface MedicalContext {
	first_name: string
	last_name: string
	medical_info: string
	allergies: string | null
	food_allergies: string | null
}

export interface StudentBirthday {
	first_name: string
	last_name: string
	image: string | null
	date_of_birth: string
}

export interface StudentLogItem {
	name: string
	student_name: string
	student_photo: string | null
	log_type: string
	date_display: string
	snippet: string
	full_content: string
	status_color: string
}

export interface StudentLogDetail {
	name: string
	student_name: string
	student_photo: string | null
	log_type: string
	date: string
	log: string
	date_display: string
	snippet: string
}

export interface AttendanceTrendPoint {
	date: string
	count: number
}

export interface AbsentStudent {
	student_name: string
	attendance_code: string
	student_group: string
	remark: string | null
	student_photo: string | null
	status_color: string | null
}

export interface WidgetsPayload {
	announcements: Announcement[]
	staff_birthdays?: StaffBirthday[]
	clinic_volume?: ClinicVolumePoint[]
	admissions_pulse?: AdmissionsPulse
	critical_incidents?: number
	today_label?: string
	medical_context?: MedicalContext[]
	grading_velocity?: number
	my_student_birthdays?: StudentBirthday[]
	student_logs?: StudentLogItem[]
	attendance_trend?: AttendanceTrendPoint[]
	my_absent_students?: AbsentStudent[]
}

// Interaction summary + thread
export interface InteractionSelf {
	name: string
	org_communication: string
	user: string
	audience_type: 'Staff' | 'Student' | 'Guardian' | 'Community' | null
	surface: OrgSurface | null
	school: string | null
	program: string | null
	student_group: string | null
	reaction_code: ReactionCode | null
	intent_type: InteractionIntentType | null
	note: string | null
	visibility: 'Public to audience' | 'Private to school' | 'Hidden' | null
	is_teacher_reply: 0 | 1
	is_pinned: 0 | 1
	is_resolved: 0 | 1
	creation: string
	modified: string
	owner?: string
	modified_by?: string
	docstatus?: number
	doctype?: string
	idx?: number
}

export type InteractionCounts = Record<string, number>

export interface InteractionSummary {
	counts: InteractionCounts
	self: InteractionSelf | null
}

export type InteractionSummaryMap = Record<string, InteractionSummary>

export interface InteractionThreadRow {
	name: string
	user: string
	full_name: string | null
	audience_type: 'Staff' | 'Student' | 'Guardian' | 'Community' | null
	intent_type: InteractionIntentType | null
	reaction_code: ReactionCode | null
	note: string | null
	visibility: 'Public to audience' | 'Private to school' | 'Hidden' | null
	is_teacher_reply: 0 | 1
	is_pinned: 0 | 1
	is_resolved: 0 | 1
	creation: string
	modified: string
}
