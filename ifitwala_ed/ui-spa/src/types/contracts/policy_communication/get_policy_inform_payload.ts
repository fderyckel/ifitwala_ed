// ui-spa/src/types/contracts/policy_communication/get_policy_inform_payload.ts

export type Request = {
	policy_version: string;
	org_communication?: string | null;
};

export type Response = {
	policy_version: string;
	institutional_policy?: string | null;
	policy_key?: string | null;
	policy_title?: string | null;
	policy_label?: string | null;
	version_label?: string | null;
	policy_organization?: string | null;
	policy_school?: string | null;
	based_on_version?: string | null;
	change_summary?: string | null;
	change_stats?: {
		added?: number | null;
		removed?: number | null;
		modified?: number | null;
	} | null;
	diff_html?: string | null;
	policy_text_html?: string | null;
	history?: Array<{
		policy_version: string;
		version_label?: string | null;
		based_on_version?: string | null;
		effective_from?: string | null;
		effective_to?: string | null;
		approved_on?: string | null;
		is_active: boolean;
	}>;
	signature_required?: boolean;
	acknowledgement_status?: 'informational' | 'pending' | 'new_version' | 'signed';
	acknowledged_at?: string | null;
};
