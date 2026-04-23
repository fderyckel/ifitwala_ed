// ui-spa/src/types/contracts/policy_signature/get_staff_policy_library.ts

export type Request = {
	organization?: string | null;
	school?: string | null;
	audience?: 'All' | 'Staff' | 'Guardian' | 'Student' | null;
};

export type PolicyLibraryRow = {
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
	applies_to_tokens: Array<'Staff' | 'Guardian' | 'Student'>;
	signature_required?: boolean | null;
	acknowledgement_status?: 'informational' | 'pending' | 'new_version' | 'signed' | null;
	acknowledged_at?: string | null;
};

export type Response = {
	meta: {
		generated_at: string;
		user: string;
		can_manage_audiences?: boolean;
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
		audience?: 'All' | 'Staff' | 'Guardian' | 'Student' | null;
	};
	options: {
		organizations: string[];
		schools: string[];
		audiences: Array<'All' | 'Staff' | 'Guardian' | 'Student'>;
	};
	counts: {
		total_policies: number;
		staff_policies: number;
		guardian_policies: number;
		student_policies: number;
		organization_scoped: number;
		school_scoped: number;
		multi_audience: number;
		signature_required: number;
		informational: number;
		signed: number;
		pending: number;
		new_version: number;
	};
	rows: PolicyLibraryRow[];
};
