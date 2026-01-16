// ui-spa/src/lib/services/focus/focusService.ts

import { createResource } from 'frappe-ui'
import { SIGNAL_FOCUS_INVALIDATE, SIGNAL_STUDENT_LOG_INVALIDATE, uiSignals } from '@/lib/uiSignals'
import type { Request as GetFocusContextRequest, Response as GetFocusContextResponse } from '@/types/contracts/focus/get_focus_context'
import type {
  Request as SubmitStudentLogFollowUpRequest,
  Response as SubmitStudentLogFollowUpResponse,
} from '@/types/contracts/focus/submit_student_log_follow_up'
import type {
  Request as ReviewStudentLogOutcomeRequest,
  Response as ReviewStudentLogOutcomeResponse,
} from '@/types/contracts/focus/review_student_log_outcome'

function unwrapMessage<T>(res: unknown): T {
  // frappe-ui may give: { message: T } OR T
  if (res && typeof res === 'object' && 'message' in res) {
    return (res as any).message as T
  }
  return res as T
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
    uiSignals.emit(SIGNAL_STUDENT_LOG_INVALIDATE)
    uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)
    return response
  }

  async function reviewStudentLogOutcome(payload: ReviewStudentLogOutcomeRequest) {
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
