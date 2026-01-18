// ui-spa/src/lib/services/studentLog/studentLogService.ts

import { createResource } from 'frappe-ui'

import { uiSignals, SIGNAL_FOCUS_INVALIDATE, SIGNAL_STUDENT_LOG_INVALIDATE } from '@/lib/uiSignals'

import type {
	Request as SearchStudentsRequest,
	Response as SearchStudentsResponse,
} from '@/types/contracts/student_log/search_students'
import type {
	Request as SearchFollowUpUsersRequest,
	Response as SearchFollowUpUsersResponse,
} from '@/types/contracts/student_log/search_follow_up_users'
import type {
	Request as GetFormOptionsRequest,
	Response as GetFormOptionsResponse,
} from '@/types/contracts/student_log/get_form_options'
import type {
	Request as SubmitStudentLogRequest,
	Response as SubmitStudentLogResponse,
} from '@/types/contracts/student_log/submit_student_log'

/**
 * Student Log Service (A+ — LOCKED)
 * ------------------------------------------------------------
 * Rules:
 * - Backend contracts are authoritative
 * - No transport normalization
 * - No envelope handling
 * - No defensive branching
 * - Services emit uiSignals ONLY after confirmed successful mutations
 *
 * A+ UX feedback rule (refined):
 * - UX feedback after success is owned by Refresh Owners (page/shell)
 *   and is triggered by signal semantics.
 * - Service emits invalidate signals after success.
 * - Refresh owner receives signal, refetches, and may optionally toast “Saved”
 *   AFTER refetch success.
 * - Overlays do zero UX signaling (no toast, no signals, no refetch).
 */

export function createStudentLogService() {
	/* ------------------------------------------------------------------
	 * Resources (transport is handled globally in ui-spa/src/resources/frappe.ts)
	 * ------------------------------------------------------------------ */

	const searchStudentsResource = createResource<SearchStudentsResponse>({
		url: 'ifitwala_ed.api.student_log.search_students',
		method: 'POST',
		auto: false,
	})

	const searchFollowUpUsersResource = createResource<SearchFollowUpUsersResponse>({
		url: 'ifitwala_ed.api.student_log.search_follow_up_users',
		method: 'POST',
		auto: false,
	})

	const getFormOptionsResource = createResource<GetFormOptionsResponse>({
		url: 'ifitwala_ed.api.student_log.get_form_options',
		method: 'POST',
		auto: false,
	})

	const submitStudentLogResource = createResource<SubmitStudentLogResponse>({
		url: 'ifitwala_ed.api.student_log.submit_student_log',
		method: 'POST',
		auto: false,
	})

	/* ------------------------------------------------------------------
	 * Public API (A+)
	 * ------------------------------------------------------------------ */

	async function searchStudents(payload: SearchStudentsRequest): Promise<SearchStudentsResponse> {
		return searchStudentsResource.submit(payload)
	}

	async function searchFollowUpUsers(
		payload: SearchFollowUpUsersRequest
	): Promise<SearchFollowUpUsersResponse> {
		return searchFollowUpUsersResource.submit(payload)
	}

	async function getFormOptions(payload: GetFormOptionsRequest): Promise<GetFormOptionsResponse> {
		return getFormOptionsResource.submit(payload)
	}

	async function submitStudentLog(payload: SubmitStudentLogRequest): Promise<SubmitStudentLogResponse> {
		// Under the A+ transport contract, submit() returns domain payloads or throws.
		// Therefore, reaching the next lines implies a confirmed success.
		const result = await submitStudentLogResource.submit(payload)

		// Invalidation is the service responsibility (A+).
		// UX feedback is owned by Refresh Owners (page/shell) and is triggered by signal semantics.
		uiSignals.emit(SIGNAL_STUDENT_LOG_INVALIDATE)
		uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)

		return result
	}

	return {
		searchStudents,
		searchFollowUpUsers,
		getFormOptions,
		submitStudentLog,
	}
}
