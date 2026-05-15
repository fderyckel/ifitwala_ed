import type { SubmissionEvidence } from '@/types/contracts/gradebook/get_drawer'
import type { ReleasedAssessmentResult } from './released_assessment_result'

export type Request = {
	outcome_id: string
}

export type Response =
	| (SubmissionEvidence & {
			released_result?: ReleasedAssessmentResult | null
	  })
	| null
