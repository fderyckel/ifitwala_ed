// ui-spa/src/types/contracts/student/get_student_policy_overview.ts

export type Request = Record<string, never>

export type PolicyAcknowledgementClause = {
	name: string
	clause_text: string
	is_required: boolean
	idx: number
}

export type Response = {
	meta: {
		generated_at: string
		student: { name: string | null }
	}
	identity: {
		student: string
		user: string
	}
	counts: {
		total_policies: number
		acknowledged_policies: number
		pending_policies: number
	}
	rows: StudentPolicyRow[]
}

export type StudentPolicyRow = {
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
	expected_signature_name: string
	acknowledgement_clauses: PolicyAcknowledgementClause[]
	ack_context_doctype: 'Student'
	ack_context_name: string
	is_acknowledged: boolean
	acknowledged_at: string
	acknowledged_by: string
}
