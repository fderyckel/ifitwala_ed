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
import type {
	Request as MarkInquiryContactedRequest,
	Response as MarkInquiryContactedResponse,
} from '@/types/contracts/focus/mark_inquiry_contacted'
import type {
	Request as SubmitApplicantReviewAssignmentRequest,
	Response as SubmitApplicantReviewAssignmentResponse,
} from '@/types/contracts/focus/submit_applicant_review_assignment'
import type {
	Request as ClaimApplicantReviewAssignmentRequest,
	Response as ClaimApplicantReviewAssignmentResponse,
} from '@/types/contracts/focus/claim_applicant_review_assignment'
import type {
	Request as ReassignApplicantReviewAssignmentRequest,
	Response as ReassignApplicantReviewAssignmentResponse,
} from '@/types/contracts/focus/reassign_applicant_review_assignment'
import type {
	Request as AcknowledgeStaffPolicyRequest,
	Response as AcknowledgeStaffPolicyResponse,
} from '@/types/contracts/focus/acknowledge_staff_policy'

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

	const markInquiryContactedResource = createResource<MarkInquiryContactedResponse>({
		url: 'ifitwala_ed.api.focus.mark_inquiry_contacted',
		method: 'POST',
		auto: false,
	})

	const submitApplicantReviewAssignmentResource =
		createResource<SubmitApplicantReviewAssignmentResponse>({
			url: 'ifitwala_ed.api.focus.submit_applicant_review_assignment',
			method: 'POST',
			auto: false,
		})

	const claimApplicantReviewAssignmentResource =
		createResource<ClaimApplicantReviewAssignmentResponse>({
			url: 'ifitwala_ed.api.focus.claim_applicant_review_assignment',
			method: 'POST',
			auto: false,
		})

	const reassignApplicantReviewAssignmentResource =
		createResource<ReassignApplicantReviewAssignmentResponse>({
			url: 'ifitwala_ed.api.focus.reassign_applicant_review_assignment',
			method: 'POST',
			auto: false,
		})

	const acknowledgeStaffPolicyResource = createResource<AcknowledgeStaffPolicyResponse>({
		url: 'ifitwala_ed.api.focus.acknowledge_staff_policy',
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
		if (response.status === 'created') {
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
		if (response.status === 'processed') {
			uiSignals.emit(SIGNAL_STUDENT_LOG_INVALIDATE)
			uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)
		}

		return response
	}

	async function markInquiryContacted(
		payload: MarkInquiryContactedRequest
	): Promise<MarkInquiryContactedResponse> {
		const response = await markInquiryContactedResource.submit(payload)

		if (response.status === 'processed') {
			uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)
		}

		return response
	}

	async function submitApplicantReviewAssignment(
		payload: SubmitApplicantReviewAssignmentRequest
	): Promise<SubmitApplicantReviewAssignmentResponse> {
		const response = await submitApplicantReviewAssignmentResource.submit(payload)

		if (response.status === 'processed' || response.status === 'already_processed') {
			uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)
		}

		return response
	}

	async function claimApplicantReviewAssignment(
		payload: ClaimApplicantReviewAssignmentRequest
	): Promise<ClaimApplicantReviewAssignmentResponse> {
		const response = await claimApplicantReviewAssignmentResource.submit(payload)

		if (response.status === 'processed' || response.status === 'already_processed') {
			uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)
		}

		return response
	}

	async function reassignApplicantReviewAssignment(
		payload: ReassignApplicantReviewAssignmentRequest
	): Promise<ReassignApplicantReviewAssignmentResponse> {
		const response = await reassignApplicantReviewAssignmentResource.submit(payload)

		if (response.status === 'processed' || response.status === 'already_processed') {
			uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)
		}

		return response
	}

	async function acknowledgeStaffPolicy(
		payload: AcknowledgeStaffPolicyRequest
	): Promise<AcknowledgeStaffPolicyResponse> {
		const response = await acknowledgeStaffPolicyResource.submit(payload)

		if (response.status === 'processed' || response.status === 'already_processed') {
			uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)
		}

		return response
	}

	return {
		getFocusContext,
		submitStudentLogFollowUp,
		reviewStudentLogOutcome,
		markInquiryContacted,
		submitApplicantReviewAssignment,
		claimApplicantReviewAssignment,
		reassignApplicantReviewAssignment,
		acknowledgeStaffPolicy,
	}
}
