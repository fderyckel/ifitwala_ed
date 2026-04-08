// ui-spa/src/types/contracts/org_communication_archive/get_org_communication_item.ts

import type { AudienceSummary, CommunicationType, Priority } from '@/types/orgCommunication'
import type { OrgCommunicationAttachmentRow } from '@/types/contracts/org_communication_attachments/shared'

export type Request = {
  name: string
}

export type Response = {
  name: string
  title: string
  message_html: string | null
  communication_type: CommunicationType
  priority: Priority
  publish_from: string | null
  audience_label?: string | null
  audience_summary?: AudienceSummary
  attachments?: OrgCommunicationAttachmentRow[]
}
