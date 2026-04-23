export type PermissionFlags = {
	can_view_tasks: boolean;
	can_view_task_marks: boolean;
	can_view_logs: boolean;
	can_view_referrals: boolean;
	can_view_nurse_details: boolean;
	can_view_attendance_details: boolean;
};

export type StudentGroup = {
	name: string;
	abbreviation?: string;
	group_based_on?: string;
	course?: string | null;
	attendance_scope?: string | null;
};

export type WellbeingTimelineItem = {
	type: 'student_log' | 'referral' | 'nurse_visit';
	doctype: string;
	name: string;
	date: string;
	academic_year?: string | null;
	title: string;
	summary?: string | null;
	status?: string | null;
	severity?: string | null;
	is_sensitive?: boolean;
};

export type WellbeingHealthNote = {
	doctype: string;
	name: string;
	title: string;
	summary?: string | null;
	updated_on?: string | null;
	is_sensitive?: boolean;
};

export type ViewMode = 'staff' | 'admin' | 'counselor' | 'attendance' | 'student' | 'guardian';

export type Snapshot = {
	meta: {
		student: string;
		student_name: string;
		school: string;
		program: string;
		current_academic_year: string;
		view_mode: ViewMode;
		permissions: PermissionFlags;
	};
	identity: {
		student: string;
		full_name: string;
		photo?: string | null;
		cohort?: string | null;
		gender?: string | null;
		age?: number | null;
		date_of_birth?: string | null;
		school?: { name: string; label?: string };
		program_enrollment?: {
			name: string;
			program: string;
			program_offering?: string;
			academic_year?: string;
			enrollment_date?: string | null;
			archived?: boolean;
		};
		student_groups: StudentGroup[];
	};
	kpis: {
		attendance: {
			present_percentage: number;
			total_days: number;
			present_days: number;
			excused_absences: number;
			unexcused_absences: number;
			late_count: number;
		};
		tasks: {
			completion_rate: number;
			total_tasks: number;
			completed_tasks: number;
			overdue_tasks: number;
			missed_tasks: number;
		};
		academic: {
			latest_overall_label: string | null;
			latest_overall_value: number | null;
			trend: string | null;
		};
		support: {
			student_logs_total: number;
			student_logs_open_followups: number;
			active_referrals: number;
			nurse_visits_this_term: number;
		};
	};
	learning: {
		current_courses: {
			course: string;
			course_name: string;
			student_group?: string | null;
			student_group_abbreviation?: string | null;
			instructors?: { name: string; full_name: string }[];
			status?: string;
			completion_rate?: number | null;
			academic_summary?: {
				latest_grade_label?: string | null;
				latest_grade_value?: number | null;
			};
		}[];
		task_progress: {
			status_distribution: {
				status: string;
				count: number;
				year_scope?: string;
				course?: string | null;
			}[];
			by_course_completion: {
				course: string;
				course_name: string;
				completion_rate: number;
				total_tasks?: number;
				completed_tasks?: number;
				missed_tasks?: number;
				academic_year?: string;
			}[];
		};
		recent_tasks: {
			task: string;
			title: string;
			course: string;
			course_name: string;
			student_group?: string | null;
			delivery_type?: string | null;
			due_date?: string | null;
			status?: string | null;
			complete?: boolean;
			mark_awarded?: number | null;
			out_of?: number | null;
			visible_to_student?: boolean;
			visible_to_guardian?: boolean;
			is_overdue?: boolean;
			is_missed?: boolean;
			last_updated_on?: string | null;
		}[];
	};
	attendance: {
		summary: {
			present_percentage: number;
			total_days: number;
			present_days: number;
			excused_absences: number;
			unexcused_absences: number;
			late_count: number;
			most_impacted_course?: {
				course: string;
				course_name: string;
				absent_percentage: number;
			} | null;
		};
		view_mode: 'all_day' | 'by_course';
		all_day_heatmap: {
			date: string;
			attendance_code: string;
			attendance_code_name?: string;
			count_as_present?: boolean;
			is_late?: boolean;
			is_excused?: boolean;
			color?: string;
			academic_year?: string;
		}[];
		by_course_heatmap: {
			course: string;
			course_name: string;
			week_label: string;
			present_sessions?: number;
			absent_sessions?: number;
			unexcused_sessions?: number;
			late_sessions?: number;
			academic_year?: string;
		}[];
		by_course_breakdown: {
			course: string;
			course_name: string;
			present_sessions: number;
			excused_absent_sessions: number;
			unexcused_absent_sessions: number;
			late_sessions: number;
			academic_year?: string;
		}[];
	};
	wellbeing: {
		timeline: WellbeingTimelineItem[];
		health_note?: WellbeingHealthNote | null;
		metrics: {
			student_logs?: { total?: number; open_followups?: number; recent_30_days?: number };
			referrals?: { total?: number; active?: number };
			nurse_visits?: { total?: number; this_term?: number; last_12_months?: number };
			time_series?: {
				period: string;
				student_logs?: number;
				referrals?: number;
				nurse_visits?: number;
			}[];
		};
	};
	history: {
		year_options: {
			key: string;
			label: string;
			academic_year?: string;
			academic_years?: string[];
		}[];
		selected_year_scope?: string;
		academic_trend: {
			academic_year: string;
			label: string;
			overall_grade_label?: string | null;
			overall_grade_value?: number | null;
			task_completion_rate?: number | null;
		}[];
		attendance_trend: {
			academic_year: string;
			label: string;
			present_percentage?: number | null;
			unexcused_absences?: number | null;
		}[];
		reflection_flags: {
			id: string;
			category: string;
			severity: 'positive' | 'neutral' | 'concern';
			message_staff?: string;
			message_student?: string;
		}[];
	};
};

export type AttendanceView = 'all_day' | 'by_course';
export type AttendanceScope = 'current' | 'last' | 'all';
export type AttendanceKpiSource = 'all_day' | 'by_course';
export type TaskYearScope = 'current' | 'previous' | 'all';
export type WellbeingScope = 'current' | 'last' | 'all';
export type WellbeingFilter = 'all' | 'student_log' | 'referral' | 'nurse_visit';
export type HistoryScope = 'current' | 'previous' | 'two_years' | 'all';

export type AttendanceSummaryForScope = {
	present_percentage: number;
	total_entries: number;
	present: number;
	excused: number;
	unexcused: number;
	late: number;
};

export type KpiTile = {
	label: string;
	value: string;
	sub: string;
	meta?: string;
	clickable?: boolean;
	onClick?: () => void;
	sourceToggle?: {
		active: AttendanceKpiSource;
		options: { id: AttendanceKpiSource; label: string }[];
	};
};

export type StudentSuggestion = {
	id: string;
	name: string;
};

export type SnapshotYearOption = Snapshot['history']['year_options'][number];
