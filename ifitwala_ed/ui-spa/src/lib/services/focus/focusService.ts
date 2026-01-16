// ui-spa/src/lib/services/focus/focusService.ts

import { createResource } from 'frappe-ui'
import {
	SIGNAL_FOCUS_INVALIDATE,
	SIGNAL_STUDENT_LOG_INVALIDATE,
	uiSignals,
} from '@/lib/uiSignals'

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
 * Transport normalization (A+ — LOCKED)
 * ------------------------------------------------------------
 * Boundary rules:
 * - Input is unknown
 * - Backend MUST return an envelope: { message: T }
 * - Axios shapes may wrap that envelope
 * - Raw T is NOT accepted
 *
 * If this throws, the backend contract is broken.
 * That is intentional.
 */
function normalizeMessage<T>(res: unknown): T {
	// Axios-style: { data: ... }
	const root =
		res && typeof res === 'object' && 'data' in res
			? (res as any).data
			: res

	if (root && typeof root === 'object' && 'message' in root) {
		return (root as any).message as T
	}

	throw new Error(
		'[focusService] Invalid response shape: expected { message: T } envelope'
	)
}

export function createFocusService() {
	/* ------------------------------------------------------------
	 * Resources (transport owned here, nowhere else)
	 * ---------------------------------------------------------- */

	const getFocusContextResource = createResource<GetFocusContextResponse>({
		url: 'ifitwala_ed.api.focus.get_focus_context',
		method: 'POST',
		auto: false,
		transform: (res: unknown) => normalizeMessage<GetFocusContextResponse>(res),
	})

	const submitFollowUpResource = createResource<SubmitStudentLogFollowUpResponse>({
		url: 'ifitwala_ed.api.focus.submit_student_log_follow_up',
		method: 'POST',
		auto: false,
		transform: (res: unknown) =>
			normalizeMessage<SubmitStudentLogFollowUpResponse>(res),
	})

	const reviewOutcomeResource = createResource<ReviewStudentLogOutcomeResponse>({
		url: 'ifitwala_ed.api.focus.review_student_log_outcome',
		method: 'POST',
		auto: false,
		transform: (res: unknown) =>
			normalizeMessage<ReviewStudentLogOutcomeResponse>(res),
	})

	/* ------------------------------------------------------------
	 * Public API (domain-only, no transport leakage)
	 * ---------------------------------------------------------- */

	async function getFocusContext(
		payload: GetFocusContextRequest
	): Promise<GetFocusContextResponse> {
		return getFocusContextResource.submit(payload)
	}

	async function submitStudentLogFollowUp(
		payload: SubmitStudentLogFollowUpRequest
	): Promise<SubmitStudentLogFollowUpResponse> {
		const response = await submitFollowUpResource.submit(payload)

		// A+ rule: services emit invalidation, not views
		uiSignals.emit(SIGNAL_STUDENT_LOG_INVALIDATE)
		uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)

		return response
	}

	async function reviewStudentLogOutcome(
		payload: ReviewStudentLogOutcomeRequest
	): Promise<ReviewStudentLogOutcomeResponse> {
		const response = await reviewOutcomeResource.submit(payload)

		uiSignals.emit(SIGNAL_STUDENT_LOG_INVALIDATE)
		uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)

		return response
	}

	return {
		getFocusContext,
		submitStudentLogFollowUp,
		reviewStudentLogOutcome,
	}
}
