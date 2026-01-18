// ui-spa/src/types/contracts/org_communication_archive/get_org_communication_feed.ts

import type { ArchiveFilters, OrgCommunicationListItem } from '@/types/orgCommunication'

export type Request = {
  filters: ArchiveFilters
  start?: number | null
  page_length?: number | null
}

export type Response = {
  items: OrgCommunicationListItem[]
  total_count: number
  has_more: boolean
  start: number
  page_length: number
  limit_start?: number
  limit_page_length?: number
}
