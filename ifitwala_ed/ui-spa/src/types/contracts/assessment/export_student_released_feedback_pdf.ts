import type { FeedbackArtifact } from './feedback_artifact'

export type Request = {
	outcome_id: string
}

export type Response = {
	artifact: FeedbackArtifact
}
