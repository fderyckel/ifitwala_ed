export interface SchoolEventDetails {
	name: string;
	subject: string;
	school?: string | null;
	location?: string | null;
	event_category?: string | null;
	event_type?: string | null;
	all_day?: boolean;
	color?: string | null;
	description?: string | null;
	start?: string | null;
	end?: string | null;
	start_label?: string | null;
	end_label?: string | null;
	timezone?: string | null;
	reference_type?: string | null;
	reference_name?: string | null;
}
