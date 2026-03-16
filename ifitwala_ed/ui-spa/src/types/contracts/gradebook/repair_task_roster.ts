// ui-spa/src/types/contracts/gradebook/repair_task_roster.ts

export type Request = {
	task: string
}

export type Response = {
	task_delivery: string
	docstatus: 0 | 1 | 2
	was_draft: 0 | 1
	eligible_students: number
	outcomes_created: number
	outcomes_total: number
	message: string
}
