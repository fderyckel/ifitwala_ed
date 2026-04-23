import type {
	PolicyOption,
	PolicySignatureAudience,
} from '@/types/contracts/policy_signature/get_staff_policy_campaign_options';

export type FamilyPolicyCampaignAudience = Exclude<PolicySignatureAudience, 'Staff'>;
export type GuardianAcknowledgementMode = 'Family Acknowledgement' | 'Child Acknowledgement';

export type Request = {
	organization?: string | null;
	school?: string | null;
	policy_version?: string | null;
	guardian_acknowledgement_mode?: GuardianAcknowledgementMode | null;
};

export type FamilyAudiencePreview = {
	audience: FamilyPolicyCampaignAudience;
	audience_label: string;
	workflow_description: string;
	eligible_targets: number;
	signed: number;
	pending: number;
	completion_pct: number;
	skipped_scope: number;
};

export type Response = {
	options: {
		organizations: string[];
		schools: string[];
		policies: PolicyOption[];
	};
	preview: {
		family_audiences: FamilyPolicyCampaignAudience[];
		guardian_acknowledgement_mode: GuardianAcknowledgementMode | null;
		guardian_acknowledgement_mode_locked: boolean;
		school_target_count: number;
		audience_previews: FamilyAudiencePreview[];
	};
};
