import type {
	StaffPlanningClassReflection,
	StaffPlanningMaterial,
	StaffPlanningReflection,
	StaffPlanningStandard,
} from '@/types/contracts/staff_teaching/get_staff_class_planning_surface'

export type Request = {
	course_plan: string
	unit_plan?: string
}

export type StaffCoursePlanUnit = {
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
	}
	resources: {
		course_plan_resources: StaffPlanningMaterial[]
	}
	curriculum: {
		units: StaffCoursePlanUnit[]
		unit_count: number
	}
}
