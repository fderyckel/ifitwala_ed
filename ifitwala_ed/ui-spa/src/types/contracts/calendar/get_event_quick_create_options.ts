// ifitwala_ed/ui-spa/src/types/contracts/calendar/get_event_quick_create_options.ts

export type SelectOption = {
	value: string;
	label: string;
};

export type LocationOption = SelectOption & {
	parent_location?: string | null;
	location_type?: string | null;
	location_type_name?: string | null;
	max_capacity?: number | null;
};

export type AttendeeKindOption = {
	value: 'employee' | 'student' | 'guardian';
	label: string;
};

export type Request = Record<string, never>;

export type Response = {
	can_create_meeting: boolean;
	can_create_school_event: boolean;
	meeting_categories: string[];
	school_event_categories: string[];
	audience_types: string[];
	announcement_publish: {
		enabled: boolean;
		blocked_reason: string | null;
	};
	schools: SelectOption[];
	teams: SelectOption[];
	student_groups: SelectOption[];
	locations: LocationOption[];
	locations_by_school: Record<string, LocationOption[]>;
	location_types: SelectOption[];
	location_types_by_school: Record<string, SelectOption[]>;
	attendee_kinds: AttendeeKindOption[];
	defaults: {
		school: string | null;
		day_start_time: string;
		day_end_time: string;
		duration_minutes: number;
	};
};
