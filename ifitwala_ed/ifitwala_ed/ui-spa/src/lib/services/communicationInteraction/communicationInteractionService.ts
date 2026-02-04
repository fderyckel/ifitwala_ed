// ui-spa/src/lib/services/communicationInteraction/communicationInteractionService.ts

/**
 * Interaction workflow
 * --------------------------------------------------
 * Uses: communicationInteractionService
 * Semantics:
 * - reactToOrgCommunication → emits SIGNAL_ORG_COMMUNICATION_INVALIDATE
 * - postOrgCommunicationComment → emits SIGNAL_ORG_COMMUNICATION_INVALIDATE
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
  Request as UpsertCommunicationInteractionRequest,
  Response as UpsertCommunicationInteractionResponse,
} from '@/types/contracts/communication_interaction/upsert_communication_interaction'

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
    url: 'ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.get_org_comm_interaction_summary',
    method: 'POST',
    auto: false,
  })

  const communicationThreadResource = createResource<GetCommunicationThreadResponse>({
    url: 'ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.get_communication_thread',
    method: 'POST',
    auto: false,
  })

  const upsertInteractionResource = createResource<UpsertCommunicationInteractionResponse>({
    url: 'ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.upsert_communication_interaction',
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
   * Low-level mutation (kept for internal reuse; app code should prefer semantic helpers below).
   * Emits invalidate only after confirmed success.
   */
  async function upsertCommunicationInteraction(
    payload: UpsertCommunicationInteractionRequest
  ): Promise<UpsertCommunicationInteractionResponse> {
    const response = await upsertInteractionResource.submit(payload)

    if (response?.name) {
      uiSignals.emit(SIGNAL_ORG_COMMUNICATION_INVALIDATE, {
        names: [payload.org_communication],
      })
    }

    return response
  }

  /**
   * Semantic mutation: react to a communication.
   * Pages should not craft upsert payloads (intent_type, etc).
   */
  async function reactToOrgCommunication(payload: {
    org_communication: string
    reaction_code: ReactionCode
    surface?: OrgSurface | null
  }): Promise<UpsertCommunicationInteractionResponse> {
    return upsertCommunicationInteraction({
      org_communication: payload.org_communication,
      reaction_code: payload.reaction_code,
      surface: payload.surface ?? DEFAULT_SURFACE,
    })
  }

  /**
   * Semantic mutation: post a comment.
   * Pages should not craft upsert payloads (intent_type, etc).
   */
  async function postOrgCommunicationComment(payload: {
    org_communication: string
    note: string
    surface?: OrgSurface | null
  }): Promise<UpsertCommunicationInteractionResponse> {
    return upsertCommunicationInteraction({
      org_communication: payload.org_communication,
      intent_type: 'Comment',
      note: payload.note,
      surface: payload.surface ?? DEFAULT_SURFACE,
    })
  }

  return {
    getOrgCommInteractionSummary,
    getCommunicationThread,

    // semantic mutations (preferred)
    reactToOrgCommunication,
    postOrgCommunicationComment,

    // low-level (avoid in pages unless truly necessary)
    upsertCommunicationInteraction,
  }
}
