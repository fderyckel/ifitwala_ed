// ui-spa/src/types/contracts/guardian/get_guardian_attendance_snapshot.ts

import type { ChildRef } from '@/types/contracts/guardian/get_guardian_home_snapshot'

export type Request = {
	student?: string
	days?: number
}

export type Response = {
	meta: {
		generated_at: string
		guardian: { name: string | null }
		filters: {
			student: string
			days: number
			start_date: string
			end_date: string
		}
	}
	family: {
		children: ChildRef[]
	}
	counts: {
		tracked_days: number
		present_days: number
		late_days: number
		absence_days: number
	}
	students: GuardianAttendanceStudent[]
}

export type GuardianAttendanceStudent = {
	student: string
	student_name: string
	summary: {
		tracked_days: number
		present_days: number
		late_days: number
		absence_days: number
	}
	days: GuardianAttendanceDay[]
}

export type GuardianAttendanceDay = {
	date: string
	state: 'present' | 'late' | 'absence'
	details: GuardianAttendanceDetail[]
}

export type GuardianAttendanceDetail = {
	attendance: string
	time?: string | null
	attendance_code: string
	attendance_code_name: string
	whole_day: boolean
	course?: string | null
	location?: string | null
	remark?: string | null
}
