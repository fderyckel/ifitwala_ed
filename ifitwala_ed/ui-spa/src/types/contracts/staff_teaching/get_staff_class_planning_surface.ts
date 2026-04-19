// ui-spa/src/types/contracts/staff_teaching/get_staff_class_planning_surface.ts

import type { AttachmentPreviewItem } from '@/types/contracts/attachments/shared'

export type Request = {
	student_group: string
	class_teaching_plan?: string
}

export type StaffPlanningActivity = {
	title: string
	activity_type?: string | null
	estimated_minutes?: number | null
	sequence_index?: number | null
	student_direction?: string | null
	teacher_prompt?: string | null
	resource_note?: string | null
}

export type StaffPlanningStandard = {
	learning_standard?: string | null
	framework_name?: string | null
	framework_version?: string | null
	subject_area?: string | null
	program?: string | null
	strand?: string | null
	substrand?: string | null
	standard_code?: string | null
	standard_description?: string | null
	coverage_level?: string | null
	alignment_strength?: string | null
	alignment_type?: string | null
	notes?: string | null
}

export type StaffPlanningMaterial = {
	material: string
	title: string
	material_type?: 'File' | 'Reference Link' | null
	modality?: string | null
	description?: string | null
	reference_url?: string | null
	thumbnail_url?: string | null
	preview_url?: string | null
	open_url?: string | null
	file_name?: string | null
	file_size?: string | null
	placement?: string | null
	origin?: string | null
	usage_role?: string | null
	placement_note?: string | null
	placement_order?: number | null
	attachment_preview?: AttachmentPreviewItem | null
}

export type StaffAssignedWork = {
	task_delivery: string
	task: string
	title: string
	task_type?: string | null
	unit_plan?: string | null
	class_session?: string | null
	delivery_mode?: string | null
	grading_mode?: string | null
	available_from?: string | null
	due_date?: string | null
	lock_date?: string | null
	materials: StaffPlanningMaterial[]
}

export type StaffPlanningReflection = {
	academic_year?: string | null
	school?: string | null
	prior_to_the_unit?: string | null
	during_the_unit?: string | null
	what_work_well?: string | null
	what_didnt_work_well?: string | null
	changes_suggestions?: string | null
}

export type StaffPlanningClassReflection = {
	class_teaching_plan: string
	student_group?: string | null
	class_label: string
	academic_year?: string | null
	prior_to_the_unit?: string | null
	during_the_unit?: string | null
	what_work_well?: string | null
	what_didnt_work_well?: string | null
	changes_suggestions?: string | null
}

export type StaffPlanningSession = {
	class_session: string
	title: string
	unit_plan: string
	session_status?: string | null
	session_date?: string | null
	sequence_index?: number | null
	learning_goal?: string | null
	teacher_note?: string | null
	activities: StaffPlanningActivity[]
	resources: StaffPlanningMaterial[]
	assigned_work: StaffAssignedWork[]
}

export type StaffPlanningUnit = {
	unit_plan: string
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
	shared_resources: StaffPlanningMaterial[]
	assigned_work: StaffAssignedWork[]
	shared_reflections?: StaffPlanningReflection[]
	class_reflections?: StaffPlanningClassReflection[]
	governed_required: number
	pacing_status?: string | null
	teacher_focus?: string | null
	pacing_note?: string | null
	prior_to_the_unit?: string | null
	during_the_unit?: string | null
	what_work_well?: string | null
	what_didnt_work_well?: string | null
	changes_suggestions?: string | null
	sessions: StaffPlanningSession[]
}

export type Response = {
	meta: {
		generated_at: string
		student_group: string
	}
	group: {
		student_group: string
		title: string
		course?: string | null
		academic_year?: string | null
	}
	course_plans: Array<{
		course_plan: string
		title: string
		academic_year?: string | null
		cycle_label?: string | null
		plan_status?: string | null
	}>
	class_teaching_plans: Array<{
		class_teaching_plan: string
		title: string
		course_plan: string
		planning_status?: string | null
	}>
	resolved: {
		class_teaching_plan?: string | null
		course_plan?: string | null
		unit_plan?: string | null
		can_initialize: number
		requires_course_plan_selection: number
	}
	teaching_plan: null | {
		class_teaching_plan: string
		title: string
		course_plan: string
		planning_status?: string | null
		team_note?: string | null
	}
	resources: {
		shared_resources: StaffPlanningMaterial[]
		class_resources: StaffPlanningMaterial[]
		general_assigned_work: StaffAssignedWork[]
	}
	curriculum: {
		units: StaffPlanningUnit[]
		session_count: number
		assigned_work_count: number
	}
}
