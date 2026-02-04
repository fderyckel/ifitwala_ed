// ui-spa/src/types/contracts/communication_interaction/upsert_communication_interaction.ts

import type { InteractionIntentType, InteractionVisibility, ReactionCode } from '@/types/interactions'
import type { OrgSurface } from '@/types/morning_brief'

export type Request = {
  org_communication: string
  intent_type?: InteractionIntentType | null
  reaction_code?: ReactionCode | null
  note?: string | null
  surface?: OrgSurface | null
  student_group?: string | null
  program?: string | null
  school?: string | null
}

export type Response = {
  name: string
  org_communication: string
  intent_type?: InteractionIntentType | null
  reaction_code?: ReactionCode | null
  note?: string | null
  visibility?: InteractionVisibility | null
}
