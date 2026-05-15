// ui-spa/src/types/contracts/self_enrollment/save_self_enrollment_choices.ts

import type { Response as ChoiceStateResponse } from '@/types/contracts/self_enrollment/get_self_enrollment_choice_state'

export type ChoiceSubmitRow = {
	course: string
	applied_basket_group?: string | null
	choice_rank?: number | null
}

export type Request = {
	selection_window: string
	student?: string | null
	courses: ChoiceSubmitRow[]
}

export type Response = ChoiceStateResponse
