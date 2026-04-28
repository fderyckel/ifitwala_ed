export type Request = {
	filters?: {
		date_mode?: 'preset' | 'custom' | 'academic_year';
		date_preset?: string;
		from_date?: string;
		to_date?: string;
		academic_year?: string;
		type_of_inquiry?: string;
		source?: string;
		assigned_to?: string;
		assignment_lane?: 'Admission' | 'Staff' | '';
		sla_status?: string;
		organization?: string;
		school?: string;
	};
	active_view?: string;
	start?: number;
	limit?: number;
};

export type ZeroLostLeadView = {
	id: string;
	title: string;
	tone: 'danger' | 'warning' | 'info' | 'success' | string;
	count: number;
	next_action: string;
};

export type ZeroLostLeadRow = {
	name: string;
	lead_title: string;
	email?: string | null;
	phone_number?: string | null;
	type_of_inquiry?: string | null;
	source?: string | null;
	organization?: string | null;
	school?: string | null;
	workflow_state: string;
	sla_status?: string | null;
	assigned_to?: string | null;
	assignment_lane?: string | null;
	student_applicant?: string | null;
	student_applicant_status?: string | null;
	submitted_at?: string | null;
	first_contact_due_on?: string | null;
	followup_due_on?: string | null;
	first_contacted_at?: string | null;
	applicant_submitted_at?: string | null;
	archive_reason?: string | null;
	next_action_note?: string | null;
	age_hours?: number | null;
	open_url?: string | null;
	student_applicant_url?: string | null;
	next_action: {
		label: string;
		target_url?: string | null;
	};
};

export type Response = {
	command_center: {
		views: ZeroLostLeadView[];
		active_view: string;
		rows: ZeroLostLeadRow[];
		pagination: {
			start: number;
			limit: number;
			total: number;
			has_next: boolean;
		};
		generated_at?: string | null;
		scope?: {
			operational_date_mode?: string;
		};
	};
	analytics: Record<string, unknown>;
};
