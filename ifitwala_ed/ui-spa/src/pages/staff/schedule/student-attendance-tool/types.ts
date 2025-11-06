export type BlockKey = number

export interface AttendanceCode {
	name: string
	attendance_code: string
	attendance_code_name: string
	display_order?: number
	color?: string | null
}

export interface StudentRosterEntry {
	student: string
	student_name: string
	preferred_name?: string | null
	student_image?: string | null
	birth_date?: string | null
	medical_info?: string | null
	blocks: BlockKey[]
	attendance: Record<BlockKey, string>
	remarks: Record<BlockKey, string>
}

export interface RosterResponse {
	students: StudentRosterEntry[]
	blocks: BlockKey[]
	group_info?: {
		name?: string | null
		program?: string | null
		course?: string | null
		cohort?: string | null
	}
}
