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

export type AdmissionsInboxMutationResponse = {
	ok: boolean;
	[key: string]: unknown;
};

export type AdmissionMessageDirection = 'Inbound' | 'Outbound' | 'System';
export type AdmissionMessageType =
	| 'Text'
	| 'Image'
	| 'Document'
	| 'Audio'
	| 'Video'
	| 'Sticker'
	| 'Template'
	| 'System';
export type AdmissionMessageDeliveryStatus =
	| 'Received'
	| 'Queued'
	| 'Sent'
	| 'Delivered'
	| 'Read'
	| 'Failed'
	| 'Logged';

export type LogAdmissionMessageRequest = {
	conversation?: string | null;
	inquiry?: string | null;
	student_applicant?: string | null;
	external_identity?: string | null;
	channel_account?: string | null;
	organization?: string | null;
	school?: string | null;
	assigned_to?: string | null;
	direction: AdmissionMessageDirection;
	body: string;
	message_type?: AdmissionMessageType;
	delivery_status?: AdmissionMessageDeliveryStatus;
	client_request_id?: string | null;
};

export type AdmissionCrmActivityType =
	| 'Call Attempt'
	| 'Reached'
	| 'No Answer'
	| 'Qualified'
	| 'Not Interested'
	| 'Booked Tour'
	| 'Attended Tour'
	| 'Follow-up Scheduled'
	| 'Archived'
	| 'Note';

export type RecordAdmissionCrmActivityRequest = {
	conversation: string;
	activity_type: AdmissionCrmActivityType;
	outcome?: string | null;
	note?: string | null;
	next_action_on?: string | null;
	client_request_id?: string | null;
};

export type LinkAdmissionConversationRequest = {
	conversation: string;
	inquiry?: string | null;
	student_applicant?: string | null;
	external_identity?: string | null;
	channel_account?: string | null;
	client_request_id?: string | null;
};

export type AdmissionExternalIdentityMatchStatus =
	| 'Unmatched'
	| 'Suggested'
	| 'Confirmed'
	| 'Rejected';

export type ConfirmAdmissionExternalIdentityRequest = {
	external_identity: string;
	match_status: AdmissionExternalIdentityMatchStatus;
	contact?: string | null;
	guardian?: string | null;
	inquiry?: string | null;
	student_applicant?: string | null;
	client_request_id?: string | null;
};

export type AssignAdmissionConversationRequest = {
	conversation: string;
	assigned_to: string;
	client_request_id?: string | null;
};

export type AdmissionConversationStatus = 'Open' | 'Closed' | 'Archived' | 'Spam';

export type UpdateAdmissionConversationStatusRequest = {
	conversation: string;
	status: AdmissionConversationStatus;
	note?: string | null;
	client_request_id?: string | null;
};

export type CreateInquiryFromAdmissionConversationRequest = {
	conversation: string;
	type_of_inquiry?: string | null;
	source?: string | null;
	message?: string | null;
	client_request_id?: string | null;
};

export type AssignInquiryFromInboxRequest = {
	inquiry: string;
	assigned_to: string;
	assignment_lane?: 'Admission' | 'Staff' | '' | null;
	client_request_id?: string | null;
};

export type ArchiveInquiryFromInboxRequest = {
	inquiry: string;
	reason: string;
	client_request_id?: string | null;
};

export type MarkInquiryContactedFromInboxRequest = {
	inquiry: string;
	complete_todo?: number | string | null;
	client_request_id?: string | null;
};

export type QualifyInquiryFromInboxRequest = {
	inquiry: string;
	client_request_id?: string | null;
};

export type InviteInquiryToApplyFromInboxRequest = {
	inquiry: string;
	school: string;
	organization?: string | null;
	client_request_id?: string | null;
};
