// ifitwala_ed/ui-spa/src/types/orgCommunication.ts

export type Priority = 'Low' | 'Normal' | 'High' | 'Critical'
export type Status = 'Draft' | 'Scheduled' | 'Published' | 'Archived'
export type PortalSurface = 'Desk' | 'Morning Brief' | 'Portal Feed' | 'Everywhere'

export const COMMUNICATION_TYPES = [
	'Logistics',
	'Reminder',
	'Information',
	'Policy Procedure',
	'Celebration',
	'Call to Action',
	'Event Announcement',
	'Class Announcement',
	'Urgent',
	'Alert',
] as const

export type CommunicationType = (typeof COMMUNICATION_TYPES)[number]

export const AUDIENCE_TARGET_MODES = [
	'School Scope',
	'Team',
	'Student Group',
] as const

export type AudienceTargetMode = (typeof AUDIENCE_TARGET_MODES)[number]

export const PRIORITY_OPTIONS = ['All', 'Low', 'Normal', 'High', 'Critical'] as const
export type PriorityFilter = (typeof PRIORITY_OPTIONS)[number]

export const STATUS_OPTIONS = ['PublishedOrArchived', 'Published', 'Draft', 'Scheduled', 'All'] as const
export type StatusFilter = (typeof STATUS_OPTIONS)[number]

export const SURFACE_OPTIONS = ['All', 'Desk', 'Morning Brief', 'Portal Feed', 'Everywhere'] as const
export type SurfaceFilter = (typeof SURFACE_OPTIONS)[number]

import type { InteractionMode } from '@/types/interactions'

export interface OrgCommunicationListItem {
  name: string
  title: string
  communication_type: CommunicationType
  status: Status
  priority: Priority
  portal_surface: PortalSurface
  school: string | null
  organization: string | null
  publish_from: string | null
  publish_to: string | null
  brief_start_date: string | null
  brief_end_date: string | null
  interaction_mode: InteractionMode
  allow_private_notes: 0 | 1 | boolean
  allow_public_thread: 0 | 1 | boolean
  snippet: string
  audience_label?: string
  has_active_thread?: boolean
}

export interface ArchiveFilters {
	search_text: string | null
	status: StatusFilter | null
	priority: PriorityFilter | null
	portal_surface: SurfaceFilter | null
	communication_type: CommunicationType | 'All' | null
	date_range: '7d' | '30d' | '90d' | 'year' | 'all' | null
	only_with_interactions: boolean

	// Always present; null means "All"
	team: string | null
	student_group: string | null
	school: string | null
	organization: string | null
}

export interface OrgCommunicationAudienceRow {
	target_mode: AudienceTargetMode
	school?: string | null
	team?: string | null
	student_group?: string | null
	include_descendants?: 0 | 1 | boolean
	to_staff?: 0 | 1 | boolean
	to_students?: 0 | 1 | boolean
	to_guardians?: 0 | 1 | boolean
	to_community?: 0 | 1 | boolean
	note?: string | null
}

export interface OrgCommunicationCreateDoc {
	doctype: 'Org Communication'
	title: string
	communication_type: CommunicationType
	status: Status
	priority: Priority
	portal_surface: PortalSurface
	publish_from?: string | null
	publish_to?: string | null
	brief_start_date?: string | null
	brief_end_date?: string | null
	message?: string
	school: string
	organization?: string | null
	audiences: OrgCommunicationAudienceRow[]
}
