// ui-spa/src/types/contracts/communication_interaction/post_org_communication_comment.ts

import type { InteractionIntentType, InteractionVisibility } from '@/types/interactions'
import type { OrgSurface } from '@/types/morning_brief'

export type Request = {
	org_communication: string
	note: string
	surface?: OrgSurface | null
}

export type Response = {
	name: string
	org_communication: string
	intent_type?: InteractionIntentType | null
	reaction_code?: string | null
	note?: string | null
	visibility?: InteractionVisibility | null
}
