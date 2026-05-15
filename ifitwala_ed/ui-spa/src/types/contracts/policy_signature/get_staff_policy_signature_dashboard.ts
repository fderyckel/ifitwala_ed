// ui-spa/src/types/contracts/policy_signature/get_staff_policy_signature_dashboard.ts

export type Request = {
	policy_version: string;
	organization?: string | null;
	school?: string | null;
	employee_group?: string | null;
	limit?: number;
};

export type PolicySignatureAudience = 'Staff' | 'Guardian' | 'Student';

export type PolicySignatureAudienceRow = {
	record_id: string;
	subject_name: string;
	subject_subtitle?: string | null;
	context_label?: string | null;
	user_id?: string | null;
	organization?: string | null;
	school?: string | null;
	is_signed: boolean;
	acknowledged_at?: string | null;
	acknowledged_by?: string | null;
};

export type PolicySignatureBreakdown = {
	label: string;
	signed: number;
	pending: number;
	total: number;
	completion_pct: number;
};

export type PolicySignatureAudienceSection = {
	audience: PolicySignatureAudience;
	audience_label: string;
	workflow_description: string;
	supports_campaign_launch: boolean;
	summary: {
		target_rows: number;
		eligible_targets: number;
		signed: number;
		pending: number;
		completion_pct: number;
		skipped_scope: number;
		already_open: number;
		to_create: number;
	};
	breakdowns: {
		by_organization: PolicySignatureBreakdown[];
		by_school: PolicySignatureBreakdown[];
		by_context: PolicySignatureBreakdown[];
		context_label?: string | null;
	};
	rows: {
		pending: PolicySignatureAudienceRow[];
		signed: PolicySignatureAudienceRow[];
	};
};

export type Response = {
	summary: {
		policy_version: string;
		institutional_policy?: string | null;
		policy_key?: string | null;
		policy_title?: string | null;
		version_label?: string | null;
		effective_from?: string | null;
		effective_to?: string | null;
		organization?: string | null;
		school?: string | null;
		employee_group?: string | null;
		applies_to_tokens: PolicySignatureAudience[];
		eligible_targets: number;
		signed: number;
		pending: number;
		completion_pct: number;
		skipped_scope: number;
	};
	audiences: PolicySignatureAudienceSection[];
};
