import type { StudentOrgCommunicationCenterItem } from '@/types/studentCommunication'

export type Request = {
	course_id: string
	student_group?: string
	focus_communication?: string | null
	start?: number | null
	page_length?: number | null
}

export type StudentCourseCommunicationSummary = {
	total_count: number
	unread_count: number
	high_priority_count: number
	has_high_priority: 0 | 1
	latest_publish_at?: string | null
}

export type Response = {
	meta: {
		generated_at: string
		course_id: string
		student_group?: string | null
		focus_communication?: string | null
	}
	summary: StudentCourseCommunicationSummary
	items: StudentOrgCommunicationCenterItem[]
	total_count: number
	has_more: boolean
	start: number
	page_length: number
}
