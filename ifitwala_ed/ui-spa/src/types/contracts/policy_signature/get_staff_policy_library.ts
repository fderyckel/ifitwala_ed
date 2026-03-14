// ui-spa/src/types/contracts/policy_signature/get_staff_policy_library.ts

export type Request = {
	organization?: string | null;
	school?: string | null;
	employee_group?: string | null;
};

export type StaffPolicyLibraryRow = {
	institutional_policy: string;
	policy_version: string;
	policy_key?: string | null;
	policy_title?: string | null;
	policy_category?: string | null;
	version_label?: string | null;
	description: string;
	policy_organization?: string | null;
	policy_school?: string | null;
	effective_from?: string | null;
	effective_to?: string | null;
	approved_on?: string | null;
	based_on_version?: string | null;
	change_summary?: string | null;
	signature_required: boolean;
	acknowledgement_status: 'informational' | 'pending' | 'new_version' | 'signed';
	acknowledged_at?: string | null;
};

export type Response = {
	meta: {
		generated_at: string;
		user: string;
		employee?: {
			name?: string | null;
			employee_full_name?: string | null;
			organization?: string | null;
			school?: string | null;
			employee_group?: string | null;
			user_id?: string | null;
		} | null;
	};
	filters: {
		organization?: string | null;
		school?: string | null;
		employee_group?: string | null;
	};
	options: {
		organizations: string[];
		schools: string[];
		employee_groups: string[];
	};
	counts: {
		total_policies: number;
		signature_required: number;
		informational: number;
		signed: number;
		pending: number;
		new_version: number;
	};
	rows: StaffPolicyLibraryRow[];
};
