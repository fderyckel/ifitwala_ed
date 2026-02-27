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
	amended_from?: string | null;
	change_summary?: string | null;
	change_stats?: {
		added?: number | null;
		removed?: number | null;
		modified?: number | null;
	} | null;
	diff_html?: string | null;
	policy_text_html?: string | null;
};
