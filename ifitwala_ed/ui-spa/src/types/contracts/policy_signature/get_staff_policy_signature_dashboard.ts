// ui-spa/src/types/contracts/policy_signature/get_staff_policy_signature_dashboard.ts

export type Request = {
	policy_version: string;
	organization?: string | null;
	school?: string | null;
	employee_group?: string | null;
	limit?: number;
};

export type StaffPolicySignatureRow = {
	employee: string;
	employee_name: string;
	user_id?: string | null;
	organization?: string | null;
	school?: string | null;
	employee_group?: string | null;
	is_signed: boolean;
	acknowledged_at?: string | null;
	acknowledged_by?: string | null;
};

export type StaffPolicySignatureBreakdown = {
	label: string;
	signed: number;
	pending: number;
	total: number;
	completion_pct: number;
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
		target_employee_rows: number;
		eligible_users: number;
		signed: number;
		pending: number;
		completion_pct: number;
		skipped_scope: number;
	};
	breakdowns: {
		by_organization: StaffPolicySignatureBreakdown[];
		by_school: StaffPolicySignatureBreakdown[];
		by_employee_group: StaffPolicySignatureBreakdown[];
	};
	rows: {
		pending: StaffPolicySignatureRow[];
		signed: StaffPolicySignatureRow[];
	};
};
