import type {
	FamilyConsentAudienceMode,
	FamilyConsentCompletionChannelMode,
	FamilyConsentRequestStatus,
	FamilyConsentRequestType,
} from '@/types/contracts/family_consent/get_family_consent_dashboard'

export type Request = {
	organization?: string | null
}

export type Response = {
	filters: {
		organization?: string | null
	}
	options: {
		organizations: string[]
		schools: string[]
		request_types: FamilyConsentRequestType[]
		statuses: FamilyConsentRequestStatus[]
		audience_modes: FamilyConsentAudienceMode[]
		completion_channel_modes: FamilyConsentCompletionChannelMode[]
	}
}
