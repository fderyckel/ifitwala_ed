import type {
	FamilyPolicyCampaignAudience,
	GuardianAcknowledgementMode,
} from '@/types/contracts/policy_signature/get_family_policy_campaign_options';

export type Request = {
	policy_version: string;
	organization: string;
	school?: string | null;
	audiences: FamilyPolicyCampaignAudience[];
	guardian_acknowledgement_mode?: GuardianAcknowledgementMode | null;
	title?: string | null;
	message?: string | null;
	publish_to?: string | null;
	client_request_id?: string | null;
};

export type Response = {
	ok: boolean;
	idempotent: boolean;
	status: 'processed' | 'already_processed';
	policy_version: string;
	organization: string;
	school?: string | null;
	audiences: FamilyPolicyCampaignAudience[];
	guardian_acknowledgement_mode?: GuardianAcknowledgementMode | null;
	counts: {
		published: number;
		pending: number;
		school_targets: number;
	};
	communications: Array<{
		audience: FamilyPolicyCampaignAudience;
		audience_label: string;
		org_communication: string;
		title: string;
		href: string;
		pending: number;
	}>;
};
