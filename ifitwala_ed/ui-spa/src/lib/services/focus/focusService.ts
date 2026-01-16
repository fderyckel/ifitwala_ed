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
 * Focus Service (A+ — LOCKED)
 * ------------------------------------------------------------
 * Rules:
 * - Backend contracts are authoritative
 * - No transport normalization
 * - No envelope handling
 * - No defensive branching
 * - Services emit uiSignals ONLY after successful mutations
 */

export function createFocusService() {
	/* ------------------------------------------------------------
	 * Resources (transport owned here, no normalization)
	 * ---------------------------------------------------------- */

	const getFocusContextResource = createResource<GetFocusContextResponse>({
		url: 'ifitwala_ed.api.focus.get_focus_context',
		method: 'POST',
		auto: false,
	})

	const submitFollowUpResource = createResource<SubmitStudentLogFollowUpResponse>({
		url: 'ifitwala_ed.api.focus.submit_student_log_follow_up',
		method: 'POST',
		auto: false,
	})

	const reviewOutcomeResource = createResource<ReviewStudentLogOutcomeResponse>({
		url: 'ifitwala_ed.api.focus.review_student_log_outcome',
		method: 'POST',
		auto: false,
	})

	/* ------------------------------------------------------------
	 * Public API (domain-only)
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

		// A+ rule: emit ONLY after a real mutation
		if (response.ok === true) {
			uiSignals.emit(SIGNAL_STUDENT_LOG_INVALIDATE)
			uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)
		}

		return response
	}

	async function reviewStudentLogOutcome(
		payload: ReviewStudentLogOutcomeRequest
	): Promise<ReviewStudentLogOutcomeResponse> {
		const response = await reviewOutcomeResource.submit(payload)

		// A+ rule: emit ONLY after a real mutation
		if (response.ok === true) {
			uiSignals.emit(SIGNAL_STUDENT_LOG_INVALIDATE)
			uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)
		}

		return response
	}

	return {
		getFocusContext,
		submitStudentLogFollowUp,
		reviewStudentLogOutcome,
	}
}
