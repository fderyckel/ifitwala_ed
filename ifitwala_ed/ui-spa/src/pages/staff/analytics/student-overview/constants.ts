import type { Snapshot, ViewMode } from './types';

export const viewModeOptions: { id: ViewMode; label: string }[] = [
	{ id: 'staff', label: 'Staff' },
	{ id: 'student', label: 'Student' },
	{ id: 'guardian', label: 'Guardian' },
];

export const emptySnapshot: Snapshot = {
	meta: {
		student: '',
		student_name: '',
		school: '',
		program: '',
		current_academic_year: '',
		view_mode: 'staff',
		permissions: {
			can_view_tasks: true,
			can_view_task_marks: true,
			can_view_logs: true,
			can_view_referrals: true,
			can_view_nurse_details: false,
			can_view_attendance_details: true,
		},
	},
	identity: {
		student: '',
		full_name: '',
		photo: null,
			cohort: null,
			gender: null,
			age: null,
			student_age: null,
			school: undefined,
		program_enrollment: undefined,
		student_groups: [],
	},
	kpis: {
		attendance: {
			present_percentage: 0,
			total_days: 0,
			present_days: 0,
			excused_absences: 0,
			unexcused_absences: 0,
			late_count: 0,
		},
		tasks: {
			completion_rate: 0,
			total_tasks: 0,
			completed_tasks: 0,
			overdue_tasks: 0,
			missed_tasks: 0,
		},
		academic: {
			latest_overall_label: null,
			latest_overall_value: null,
			trend: null,
		},
		support: {
			student_logs_total: 0,
			student_logs_open_followups: 0,
			active_referrals: 0,
			nurse_visits_this_term: 0,
		},
	},
	learning: {
		current_courses: [],
		task_progress: {
			status_distribution: [],
			by_course_completion: [],
		},
		recent_tasks: [],
	},
	attendance: {
		summary: {
			present_percentage: 0,
			total_days: 0,
			present_days: 0,
			excused_absences: 0,
			unexcused_absences: 0,
			late_count: 0,
			most_impacted_course: null,
		},
		view_mode: 'all_day',
		all_day_heatmap: [],
		by_course_heatmap: [],
		by_course_breakdown: [],
	},
	wellbeing: {
		timeline: [],
		health_note: null,
		metrics: {},
	},
	history: {
		year_options: [],
		selected_year_scope: 'all',
		academic_trend: [],
		attendance_trend: [],
		reflection_flags: [],
	},
};
