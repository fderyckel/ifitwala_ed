export type Priority = 'Low' | 'Normal' | 'High' | 'Critical'
export type Status = 'Draft' | 'Scheduled' | 'Published' | 'Archived'
export type PortalSurface = 'Desk' | 'Morning Brief' | 'Portal Feed' | 'Everywhere'

export const PRIORITY_OPTIONS = ['All', 'Low', 'Normal', 'High', 'Critical'] as const
export type PriorityFilter = (typeof PRIORITY_OPTIONS)[number]

export const STATUS_OPTIONS = ['PublishedOrArchived', 'Published', 'Draft', 'Scheduled', 'All'] as const
export type StatusFilter = (typeof STATUS_OPTIONS)[number]

export const SURFACE_OPTIONS = ['All', 'Desk', 'Morning Brief', 'Portal Feed', 'Everywhere'] as const
export type SurfaceFilter = (typeof SURFACE_OPTIONS)[number]

export interface OrgCommunicationListItem {
  name: string
  title: string
  communication_type: string
  status: Status
  priority: Priority
  portal_surface: PortalSurface
  school: string | null
  organization: string | null
  publish_from: string | null
  publish_to: string | null
  brief_start_date: string | null
  brief_end_date: string | null
  interaction_mode: 'None' | 'Staff Comments' | 'Structured Feedback' | 'Student Q&A'
  allow_private_notes: 0 | 1 | boolean
  allow_public_thread: 0 | 1 | boolean
  snippet: string
  audience_label?: string
  has_active_thread?: boolean
}

export interface InteractionSummarySelf {
  intent_type?: string
  name: string
  user: string
  reaction_code?: string
  note?: string
  visibility?: string
}

export interface InteractionSummary {
  counts: Record<string, number>
  self: InteractionSummarySelf | null
}

export interface ArchiveFilters {
  search: string
  status: StatusFilter
  priority: PriorityFilter
  portal_surface: SurfaceFilter
  communication_type: string | 'All'
  date_range: '7d' | '30d' | '90d' | 'year' | 'all'
  only_with_interactions: boolean
  team?: string | 'All'
  student_group?: string | 'All'
  school?: string | 'All'
  organization?: string | 'All'
}

export function canShowPublicInteractions(item: OrgCommunicationListItem | null | undefined): boolean {
	if (!item) return false

	const mode = (item.interaction_mode || 'None').trim()

	// Only these modes allow comments + emoji
	const interactiveModes = [
		'Staff Comments',
		'Structured Feedback',
		'Student Q&A'
	]

	if (!interactiveModes.includes(mode)) {
		return false
	}

	// Frappe booleans can be 0/1, '0'/'1', true/false
	const raw = item.allow_public_thread as unknown
	const publicEnabled =
		raw === 1 ||
		raw === true ||
		raw === '1'

	return publicEnabled
}
