import type { ConsentFieldValue } from '@/types/contracts/family_consent/shared'

export type Request = {
	request_key: string
	student: string
	decision_status: string
	typed_signature_name?: string
	attestation_confirmed?: number
	field_values?: Array<{ field_key: string; value: ConsentFieldValue }>
	profile_writeback_mode?: 'Form Only' | 'Update Profile'
}

export type Response = {
	ok: boolean
	status: 'submitted' | 'already_current'
	decision_name: string
	request_key: string
	student: string
	current_status: 'pending' | 'completed' | 'declined' | 'withdrawn' | 'expired' | 'overdue'
	profile_writeback_mode?: string | null
}
