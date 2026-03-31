// ui-spa/src/lib/services/staff/staffTeachingService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetStaffClassPlanningSurfaceRequest,
	Response as GetStaffClassPlanningSurfaceResponse,
	StaffPlanningActivity,
} from '@/types/contracts/staff_teaching/get_staff_class_planning_surface'

const METHODS = {
	getSurface: 'ifitwala_ed.api.teaching_plans.get_staff_class_planning_surface',
	createPlan: 'ifitwala_ed.api.teaching_plans.create_class_teaching_plan',
	savePlan: 'ifitwala_ed.api.teaching_plans.save_class_teaching_plan',
	saveUnit: 'ifitwala_ed.api.teaching_plans.save_class_teaching_plan_unit',
	saveSession: 'ifitwala_ed.api.teaching_plans.save_class_session',
} as const

export type CreateClassTeachingPlanRequest = {
	student_group: string
	course_plan: string
}

export type CreateClassTeachingPlanResponse = {
	class_teaching_plan: string
	student_group: string
}

export type SaveClassTeachingPlanRequest = {
	class_teaching_plan: string
	planning_status?: string
	team_note?: string
}

export type SaveClassTeachingPlanResponse = {
	class_teaching_plan: string
	planning_status?: string | null
}

export type SaveClassTeachingPlanUnitRequest = {
	class_teaching_plan: string
	unit_plan: string
	pacing_status?: string
	teacher_focus?: string
	pacing_note?: string
}

export type SaveClassTeachingPlanUnitResponse = {
	class_teaching_plan: string
	unit_plan: string
	pacing_status?: string | null
}

export type SaveClassSessionRequest = {
	class_teaching_plan: string
	unit_plan: string
	title: string
	session_status?: string
	session_date?: string | null
	sequence_index?: number | null
	learning_goal?: string
	teacher_note?: string
	class_session?: string
	activities: StaffPlanningActivity[]
}

export type SaveClassSessionResponse = {
	class_session: string
	class_teaching_plan: string
	session_status?: string | null
}

export async function getStaffClassPlanningSurface(
	payload: GetStaffClassPlanningSurfaceRequest
): Promise<GetStaffClassPlanningSurfaceResponse> {
	return apiMethod<GetStaffClassPlanningSurfaceResponse>(METHODS.getSurface, payload)
}

export async function createClassTeachingPlan(
	payload: CreateClassTeachingPlanRequest
): Promise<CreateClassTeachingPlanResponse> {
	return apiMethod<CreateClassTeachingPlanResponse>(METHODS.createPlan, payload)
}

export async function saveClassTeachingPlan(
	payload: SaveClassTeachingPlanRequest
): Promise<SaveClassTeachingPlanResponse> {
	return apiMethod<SaveClassTeachingPlanResponse>(METHODS.savePlan, payload)
}

export async function saveClassTeachingPlanUnit(
	payload: SaveClassTeachingPlanUnitRequest
): Promise<SaveClassTeachingPlanUnitResponse> {
	return apiMethod<SaveClassTeachingPlanUnitResponse>(METHODS.saveUnit, payload)
}

export async function saveClassSession(
	payload: SaveClassSessionRequest
): Promise<SaveClassSessionResponse> {
	const { activities, ...rest } = payload
	return apiMethod<SaveClassSessionResponse>(METHODS.saveSession, {
		...rest,
		activities_json: JSON.stringify(activities || []),
	})
}
