// ui-spa/src/lib/services/focus/focusService.ts

import { createResource } from 'frappe-ui'
import { SIGNAL_FOCUS_INVALIDATE, SIGNAL_STUDENT_LOG_INVALIDATE, uiSignals } from '@/lib/uiSignals'

import type {
	Request as GetFocusContextRequest,
	Response as GetFocusContextResponse,
} from '@/types/contracts/focus/get_focus_context'
import type {
	Request as SubmitStudentLogFollowUpRequest,
	Response as SubmitStudentLogFollowUpResponse,
} from '@/types/contracts/focus/submit_student_log_follow_up'
import type {
	Request as ReviewStudentLogOutcomeRequest,
	Response as ReviewStudentLogOutcomeResponse,
} from '@/types/contracts/focus/review_student_log_outcome'

/**
 * Transport normalization (A+)
 * - Accept unknown at the boundary.
 * - Normalize once.
 * - Return ONLY the contract type downstream (no union types).
 *
 * Handles:
 * - { message: T }
 * - Axios-ish: { data: { message: T } } / { data: T }
 * - Raw T
 */
function unwrapMessage<T>(res: unknown): T {
	const root =
		res && typeof res === 'object' && 'data' in (res as any) ? (res as any).data : res

	if (root && typeof root === 'object' && 'message' in (root as any)) {
		return (root as any).message as T
	}
	return root as T
}

/**
 * A+ invalidation helper:
 * Emit ONLY after a successful workflow mutation.
 * (No emissions on thrown errors / failed responses.)
 */
function emitAfterStudentLogMutation() {
	uiSignals.emit(SIGNAL_STUDENT_LOG_INVALIDATE)
	uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)
}

export function createFocusService() {
	const getFocusContextResource = createResource<GetFocusContextResponse>({
		url: 'ifitwala_ed.api.focus.get_focus_context',
		method: 'POST',
		auto: false,
		transform: (res: unknown) => unwrapMessage<GetFocusContextResponse>(res),
	})

	const submitFollowUpResource = createResource<SubmitStudentLogFollowUpResponse>({
		url: 'ifitwala_ed.api.focus.submit_student_log_follow_up',
		method: 'POST',
		auto: false,
		transform: (res: unknown) => unwrapMessage<SubmitStudentLogFollowUpResponse>(res),
	})

	const reviewOutcomeResource = createResource<ReviewStudentLogOutcomeResponse>({
		url: 'ifitwala_ed.api.focus.review_student_log_outcome',
		method: 'POST',
		auto: false,
		transform: (res: unknown) => unwrapMessage<ReviewStudentLogOutcomeResponse>(res),
	})

	async function getFocusContext(payload: GetFocusContextRequest) {
		return getFocusContextResource.submit(payload)
	}

	async function submitStudentLogFollowUp(payload: SubmitStudentLogFollowUpRequest) {
		const response = await submitFollowUpResource.submit(payload)

		// Emit invalidation only on success
		if ((response as any)?.ok) emitAfterStudentLogMutation()

		return response
	}

	async function reviewStudentLogOutcome(payload: ReviewStudentLogOutcomeRequest) {
		const response = await reviewOutcomeResource.submit(payload)

		// Emit invalidation only on success
		if ((response as any)?.ok) emitAfterStudentLogMutation()

		return response
	}

	return {
		getFocusContext,
		submitStudentLogFollowUp,
		reviewStudentLogOutcome,
	}
}
