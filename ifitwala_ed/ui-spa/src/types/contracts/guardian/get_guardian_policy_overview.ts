// ui-spa/src/types/contracts/guardian/get_guardian_policy_overview.ts

import type { ChildRef } from '@/types/contracts/guardian/get_guardian_home_snapshot'

export type Request = Record<string, never>

export type Response = {
	meta: {
		generated_at: string
		guardian: { name: string | null }
	}
	family: {
		children: ChildRef[]
	}
	counts: {
		total_policies: number
		acknowledged_policies: number
		pending_policies: number
	}
	rows: GuardianPolicyRow[]
}

export type GuardianPolicyRow = {
	policy_name: string
	policy_key: string
	policy_title: string
	policy_category: string
	policy_version: string
	version_label: string
	organization: string
	school: string
	description: string
	policy_text: string
	effective_from: string
	effective_to: string
	approved_on: string
	ack_context_doctype: 'Guardian'
	ack_context_name: string
	is_acknowledged: boolean
	acknowledged_at: string
	acknowledged_by: string
}
