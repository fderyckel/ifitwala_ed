import type { ChildRef } from '@/types/contracts/guardian/get_guardian_home_snapshot'
import type { StudentLearningMaterial } from '@/types/contracts/student_learning/get_student_learning_space'

export type Request = {
	student_id: string
}

export type GuardianStudentCourseBrief = {
	course: string
	course_name: string
	course_group?: string | null
	class_label?: string | null
	current_unit?: {
		unit_plan: string
		title: string
		overview?: string | null
		essential_understanding?: string | null
		content?: string | null
		skills?: string | null
		concepts?: string | null
	} | null
	current_session?: {
		class_session: string
		title: string
		session_date?: string | null
		learning_goal?: string | null
	} | null
	focus_statement?: string | null
	next_step?: string | null
	next_step_supporting_text?: string | null
	upcoming_experiences: Array<{
		class_session: string
		title: string
		session_date?: string | null
		learning_goal?: string | null
	}>
	dinner_prompt?: string | null
	support_resources?: StudentLearningMaterial[]
}

export type Response = {
	meta: {
		generated_at: string
		guardian: { name: string | null }
		student: string
	}
	student: ChildRef
	course_briefs: GuardianStudentCourseBrief[]
}
