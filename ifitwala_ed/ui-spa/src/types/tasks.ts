// ifitwala_ed/ui-spa/src/types/tasks.ts

export type CreateTaskDeliveryPayload = {
	task: string;
	task_delivery: string;
};

export type CreateTaskDeliveryInput = {
	title: string;
	instructions?: string;
	task_type?: string;
	student_group: string;
	delivery_mode: 'Assign Only' | 'Collect Work' | 'Assess';
	available_from?: string;
	due_date?: string;
	lock_date?: string;
	allow_late_submission?: 0 | 1;
	group_submission?: 0 | 1;
	grading_mode?: 'None' | 'Completion' | 'Binary' | 'Points';
	max_points?: number | string;
};
