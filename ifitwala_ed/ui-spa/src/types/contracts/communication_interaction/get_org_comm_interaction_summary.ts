// ui-spa/src/types/contracts/communication_interaction/get_org_comm_interaction_summary.ts

import type { InteractionSummaryMap } from '@/types/morning_brief'

export type Request = {
  comm_names: string[]
}

export type Response = InteractionSummaryMap
