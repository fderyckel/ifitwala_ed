import type { RouteTarget } from '@/types/contracts/student_hub/get_student_hub_home'
import type { OrgCommunicationListItem } from '@/types/orgCommunication'

export type StudentCommunicationSource =
	| 'course'
	| 'activity'
	| 'school'
	| 'pastoral'
	| 'cohort'

export type StudentSchoolEventFeedItem = {
	name: string
	subject: string
	school?: string | null
	location?: string | null
	event_type?: string | null
	event_category?: string | null
	description?: string | null
	snippet?: string | null
	starts_on?: string | null
	ends_on?: string | null
	all_day?: 0 | 1
}

export type StudentOrgCommunicationCenterItem = {
	kind: 'org_communication'
	item_id: string
	sort_at?: string | null
	source_type: StudentCommunicationSource
	source_label: string
	context_label?: string | null
	href?: RouteTarget | null
	href_label?: string | null
	org_communication: OrgCommunicationListItem
}

export type StudentSchoolEventCenterItem = {
	kind: 'school_event'
	item_id: string
	sort_at?: string | null
	source_type: 'school'
	source_label: string
	context_label?: string | null
	href?: RouteTarget | null
	href_label?: string | null
	school_event: StudentSchoolEventFeedItem
}

export type StudentCommunicationCenterItem =
	| StudentOrgCommunicationCenterItem
	| StudentSchoolEventCenterItem
