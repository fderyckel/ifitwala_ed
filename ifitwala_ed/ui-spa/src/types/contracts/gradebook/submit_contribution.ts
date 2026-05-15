import type { CriteriaScoreUpdate } from './update_task_student'

export type Request = {
	task_outcome: string
	task_submission?: string | null
	contribution_type?: 'Self' | 'Peer Review' | 'Moderator' | 'Official Override' | null
	score?: number | null
	feedback?: string | null
	judgment_code?: string | null
	rubric_scores?: CriteriaScoreUpdate[]
	evidence_note?: string | null
	name?: string | null
	draft_name?: string | null
}

export type Response = {
	ok: boolean
	outcome_update?: Record<string, unknown> | null
	result: {
		contribution: string
		status: string
		task_outcome: string
		task_submission?: string | null
		outcome_update?: Record<string, unknown> | null
	}
}
