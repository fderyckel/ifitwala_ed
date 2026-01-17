// ui-spa/src/lib/services/communicationInteraction/communicationInteractionService.ts

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

/**
 * Communication Interaction Service (A+ — LOCKED)
 * ------------------------------------------------------------
 * Rules:
 * - Backend contracts are authoritative
 * - No transport normalization
 * - No envelope handling
 * - Services emit uiSignals ONLY after confirmed semantic success
 */

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

  return {
    getOrgCommInteractionSummary,
    getCommunicationThread,
    upsertCommunicationInteraction,
  }
}
