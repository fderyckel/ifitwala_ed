// ui-spa/src/types/contracts/activity_booking/get_activity_portal_board.ts

export type Request = {
	students?: string[] | null
	include_inactive?: 0 | 1 | null
}

export type ActivityBookingRow = {
	name: string
	program_offering: string
	status: string
	status_label: string
	allocated_student_group?: string | null
	waitlist_position?: number | null
	offer_expires_on?: string | null
	payment_required: 0 | 1
	amount: number
	sales_invoice?: string | null
	sales_invoice_url?: string | null
	org_communication?: string | null
	choices: string[]
}

export type ActivityStudentBoard = {
	student: string
	full_name: string
	preferred_name?: string | null
	cohort?: string | null
	student_image?: string | null
	account_holder?: string | null
	anchor_school?: string | null
	bookings: ActivityBookingRow[]
	booking_counts: Record<string, number>
}

export type ActivitySection = {
	student_group: string
	label: string
	capacity?: number | null
	reserved: number
	remaining?: number | null
	allow_waitlist: 0 | 1
	next_slot?: {
		start: string
		end: string
		location?: string | null
		map_url?: string | null
	} | null
}

export type ActivityOffering = {
	program_offering: string
	program: string
	program_label: string
	program_abbreviation?: string | null
	school: string
	school_label: string
	school_abbr?: string | null
	title: string
	start_date?: string | null
	end_date?: string | null
	booking_status: string
	booking_window: {
		open_from?: string | null
		open_to?: string | null
		is_open_now: 0 | 1
	}
	allocation_mode: string
	allocation_explanation: string
	booking_roles: {
		allow_student: 0 | 1
		allow_guardian: 0 | 1
		allow_staff: 0 | 1
	}
	age_limits: {
		min_years?: number | null
		max_years?: number | null
	}
	waitlist: {
		enabled: 0 | 1
		offer_hours: number
	}
	payment: {
		required: 0 | 1
		amount: number
		billable_offering?: string | null
		portal_state_mode: string
	}
	activity_context: {
		activity?: string | null
		descriptions?: string | null
		logistics_location_label?: string | null
		logistics_pickup_instructions?: string | null
		logistics_dropoff_instructions?: string | null
		logistics_map_url?: string | null
		logistics_notes?: string | null
		media_cover_image?: string | null
		media_gallery_link?: string | null
		media_notes?: string | null
	}
	sections: ActivitySection[]
}

export type Response = {
	generated_at: string
	viewer: {
		actor_type: 'Guardian' | 'Student' | 'Staff'
		user: string
	}
	settings: {
		default_max_choices: number
		default_show_waitlist_position: 0 | 1
		default_guardian_student_cancellation_mode: string
		default_paid_booking_portal_state: string
		default_offer_banner_hours: number
	}
	students: ActivityStudentBoard[]
	offerings: ActivityOffering[]
}
