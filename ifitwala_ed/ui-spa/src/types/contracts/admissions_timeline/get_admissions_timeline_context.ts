export type AdmissionsTimelineContextDoctype =
	| 'Inquiry'
	| 'Student Applicant'
	| 'Admission Conversation';

export type AdmissionsTimelineRequest = {
	context_doctype: AdmissionsTimelineContextDoctype;
	context_name: string;
	limit?: number | string | null;
};

export type AdmissionsTimelineAction = {
	id: string;
	label?: string | null;
	enabled: boolean;
	target?: string | null;
	disabled_reason?: string | null;
};

export type AdmissionsTimelineItem = {
	id: string;
	kind: string;
	source_doctype: string;
	source_name: string;
	occurred_at?: string | null;
	title: string;
	summary?: string | null;
	actor?: string | null;
	visibility: string;
	context_labels: Record<string, string | null | undefined>;
	open_url?: string | null;
	actions: AdmissionsTimelineAction[];
};

export type AdmissionsTimelineLadderStep = {
	id: string;
	label: string;
	state: 'done' | 'current' | 'pending' | string;
	source?: string | null;
};

export type AdmissionsTimelineSummary = {
	headline?: string | null;
	latest_at?: string | null;
	needs_reply: boolean;
	counts: Record<string, number>;
	completion_ladder: AdmissionsTimelineLadderStep[];
};

export type AdmissionsTimelineContext = {
	ok: boolean;
	generated_at?: string | null;
	context: {
		doctype: AdmissionsTimelineContextDoctype;
		name: string;
		label?: string | null;
		organization?: string | null;
		school?: string | null;
		inquiry?: string | null;
		student_applicant?: string | null;
		conversation?: string | null;
		limit: number;
	};
	summary: AdmissionsTimelineSummary;
	items: AdmissionsTimelineItem[];
	actions: AdmissionsTimelineAction[];
	has_more: boolean;
	sources: Record<string, number>;
};
