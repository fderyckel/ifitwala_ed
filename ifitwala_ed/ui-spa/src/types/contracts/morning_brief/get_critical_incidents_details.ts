// ui-spa/src/types/contracts/morning_brief/get_critical_incidents_details.ts
// Types for ifitwala_ed.api.morning_brief.get_critical_incidents_details endpoint

export type StudentLogDetail = {
	name: string
	student_name: string
	student_image: string | null
	log_type: string
	date: string
	log: string
	date_display: string
	snippet: string
}

export type Response = StudentLogDetail[]
