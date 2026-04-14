import type { ChildRef } from '@/types/contracts/guardian/get_guardian_home_snapshot'
import type { OrgCommunicationListItem } from '@/types/orgCommunication'

export type GuardianCommunicationSource =
	| 'course'
	| 'activity'
	| 'school'
	| 'pastoral'
	| 'cohort'

export type Request = {
	source?: 'all' | GuardianCommunicationSource
	student?: string | null
	start?: number | null
	page_length?: number | null
}

export type GuardianCommunicationCenterItem = {
	kind: 'org_communication'
	item_id: string
	sort_at?: string | null
	source_type: GuardianCommunicationSource
	source_label: string
	context_label?: string | null
	matched_children: ChildRef[]
	is_unread: boolean
	org_communication: OrgCommunicationListItem
}

export type Response = {
	meta: {
		generated_at: string
		source: 'all' | GuardianCommunicationSource
		student?: string | null
	}
	family: {
		children: ChildRef[]
	}
	summary: {
		total_items: number
		source_counts: Record<string, number>
		unread_items: number
	}
	items: GuardianCommunicationCenterItem[]
	total_count: number
	has_more: boolean
	start: number
	page_length: number
}
