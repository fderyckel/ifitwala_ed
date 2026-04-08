import type {
	StaffPlanningClassReflection,
	StaffPlanningMaterial,
	StaffPlanningReflection,
	StaffPlanningStandard,
} from '@/types/contracts/staff_teaching/get_staff_class_planning_surface'

export type Request = {
	course_plan: string
	unit_plan?: string
	quiz_question_bank?: string
}

export type StaffCoursePlanQuizQuestionOption = {
	option_text?: string | null
	is_correct?: number
}

export type StaffCoursePlanQuizQuestion = {
	quiz_question?: string | null
	title: string
	question_type: string
	is_published?: number
	prompt?: string | null
	accepted_answers?: string | null
	explanation?: string | null
	options: StaffCoursePlanQuizQuestionOption[]
}

export type StaffCoursePlanQuizQuestionBankSummary = {
	quiz_question_bank: string
	bank_title: string
	course?: string | null
	is_published?: number
	question_count?: number
	published_question_count?: number
}

export type StaffCoursePlanQuizQuestionBank = {
	quiz_question_bank: string
	record_modified?: string | null
	bank_title: string
	course?: string | null
	is_published?: number
	description?: string | null
	questions: StaffCoursePlanQuizQuestion[]
}

export type StaffCoursePlanAcademicYearOption = {
	value: string
	label: string
	school?: string | null
	year_start_date?: string | null
	year_end_date?: string | null
}

export type StaffCoursePlanProgramOption = {
	value: string
	label: string
	parent_program?: string | null
	is_group?: number
	archived?: number
}

export type StaffCoursePlanUnit = {
	unit_plan: string
	record_modified?: string | null
	title: string
	unit_order?: number | null
	program?: string | null
	unit_code?: string | null
	unit_status?: string | null
	version?: string | null
	duration?: string | null
	estimated_duration?: string | null
	is_published?: number
	overview?: string | null
	essential_understanding?: string | null
	misconceptions?: string | null
	content?: string | null
	skills?: string | null
	concepts?: string | null
	standards: StaffPlanningStandard[]
	shared_reflections?: StaffPlanningReflection[]
	class_reflections?: StaffPlanningClassReflection[]
	shared_resources: StaffPlanningMaterial[]
}

export type Response = {
	meta: {
		generated_at: string
		course_plan: string
	}
	course_plan: {
		course_plan: string
		record_modified?: string | null
		title: string
		course: string
		course_name?: string | null
		course_group?: string | null
		school?: string | null
		academic_year?: string | null
		cycle_label?: string | null
		plan_status?: string | null
		summary?: string | null
		can_manage_resources: number
	}
	resolved: {
		unit_plan?: string | null
		quiz_question_bank?: string | null
	}
	resources: {
		course_plan_resources: StaffPlanningMaterial[]
	}
	field_options: {
		academic_years: StaffCoursePlanAcademicYearOption[]
		programs: StaffCoursePlanProgramOption[]
	}
	curriculum: {
		units: StaffCoursePlanUnit[]
		unit_count: number
	}
	assessment: {
		quiz_question_banks: StaffCoursePlanQuizQuestionBankSummary[]
		selected_quiz_question_bank?: StaffCoursePlanQuizQuestionBank | null
	}
}
