// ifitwala_ed/ui-spa/src/types/tasks.ts

export type CreateTaskDeliveryPayload = {
	task: string;
	task_delivery: string;
	outcomes_created?: number;
};

export type TaskLibraryScope = 'all' | 'mine' | 'shared';

export type ReusableTaskSummary = {
	name: string;
	title: string;
	task_type?: string | null;
	default_course: string;
	unit_plan?: string | null;
	owner?: string | null;
	is_template: 0 | 1;
	modified?: string | null;
	visibility_scope: 'mine' | 'shared';
	visibility_label: string;
};

export type TaskForDeliveryPayload = {
	name: string;
	title: string;
	instructions?: string | null;
	task_type?: string | null;
	default_course: string;
	unit_plan?: string | null;
	owner?: string | null;
	is_template: 0 | 1;
	visibility_scope: 'mine' | 'shared';
	default_delivery_mode?: 'Assign Only' | 'Collect Work' | 'Assess' | null;
	grading_defaults: {
		default_allow_feedback?: 0 | 1 | null;
		default_grading_mode?: 'None' | 'Completion' | 'Binary' | 'Points' | 'Criteria' | null;
		default_max_points?: number | string | null;
		default_grade_scale?: string | null;
	};
	quiz_defaults: {
		quiz_question_bank?: string | null;
		quiz_question_count?: number | string | null;
		quiz_time_limit_minutes?: number | string | null;
		quiz_max_attempts?: number | string | null;
		quiz_pass_percentage?: number | string | null;
	};
};

export type CreateTaskDeliveryInput = {
	title: string;
	instructions?: string;
	task_type?: string;
	is_template?: 0 | 1;
	student_group: string;
	class_teaching_plan?: string;
	class_session?: string;
	unit_plan?: string;
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
