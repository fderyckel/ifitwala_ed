export type FamilyConsentRequestType = 'One-off Permission Request' | 'Mutable Consent'

export type FamilyConsentRequestStatus = 'Draft' | 'Published' | 'Closed' | 'Archived'

export type FamilyConsentAudienceMode = 'Guardian' | 'Student' | 'Guardian + Student'

export type FamilyConsentCompletionChannelMode =
	| 'Portal Only'
	| 'Portal Or Paper'
	| 'Paper Only'

export type Request = {
	organization?: string | null
	school?: string | null
	request_type?: FamilyConsentRequestType | null
	status?: FamilyConsentRequestStatus | null
	audience_mode?: FamilyConsentAudienceMode | null
	completion_channel_mode?: FamilyConsentCompletionChannelMode | null
}

export type FamilyConsentDashboardRow = {
	family_consent_request: string
	request_key: string
	request_title: string
	request_type: FamilyConsentRequestType
	audience_mode: FamilyConsentAudienceMode
	signer_rule: string
	completion_channel_mode: FamilyConsentCompletionChannelMode
	status: FamilyConsentRequestStatus
	organization: string
	school?: string | null
	due_on?: string | null
	target_count: number
	pending_count: number
	completed_count: number
	declined_count: number
	withdrawn_count: number
	expired_count: number
	overdue_count: number
}

export type Response = {
	meta: {
		generated_at: string
	}
	filters: {
		organization?: string | null
		school?: string | null
		request_type?: FamilyConsentRequestType | null
		status?: FamilyConsentRequestStatus | null
		audience_mode?: FamilyConsentAudienceMode | null
		completion_channel_mode?: FamilyConsentCompletionChannelMode | null
	}
	counts: {
		requests: number
		pending: number
		completed: number
		declined: number
		withdrawn: number
		expired: number
		overdue: number
	}
	rows: FamilyConsentDashboardRow[]
}
