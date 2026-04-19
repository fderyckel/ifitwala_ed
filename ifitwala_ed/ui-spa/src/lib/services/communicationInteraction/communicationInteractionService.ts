// ui-spa/src/lib/services/communicationInteraction/communicationInteractionService.ts

/**
 * Interaction workflow
 * --------------------------------------------------
 * Uses: communicationInteractionService
 * Semantics:
 * - reactToOrgCommunication → emits SIGNAL_ORG_COMMUNICATION_INVALIDATE
 * - postOrgCommunicationComment → emits SIGNAL_ORG_COMMUNICATION_INVALIDATE
 * - markOrgCommunicationRead → emits SIGNAL_ORG_COMMUNICATION_INVALIDATE
 *
 * Page responsibility:
 * - call semantic method
 * - re-fetch archive data on signal
 */

import { createResource } from 'frappe-ui'

import { uiSignals, SIGNAL_ORG_COMMUNICATION_INVALIDATE } from '@/lib/uiSignals'

import type {
  Request as GetOrgCommInteractionSummaryRequest,
  Response as GetOrgCommInteractionSummaryResponse,
} from '@/types/contracts/communication_interaction/get_org_comm_interaction_summary'

import type {
  Request as GetCommunicationThreadRequest,
  Response as GetCommunicationThreadResponse,
} from '@/types/contracts/communication_interaction/get_communication_thread'

import type {
  Request as ReactToOrgCommunicationRequest,
  Response as ReactToOrgCommunicationResponse,
} from '@/types/contracts/communication_interaction/react_to_org_communication'

import type {
  Request as PostOrgCommunicationCommentRequest,
  Response as PostOrgCommunicationCommentResponse,
} from '@/types/contracts/communication_interaction/post_org_communication_comment'
import type {
  Request as MarkOrgCommunicationReadRequest,
  Response as MarkOrgCommunicationReadResponse,
} from '@/types/contracts/communication_interaction/mark_org_communication_read'

import type { ReactionCode } from '@/types/interactions'
import type { OrgSurface } from '@/types/morning_brief'

/**
 * Communication Interaction Service (A+ — LOCKED)
 * ------------------------------------------------------------
 * Rules:
 * - Backend contracts are authoritative
 * - No transport normalization
 * - No envelope handling
 * - Services emit uiSignals ONLY after confirmed semantic success
 */

const DEFAULT_SURFACE: OrgSurface = 'Portal Feed'

export function createCommunicationInteractionService() {
  const interactionSummaryResource = createResource<GetOrgCommInteractionSummaryResponse>({
    url: 'ifitwala_ed.api.org_communication_interactions.get_org_communication_interaction_summary',
    method: 'POST',
    auto: false,
  })

  const communicationThreadResource = createResource<GetCommunicationThreadResponse>({
    url: 'ifitwala_ed.api.org_communication_interactions.get_org_communication_thread',
    method: 'POST',
    auto: false,
  })

  const reactResource = createResource<ReactToOrgCommunicationResponse>({
    url: 'ifitwala_ed.api.org_communication_interactions.react_to_org_communication',
    method: 'POST',
    auto: false,
  })

  const postCommentResource = createResource<PostOrgCommunicationCommentResponse>({
    url: 'ifitwala_ed.api.org_communication_interactions.post_org_communication_comment',
    method: 'POST',
    auto: false,
  })

  const markReadResource = createResource<MarkOrgCommunicationReadResponse>({
    url: 'ifitwala_ed.api.org_communication_interactions.mark_org_communication_read',
    method: 'POST',
    auto: false,
  })

  async function getOrgCommInteractionSummary(
    payload: GetOrgCommInteractionSummaryRequest
  ): Promise<GetOrgCommInteractionSummaryResponse> {
    return interactionSummaryResource.submit(payload)
  }

  async function getCommunicationThread(
    payload: GetCommunicationThreadRequest
  ): Promise<GetCommunicationThreadResponse> {
    return communicationThreadResource.submit(payload)
  }

  /**
   * Semantic mutation: react to a communication.
   * Pages should not craft reaction intents manually.
   */
  async function reactToOrgCommunication(payload: {
    org_communication: string
    reaction_code: ReactionCode
    surface?: OrgSurface | null
  }): Promise<ReactToOrgCommunicationResponse> {
    const request: ReactToOrgCommunicationRequest = {
      org_communication: payload.org_communication,
      reaction_code: payload.reaction_code,
      surface: payload.surface ?? DEFAULT_SURFACE,
    }
    const response = await reactResource.submit(request)
    if (response?.name) {
      uiSignals.emit(SIGNAL_ORG_COMMUNICATION_INVALIDATE, {
        names: [payload.org_communication],
      })
    }
    return response
  }

  /**
   * Semantic mutation: post a comment.
   * Pages should not craft generic interaction payloads.
   */
  async function postOrgCommunicationComment(payload: {
    org_communication: string
    note: string
    surface?: OrgSurface | null
  }): Promise<PostOrgCommunicationCommentResponse> {
    const request: PostOrgCommunicationCommentRequest = {
      org_communication: payload.org_communication,
      note: payload.note,
      surface: payload.surface ?? DEFAULT_SURFACE,
    }
    const response = await postCommentResource.submit(request)
    if (response?.name) {
      uiSignals.emit(SIGNAL_ORG_COMMUNICATION_INVALIDATE, {
        names: [payload.org_communication],
      })
    }
    return response
  }

  async function markOrgCommunicationRead(
    payload: MarkOrgCommunicationReadRequest
  ): Promise<MarkOrgCommunicationReadResponse> {
    const response = await markReadResource.submit(payload)
    if (response?.ok || response?.read_at) {
      uiSignals.emit(SIGNAL_ORG_COMMUNICATION_INVALIDATE, {
        names: [payload.org_communication],
      })
    }
    return response
  }

  return {
    getOrgCommInteractionSummary,
    getCommunicationThread,

    // semantic mutations (preferred)
    reactToOrgCommunication,
    postOrgCommunicationComment,
    markOrgCommunicationRead,
  }
}
