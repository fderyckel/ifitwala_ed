import type {
	PolicySignatureAudience,
	PolicySignatureAudienceRow,
} from '@/types/contracts/policy_signature/get_staff_policy_signature_dashboard';

export type PolicySignatureRegisterStatus = 'all' | 'pending' | 'signed';

export type Request = {
	policy_version: string;
	audience: PolicySignatureAudience;
	organization?: string | null;
	school?: string | null;
	employee_group?: string | null;
	status?: PolicySignatureRegisterStatus | null;
	query?: string | null;
	page?: number;
	limit?: number;
};

export type Response = {
	audience: PolicySignatureAudience;
	audience_label: string;
	workflow_description: string;
	supports_campaign_launch: boolean;
	status: PolicySignatureRegisterStatus;
	query?: string | null;
	rows: PolicySignatureAudienceRow[];
	pagination: {
		page: number;
		limit: number;
		total_rows: number;
		total_pages: number;
	};
};
