// ui-spa/src/types/contracts/guardian/get_guardian_monitoring_snapshot.ts

import type { ChildRef } from '@/types/contracts/guardian/get_guardian_home_snapshot'

export type Request = {
	student?: string
	days?: number
	page_length?: number
	prioritize_unread?: boolean
}

export type PageRequest = Request & {
	start?: number
}

export type MarkGuardianStudentLogReadRequest = {
	log_name: string
}

export type MarkGuardianStudentLogReadResponse = {
	ok: boolean
	student_log: string
	read_at: string
}

export type MonitoringPage<T> = {
	items: T[]
	total_count: number
	has_more: boolean
	start: number
	page_length: number
}

export type Response = {
	meta: {
		generated_at: string
		guardian: { name: string | null }
		filters: {
			student: string
			days: number
		}
	}
	family: {
		children: ChildRef[]
	}
	counts: {
		visible_student_logs: number
		unread_visible_student_logs: number
		published_results: number
	}
	student_logs: MonitoringPage<MonitoringStudentLog>
	published_results: MonitoringPage<MonitoringPublishedResult>
}

export type MonitoringStudentLog = {
	student_log: string
	student: string
	student_name: string
	date: string
	time?: string | null
	summary: string
	follow_up_status: string
	is_unread: boolean
}

export type MonitoringPublishedResult = {
	task_outcome: string
	student: string
	student_name: string
	title: string
	published_on: string
	published_by: string
	score?: { value: number | string } | null
	narrative?: string
	grade_visible?: boolean
	feedback_visible?: boolean
}

export type StudentLogPageResponse = MonitoringPage<MonitoringStudentLog>
export type PublishedResultPageResponse = MonitoringPage<MonitoringPublishedResult>
