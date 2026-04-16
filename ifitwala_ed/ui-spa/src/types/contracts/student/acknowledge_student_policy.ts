// ui-spa/src/types/contracts/student/acknowledge_student_policy.ts

export type Request = {
	policy_version: string
	typed_signature_name: string
	attestation_confirmed: 0 | 1
	checked_clause_names?: string[] | null
}

export type Response = {
	ok: boolean
	status: 'acknowledged' | 'already_acknowledged'
	acknowledgement_name: string
	policy_version: string
}
