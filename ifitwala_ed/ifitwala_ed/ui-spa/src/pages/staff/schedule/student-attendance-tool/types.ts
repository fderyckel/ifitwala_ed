// ui-spa/src/pages/staff/schedule/student-attendance-tool/types.ts
// ------------------------------------------------------------
// UI View-Model Types (page-owned)
// ------------------------------------------------------------
// - These types are projections used only by StudentAttendanceTool.vue
// - They must NOT mirror backend payloads
// - They must NOT be imported by services
// ------------------------------------------------------------

export type BlockKey = number

export interface StudentRosterEntry {
	student: string
	student_name: string
	preferred_name?: string | null
	student_image?: string | null
	birth_date?: string | null
	medical_info?: string | null

	// UI-composed state
	blocks: BlockKey[]
	attendance: Record<BlockKey, string>
	remarks: Record<BlockKey, string>
}
