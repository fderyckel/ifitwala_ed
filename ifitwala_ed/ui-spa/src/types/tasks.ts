// ifitwala_ed/ui-spa/src/types/tasks.ts

export type CreateTaskDeliveryPayload = {
	task: string;
	task_delivery: string;
	outcomes_created?: number;
};

export type CreateTaskDeliveryInput = {
	title: string;
	instructions?: string;
	task_type?: string;
	student_group: string;
	class_teaching_plan?: string;
	class_session?: string;
	unit_plan?: string;
	lesson?: string;
	delivery_mode: 'Assign Only' | 'Collect Work' | 'Assess';
	available_from?: string;
	due_date?: string;
	lock_date?: string;
	allow_late_submission?: 0 | 1;
	group_submission?: 0 | 1;
	grading_mode?: 'None' | 'Completion' | 'Binary' | 'Points' | 'Criteria';
	allow_feedback?: 0 | 1;
	max_points?: number | string;
	quiz_question_bank?: string;
	quiz_question_count?: number | string;
	quiz_time_limit_minutes?: number | string;
	quiz_max_attempts?: number | string;
	quiz_pass_percentage?: number | string;
};
