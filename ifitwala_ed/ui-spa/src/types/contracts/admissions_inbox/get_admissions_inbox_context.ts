export type AdmissionsInboxRequest = {
	organization?: string | null;
	school?: string | null;
	limit?: number | string | null;
};

export type AdmissionsInboxAction = {
	id: string;
	enabled: boolean;
	disabled_reason?: string | null;
};

export type AdmissionsInboxRow = {
	id: string;
	kind: 'conversation' | 'inquiry' | 'student_applicant' | string;
	stage: string;
	title: string;
	subtitle?: string | null;
	organization?: string | null;
	school?: string | null;
	inquiry?: string | null;
	student_applicant?: string | null;
	conversation?: string | null;
	open_url?: string | null;
	external_identity?: string | null;
	channel_type?: string | null;
	channel_account?: string | null;
	owner?: string | null;
	sla_state?: string | null;
	last_activity_at?: string | null;
	last_message_preview?: string | null;
	needs_reply: boolean;
	unread_count: number;
	next_action_on?: string | null;
	permissions: Record<string, boolean>;
	actions: AdmissionsInboxAction[];
};

export type AdmissionsInboxQueue = {
	id: string;
	label: string;
	count: number;
	rows: AdmissionsInboxRow[];
	has_more: boolean;
};

export type AdmissionsInboxContext = {
	ok: boolean;
	generated_at?: string | null;
	filters: {
		organization?: string | null;
		school?: string | null;
		limit: number;
	};
	queues: AdmissionsInboxQueue[];
	sources: Record<string, number>;
};
