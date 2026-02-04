export interface MeetingParticipantSummary {
	participant: string | null;
	participant_name: string | null;
	employee: string | null;
	role_in_meeting: string | null;
	attendance_status: string | null;
}

export interface MeetingDetails {
	name: string;
	title: string;
	status?: string | null;
	date?: string | null;
	start?: string | null;
	end?: string | null;
	start_label?: string | null;
	end_label?: string | null;
	location?: string | null;
	virtual_link?: string | null;
	meeting_category?: string | null;
	agenda?: string | null;
	minutes?: string | null;
	timezone?: string | null;
	participants: MeetingParticipantSummary[];
	participant_count: number;
	leaders: MeetingParticipantSummary[];
	team?: string | null;
	team_name?: string | null;
	team_color?: string | null;
	school?: string | null;
	academic_year?: string | null;
}
