import type { StudentCommunicationCenterItem } from '@/types/studentCommunication'

export type Request = {
	source?: 'all' | 'course' | 'activity' | 'school' | 'pastoral' | 'cohort'
	course_id?: string | null
	student_group?: string | null
	item?: string | null
	start?: number | null
	page_length?: number | null
}

export type Response = {
	meta: {
		generated_at: string
		source: 'all' | 'course' | 'activity' | 'school' | 'pastoral' | 'cohort'
		course_id?: string | null
		student_group?: string | null
		item?: string | null
	}
	summary: {
		total_items: number
		source_counts: Record<string, number>
	}
	items: StudentCommunicationCenterItem[]
	total_count: number
	has_more: boolean
	start: number
	page_length: number
}
