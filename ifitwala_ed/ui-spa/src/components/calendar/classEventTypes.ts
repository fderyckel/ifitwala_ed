export interface ClassEventDetails {
	id: string;
	student_group: string;
	title: string;
	class_type?: string | null;
	program?: string | null;
	course?: string | null;
	course_name?: string | null;
	cohort?: string | null;
	school?: string | null;
	rotation_day?: number | null;
	block_number?: number | null;
	block_label?: string | null;
	session_date?: string | null;
	location?: string | null;
	start?: string | null;
	end?: string | null;
	start_label?: string | null;
	end_label?: string | null;
	timezone?: string | null;
}
