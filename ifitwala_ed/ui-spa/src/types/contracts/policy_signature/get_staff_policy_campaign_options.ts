// ui-spa/src/types/contracts/policy_signature/get_staff_policy_campaign_options.ts

export type Request = {
	organization?: string | null;
	school?: string | null;
	employee_group?: string | null;
	policy_version?: string | null;
};

export type PolicyOption = {
	policy_version: string;
	version_label?: string | null;
	effective_from?: string | null;
	effective_to?: string | null;
	institutional_policy?: string | null;
	policy_title?: string | null;
	policy_key?: string | null;
	policy_organization?: string | null;
	policy_school?: string | null;
};

export type PreviewCounts = {
	target_employee_rows: number;
	eligible_users: number;
	already_signed: number;
	already_open: number;
	to_create: number;
	skipped_scope: number;
};

export type Response = {
	options: {
		organizations: string[];
		schools: string[];
		employee_groups: string[];
		policies: PolicyOption[];
	};
	preview: PreviewCounts;
};
