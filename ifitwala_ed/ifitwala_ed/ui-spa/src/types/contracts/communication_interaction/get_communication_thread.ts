// ui-spa/src/types/contracts/communication_interaction/get_communication_thread.ts

import type { InteractionThreadRow } from '@/types/morning_brief'

export type Request = {
  org_communication: string
  limit_start?: number | null
  limit_page_length?: number | null
}

export type Response = InteractionThreadRow[]
