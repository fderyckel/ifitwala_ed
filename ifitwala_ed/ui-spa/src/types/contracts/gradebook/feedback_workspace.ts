export type FeedbackVisibility = 'hidden' | 'student' | 'student_and_guardian'

export type FeedbackItemKind = 'point' | 'rect' | 'page' | 'text_quote' | 'path'

export type FeedbackIntent =
	| 'strength'
	| 'issue'
	| 'question'
	| 'next_step'
	| 'rubric_evidence'

export type FeedbackWorkflowState = 'draft' | 'published' | 'acknowledged' | 'resolved'
export type FeedbackThreadTargetType = 'feedback_item' | 'priority' | 'summary'
export type FeedbackThreadLearnerState = 'none' | 'understood' | 'acted_on'
export type FeedbackThreadStatus = 'open' | 'resolved'
export type FeedbackThreadMessageKind = 'reply' | 'clarification'
export type FeedbackThreadAuthorRole = 'student' | 'instructor'

export type FeedbackAnchor =
	| {
			kind: 'page'
			page: number
	  }
	| {
			kind: 'point'
			page: number
			point: {
				x: number
				y: number
			}
	  }
	| {
			kind: 'rect'
			page: number
			rect: {
				x: number
				y: number
				width: number
				height: number
			}
	  }
	| {
			kind: 'text_quote'
			page: number
			quote: string
			rects?: unknown[]
			selector?: Record<string, unknown>
	  }
	| {
			kind: 'path'
			page: number
			strokes: unknown[]
	  }

export type FeedbackWorkspaceItem = {
	id?: string | null
	kind: FeedbackItemKind
	page: number
	intent: FeedbackIntent
	workflow_state: FeedbackWorkflowState
	comment: string
	anchor: FeedbackAnchor
	assessment_criteria?: string | null
	author?: string | null
}

export type FeedbackPriority = {
	id?: string | null
	title: string
	detail?: string | null
	feedback_item_id?: string | null
	assessment_criteria?: string | null
}

export type FeedbackThreadMessage = {
	id?: string | null
	author?: string | null
	author_role: FeedbackThreadAuthorRole
	message_kind: FeedbackThreadMessageKind
	body: string
	created?: string | null
}

export type FeedbackThread = {
	thread_id: string
	target_type: FeedbackThreadTargetType
	target_feedback_item?: string | null
	target_priority?: string | null
	summary_field?: 'overall' | 'strengths' | 'improvements' | 'next_steps' | null
	learner_state: FeedbackThreadLearnerState
	thread_status: FeedbackThreadStatus
	messages: FeedbackThreadMessage[]
	modified?: string | null
	modified_by?: string | null
}

export type FeedbackWorkspacePayload = {
	workspace_id?: string | null
	task_outcome: string
	task_submission: string
	submission_version?: number | null
	summary: {
		overall: string
		strengths: string
		improvements: string
		next_steps: string
	}
	priorities: FeedbackPriority[]
	items: FeedbackWorkspaceItem[]
	publication: {
		feedback_visibility: FeedbackVisibility
		grade_visibility: FeedbackVisibility
		derived_from_legacy_outcome: boolean
		legacy_outcome_published: boolean
		legacy_published_on?: string | null
		legacy_published_by?: string | null
	}
	modified?: string | null
	modified_by?: string | null
}
