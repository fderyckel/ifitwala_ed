import type { SubmissionEvidence } from '@/types/contracts/gradebook/get_drawer'

export type Request = {
	outcome_id: string
}

export type Response = SubmissionEvidence | null
