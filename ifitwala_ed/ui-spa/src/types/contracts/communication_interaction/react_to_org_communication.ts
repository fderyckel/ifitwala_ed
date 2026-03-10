// ui-spa/src/types/contracts/communication_interaction/react_to_org_communication.ts

import type { ReactionCode, InteractionIntentType, InteractionVisibility } from '@/types/interactions'
import type { OrgSurface } from '@/types/morning_brief'

export type Request = {
	org_communication: string
	reaction_code: ReactionCode
	surface?: OrgSurface | null
}

export type Response = {
	name: string
	org_communication: string
	intent_type?: InteractionIntentType | null
	reaction_code?: ReactionCode | null
	note?: string | null
	visibility?: InteractionVisibility | null
}
