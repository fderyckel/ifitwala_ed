// ui-spa/src/lib/services/studentLog/studentLogService.ts

import { createResource } from 'frappe-ui'
import { SIGNAL_FOCUS_INVALIDATE, SIGNAL_STUDENT_LOG_INVALIDATE, uiSignals } from '@/lib/uiSignals'
import type { Request as GetFormOptionsRequest, Response as GetFormOptionsResponse } from '@/types/contracts/student_log/get_form_options'
import type { Request as SearchFollowUpUsersRequest, Response as SearchFollowUpUsersResponse } from '@/types/contracts/student_log/search_follow_up_users'
import type { Request as SearchStudentsRequest, Response as SearchStudentsResponse } from '@/types/contracts/student_log/search_students'
import type { Request as SubmitStudentLogRequest, Response as SubmitStudentLogResponse } from '@/types/contracts/student_log/submit_student_log'

function unwrapMessage<T>(res: any): T {
  // Normalize Frappe + Axios envelopes:
  // - { message: T }
  // - { data: { message: T } }
  // - { data: T }
  const root = res?.data ?? res
  if (root && typeof root === 'object' && 'message' in root) {
    return (root as any).message as T
  }
  return root as T
}


export function createStudentLogService() {
  const searchStudentsResource = createResource<SearchStudentsResponse>({
    url: 'ifitwala_ed.api.student_log.search_students',
    method: 'POST',
    auto: false,
    transform: unwrapMessage,
  })

  const searchFollowUpUsersResource = createResource<SearchFollowUpUsersResponse>({
    url: 'ifitwala_ed.api.student_log.search_follow_up_users',
    method: 'POST',
    auto: false,
    transform: unwrapMessage,
  })

  const getFormOptionsResource = createResource<GetFormOptionsResponse>({
    url: 'ifitwala_ed.api.student_log.get_form_options',
    method: 'POST',
    auto: false,
    transform: unwrapMessage,
  })

  const submitStudentLogResource = createResource<SubmitStudentLogResponse>({
    url: 'ifitwala_ed.api.student_log.submit_student_log',
    method: 'POST',
    auto: false,
    transform: unwrapMessage,
  })

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
    const response = await submitStudentLogResource.submit(payload)
    uiSignals.emit(SIGNAL_STUDENT_LOG_INVALIDATE)
    uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)
    return response
  }

  return {
    searchStudents,
    searchFollowUpUsers,
    getFormOptions,
    submitStudentLog,
  }
}
