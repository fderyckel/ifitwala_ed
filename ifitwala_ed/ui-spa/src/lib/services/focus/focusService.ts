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
	const root = (() => {
		if (!res || typeof res !== 'object') return res
		if ('data' in (res as Record<string, unknown>)) return (res as { data?: unknown }).data
		return res
	})()

	if (root && typeof root === 'object' && 'message' in (root as Record<string, unknown>)) {
		return (root as { message?: unknown }).message as T
	}
	return root as T
}

function isOkResponse(value: unknown): value is { ok: true } {
	return !!value && typeof value === 'object' && (value as { ok?: unknown }).ok === true
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

	async function getFocusContext(payload: GetFocusContextRequest): Promise<GetFocusContextResponse> {
		return getFocusContextResource.submit(payload)
	}

	async function submitStudentLogFollowUp(
		payload: SubmitStudentLogFollowUpRequest,
	): Promise<SubmitStudentLogFollowUpResponse> {
		const response = await submitFollowUpResource.submit(payload)

		if (isOkResponse(response)) emitAfterStudentLogMutation()

		return response
	}

	async function reviewStudentLogOutcome(
		payload: ReviewStudentLogOutcomeRequest,
	): Promise<ReviewStudentLogOutcomeResponse> {
		const response = await reviewOutcomeResource.submit(payload)

		if (isOkResponse(response)) emitAfterStudentLogMutation()

		return response
	}

	return {
		getFocusContext,
		submitStudentLogFollowUp,
		reviewStudentLogOutcome,
	}
}
