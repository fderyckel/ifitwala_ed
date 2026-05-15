// ui-spa/src/types/contracts/policy_signature/launch_staff_policy_campaign.ts

import type { PreviewCounts } from '@/types/contracts/policy_signature/get_staff_policy_campaign_options';

export type Request = {
	policy_version: string;
	organization: string;
	school?: string | null;
	employee_group?: string | null;
	due_date?: string | null;
	message?: string | null;
	client_request_id?: string | null;
};

export type Response = {
	ok: boolean;
	idempotent: boolean;
	status: 'processed' | 'already_processed';
	policy_version: string;
	organization: string;
	school?: string | null;
	employee_group?: string | null;
	counts: PreviewCounts & {
		created: number;
	};
	created_todos?: string[];
};
