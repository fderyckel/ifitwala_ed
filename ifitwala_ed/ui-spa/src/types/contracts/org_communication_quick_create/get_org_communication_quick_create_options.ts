// ui-spa/src/types/contracts/org_communication_quick_create/get_org_communication_quick_create_options.ts

export type Request = {
	prefill_student_group?: string | null
}

export type OrgCommunicationQuickContext = {
	default_school: string | null
	default_organization: string | null
	allowed_schools: string[]
	allowed_organizations: string[]
	is_privileged: boolean
	can_select_school: boolean
	lock_to_default_school: boolean
}

export type OrgCommunicationQuickDefaults = {
	communication_type: string
	status: string
	priority: string
	portal_surface: string
	interaction_mode: string
	allow_private_notes: 0 | 1
	allow_public_thread: 0 | 1
}

export type OrgCommunicationQuickFields = {
	communication_types: string[]
	statuses: string[]
	priorities: string[]
	portal_surfaces: string[]
	interaction_modes: string[]
	audience_target_modes: string[]
}

export type OrgCommunicationRecipientRule = {
	allowed_fields: string[]
	allowed_labels: string[]
	default_fields: string[]
}

export type OrgCommunicationQuickReferenceOrganization = {
	name: string
	organization_name?: string | null
	abbr?: string | null
}

export type OrgCommunicationQuickReferenceSchool = {
	name: string
	school_name?: string | null
	abbr?: string | null
	organization?: string | null
}

export type OrgCommunicationQuickReferenceTeam = {
	name: string
	team_name?: string | null
	team_code?: string | null
	school?: string | null
	organization?: string | null
}

export type OrgCommunicationQuickReferenceStudentGroup = {
	name: string
	student_group_name?: string | null
	student_group_abbreviation?: string | null
	school?: string | null
	group_based_on?: string | null
}

export type OrgCommunicationAudiencePreset = {
	key: string
	label: string
	description: string
	target_mode: string
	default_fields: string[]
	picker_kind?: 'team' | 'student_group' | null
}

export type OrgCommunicationQuickDeliveryProfileKey =
	| 'undecided'
	| 'staff_only'
	| 'portal_only'
	| 'mixed'

export type OrgCommunicationQuickDeliveryProfile = {
	allowed_portal_surfaces: string[]
	preferred_portal_surface: string
	help_text: string
}

export type OrgCommunicationQuickDeliveryRules = {
	brief_portal_surfaces: string[]
	profiles: Record<OrgCommunicationQuickDeliveryProfileKey, OrgCommunicationQuickDeliveryProfile>
}

export type Response = {
	context: OrgCommunicationQuickContext
	defaults: OrgCommunicationQuickDefaults
	fields: OrgCommunicationQuickFields
	recipient_rules: Record<string, OrgCommunicationRecipientRule>
	audience_presets: OrgCommunicationAudiencePreset[]
	references: {
		organizations: OrgCommunicationQuickReferenceOrganization[]
		schools: OrgCommunicationQuickReferenceSchool[]
	}
	suggested_targets: {
		teams: OrgCommunicationQuickReferenceTeam[]
		student_groups: OrgCommunicationQuickReferenceStudentGroup[]
	}
	permissions: {
		can_create: boolean
		blocked_reason?: string | null
		can_target_wide_school_scope: boolean
	}
	delivery_rules: OrgCommunicationQuickDeliveryRules
}
