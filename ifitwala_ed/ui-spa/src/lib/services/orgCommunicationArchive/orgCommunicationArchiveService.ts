// ui-spa/src/lib/services/orgCommunicationArchive/orgCommunicationArchiveService.ts

import { createResource } from 'frappe-ui'

import type {
  Request as GetArchiveContextRequest,
  Response as GetArchiveContextResponse,
} from '@/types/contracts/org_communication_archive/get_archive_context'

import type {
  Request as GetOrgCommunicationFeedRequest,
  Response as GetOrgCommunicationFeedResponse,
} from '@/types/contracts/org_communication_archive/get_org_communication_feed'

import type {
  Request as GetOrgCommunicationItemRequest,
  Response as GetOrgCommunicationItemResponse,
} from '@/types/contracts/org_communication_archive/get_org_communication_item'

/**
 * Org Communication Archive Service (A+ — LOCKED)
 * ------------------------------------------------------------
 * Rules:
 * - Backend contracts are authoritative
 * - No transport normalization
 * - No envelope handling
 */

export function createOrgCommunicationArchiveService() {
  const archiveContextResource = createResource<GetArchiveContextResponse>({
    url: 'ifitwala_ed.api.org_communication_archive.get_archive_context',
    method: 'POST',
    auto: false,
  })

  const orgCommunicationFeedResource = createResource<GetOrgCommunicationFeedResponse>({
    url: 'ifitwala_ed.api.org_communication_archive.get_org_communication_feed',
    method: 'POST',
    auto: false,
  })

  const orgCommunicationItemResource = createResource<GetOrgCommunicationItemResponse>({
    url: 'ifitwala_ed.api.org_communication_archive.get_org_communication_item',
    method: 'POST',
    auto: false,
  })

  async function getArchiveContext(
    payload: GetArchiveContextRequest
  ): Promise<GetArchiveContextResponse> {
    return archiveContextResource.submit(payload)
  }

  async function getOrgCommunicationFeed(
    payload: GetOrgCommunicationFeedRequest
  ): Promise<GetOrgCommunicationFeedResponse> {
    return orgCommunicationFeedResource.submit(payload)
  }

  async function getOrgCommunicationItem(
    payload: GetOrgCommunicationItemRequest
  ): Promise<GetOrgCommunicationItemResponse> {
    return orgCommunicationItemResource.submit(payload)
  }

  return {
    getArchiveContext,
    getOrgCommunicationFeed,
    getOrgCommunicationItem,
  }
}
