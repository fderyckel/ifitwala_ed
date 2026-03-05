// ui-spa/src/types/contracts/gradebook/fetch_group_tasks.ts

export type Request = {
	student_group: string
}

export type TaskSummary = {
	name: string
	title: string
	due_date?: string | null
	status?: string | null
	points: 0 | 1
	binary: 0 | 1
	criteria: 0 | 1
	observations: 0 | 1
	max_points?: number | null
	task_type?: string | null
	delivery_type?: string | null
}

export type Response = {
	tasks: TaskSummary[]
}
