// ui-spa/src/types/contracts/activity_booking/get_activity_communications.ts

import type { OrgCommunicationListItem } from '@/types/orgCommunication'

export type Request = {
	activity_program_offering?: string | null
	activity_student_group?: string | null
	start?: number | null
	page_length?: number | null
}

export type Response = {
	items: OrgCommunicationListItem[]
	total_count: number
	has_more: boolean
	start: number
	page_length: number
}
