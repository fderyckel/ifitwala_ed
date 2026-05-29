// ui-spa/src/types/contracts/self_enrollment/submit_self_enrollment_choices.ts

import type {
	EnrollmentIntent,
	Response as ChoiceStateResponse,
} from '@/types/contracts/self_enrollment/get_self_enrollment_choice_state'
import type { ChoiceSubmitRow } from '@/types/contracts/self_enrollment/save_self_enrollment_choices'

export type Request = {
	selection_window: string
	student?: string | null
	courses?: ChoiceSubmitRow[] | null
	enrollment_intent?: EnrollmentIntent | '' | null
}

export type Response = ChoiceStateResponse
