// ui-spa/src/lib/services/studentLog/studentLogService.ts

import { createResource } from 'frappe-ui'
import { uiSignals, SIGNAL_STUDENT_LOG_INVALIDATE, SIGNAL_FOCUS_INVALIDATE } from '@/lib/uiSignals'

import type {
	Request as GetFormOptionsRequest,
	Response as GetFormOptionsResponse,
} from '@/types/contracts/student_log/get_form_options'

import type {
	Request as SearchFollowUpUsersRequest,
	Response as SearchFollowUpUsersResponse,
} from '@/types/contracts/student_log/search_follow_up_users'

import type {
	Request as SearchStudentsRequest,
	Response as SearchStudentsResponse,
} from '@/types/contracts/student_log/search_students'

import type {
	Request as SubmitStudentLogRequest,
	Response as SubmitStudentLogResponse,
} from '@/types/contracts/student_log/submit_student_log'

/**
 * Transport normalization (A+)
 * ------------------------------------------------------------
 * - Accept unknown at the boundary
 * - Normalize ONCE
 * - Return ONLY the contract type downstream
 *
 * This is defensive, not a contract.
 * The rest of the app must never rely on these envelopes.
 */
function normalize<T>(input: unknown): T {
	const root =
		typeof input === 'object' && input !== null && 'data' in (input as any)
			? (input as any).data
			: input

	if (root && typeof root === 'object' && 'message' in (root as any)) {
		return (root as any).message as T
	}

	return root as T
}

export function createStudentLogService() {
	/* ------------------------------------------------------------------
	 * Resources
	 * ------------------------------------------------------------------ */

	const searchStudentsResource = createResource<SearchStudentsResponse>({
		url: 'ifitwala_ed.api.student_log.search_students',
		method: 'POST',
		auto: false,
		transform: (res: unknown) => normalize<SearchStudentsResponse>(res),
	})

	const searchFollowUpUsersResource = createResource<SearchFollowUpUsersResponse>({
		url: 'ifitwala_ed.api.student_log.search_follow_up_users',
		method: 'POST',
		auto: false,
		transform: (res: unknown) => normalize<SearchFollowUpUsersResponse>(res),
	})

	const getFormOptionsResource = createResource<GetFormOptionsResponse>({
		url: 'ifitwala_ed.api.student_log.get_form_options',
		method: 'POST',
		auto: false,
		transform: (res: unknown) => normalize<GetFormOptionsResponse>(res),
	})

	const submitStudentLogResource = createResource<SubmitStudentLogResponse>({
		url: 'ifitwala_ed.api.student_log.submit_student_log',
		method: 'POST',
		auto: false,
		transform: (res: unknown) => normalize<SubmitStudentLogResponse>(res),
	})

	/* ------------------------------------------------------------------
	 * Public API (A+)
	 * ------------------------------------------------------------------ */

	async function searchStudents(payload: SearchStudentsRequest) {
		return searchStudentsResource.submit(payload)
	}

	async function searchFollowUpUsers(payload: SearchFollowUpUsersRequest) {
		return searchFollowUpUsersResource.submit(payload)
	}

	async function getFormOptions(payload: GetFormOptionsRequest) {
		return getFormOptionsResource.submit(payload)
	}

	async function submitStudentLog(payload: SubmitStudentLogRequest) {
		const result = await submitStudentLogResource.submit(payload)

		// A+ invalidation responsibility lives in the service
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
