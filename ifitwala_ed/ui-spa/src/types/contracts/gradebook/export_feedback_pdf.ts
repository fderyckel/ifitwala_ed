import type { FeedbackArtifact } from '@/types/contracts/assessment/feedback_artifact'

export type Request = {
	outcome_id: string
	submission_id?: string | null
}

export type Response = {
	artifact: FeedbackArtifact
}
