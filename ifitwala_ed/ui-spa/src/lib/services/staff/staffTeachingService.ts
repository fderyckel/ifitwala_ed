// ui-spa/src/lib/services/staff/staffTeachingService.ts

import { apiUpload } from '@/lib/client'
import type { UploadProgressCallback } from '@/lib/uploadProgress'
import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetStaffClassPlanningSurfaceRequest,
	Response as GetStaffClassPlanningSurfaceResponse,
	StaffPlanningActivity,
	StaffPlanningMaterial,
	StaffPlanningReflection,
	StaffPlanningStandard,
} from '@/types/contracts/staff_teaching/get_staff_class_planning_surface'
import type {
	Response as GetStaffCoursePlanIndexResponse,
} from '@/types/contracts/staff_teaching/get_staff_course_plan_index'
import type {
	Request as GetLearningStandardPickerRequest,
	Response as GetLearningStandardPickerResponse,
} from '@/types/contracts/staff_teaching/get_learning_standard_picker'
import type {
	Request as GetStaffCoursePlanSurfaceRequest,
	Response as GetStaffCoursePlanSurfaceResponse,
	StaffCoursePlanQuizQuestion,
} from '@/types/contracts/staff_teaching/get_staff_course_plan_surface'

const METHODS = {
	getClassPlanningSurface: 'ifitwala_ed.api.teaching_plans.get_staff_class_planning_surface',
	getCoursePlanIndex: 'ifitwala_ed.api.teaching_plans.list_staff_course_plans',
	getCoursePlanSurface: 'ifitwala_ed.api.teaching_plans.get_staff_course_plan_surface',
	getLearningStandardPicker:
		'ifitwala_ed.curriculum.doctype.unit_plan.unit_plan.get_learning_standard_picker',
	createCoursePlan: 'ifitwala_ed.api.teaching_plans.create_course_plan',
	createPlan: 'ifitwala_ed.api.teaching_plans.create_class_teaching_plan',
	saveCoursePlan: 'ifitwala_ed.api.teaching_plans.save_course_plan',
	saveGovernedUnit: 'ifitwala_ed.api.teaching_plans.save_unit_plan',
	savePlan: 'ifitwala_ed.api.teaching_plans.save_class_teaching_plan',
	saveUnit: 'ifitwala_ed.api.teaching_plans.save_class_teaching_plan_unit',
	saveSession: 'ifitwala_ed.api.teaching_plans.save_class_session',
	saveQuizQuestionBank: 'ifitwala_ed.api.quiz.save_question_bank',
	createPlanningReferenceMaterial:
		'ifitwala_ed.api.teaching_plans.create_planning_reference_material',
	uploadPlanningMaterialFile:
		'ifitwala_ed.api.teaching_plans.upload_planning_material_file',
	removePlanningMaterial: 'ifitwala_ed.api.teaching_plans.remove_planning_material',
} as const

export type PlanningMaterialAnchorDoctype =
	| 'Course Plan'
	| 'Unit Plan'
	| 'Class Teaching Plan'
	| 'Class Session'

export type CreateClassTeachingPlanRequest = {
	student_group: string
	course_plan: string
}

export type CreateClassTeachingPlanResponse = {
	class_teaching_plan: string
	student_group: string
}

export type CreateCoursePlanRequest = {
	course: string
	title?: string | null
	academic_year?: string | null
	cycle_label?: string | null
	plan_status?: string | null
	summary?: string | null
}

export type CreateCoursePlanResponse = {
	course_plan: string
	course: string
	title: string
	plan_status?: string | null
}

export type SaveCoursePlanRequest = {
	course_plan: string
	expected_modified?: string | null
	title: string
	academic_year?: string | null
	cycle_label?: string | null
	plan_status?: string | null
	summary?: string | null
}

export type SaveCoursePlanResponse = {
	course_plan: string
	plan_status?: string | null
}

export type SaveGovernedUnitPlanRequest = {
	course_plan: string
	unit_plan?: string
	expected_modified?: string | null
	title: string
	program?: string | null
	unit_code?: string | null
	unit_order?: number | null
	unit_status?: string | null
	version?: string | null
	duration?: string | null
	estimated_duration?: string | null
	is_published?: number | boolean | null
	overview?: string | null
	essential_understanding?: string | null
	misconceptions?: string | null
	content?: string | null
	skills?: string | null
	concepts?: string | null
	standards: StaffPlanningStandard[]
	reflections: StaffPlanningReflection[]
}

export type SaveGovernedUnitPlanResponse = {
	course_plan: string
	unit_plan: string
	unit_order?: number | null
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
	prior_to_the_unit?: string
	during_the_unit?: string
	what_work_well?: string
	what_didnt_work_well?: string
	changes_suggestions?: string
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

export type SaveQuizQuestionBankRequest = {
	course_plan: string
	quiz_question_bank?: string
	expected_modified?: string | null
	bank_title: string
	description?: string | null
	is_published?: number | boolean | null
	questions: StaffCoursePlanQuizQuestion[]
}

export type SaveQuizQuestionBankResponse = {
	quiz_question_bank: string
	course?: string | null
	is_published?: number
}

export type CreatePlanningReferenceMaterialRequest = {
	anchor_doctype: PlanningMaterialAnchorDoctype
	anchor_name: string
	title: string
	reference_url: string
	description?: string
	modality?: string
	usage_role?: string
	placement_note?: string
}

export type CreatePlanningReferenceMaterialResponse = {
	anchor_doctype: PlanningMaterialAnchorDoctype
	anchor_name: string
	placement: string
	resource: StaffPlanningMaterial
}

export type UploadPlanningMaterialFileRequest = {
	anchor_doctype: PlanningMaterialAnchorDoctype
	anchor_name: string
	title: string
	file: File
	description?: string
	modality?: string
	usage_role?: string
	placement_note?: string
}

export type UploadPlanningMaterialFileResponse = {
	anchor_doctype: PlanningMaterialAnchorDoctype
	anchor_name: string
	placement: string
	resource: StaffPlanningMaterial
}

export type RemovePlanningMaterialRequest = {
	anchor_doctype: PlanningMaterialAnchorDoctype
	anchor_name: string
	placement: string
}

export type RemovePlanningMaterialResponse = {
	anchor_doctype: PlanningMaterialAnchorDoctype
	anchor_name: string
	placement: string
	removed: number
}

export async function getStaffClassPlanningSurface(
	payload: GetStaffClassPlanningSurfaceRequest
): Promise<GetStaffClassPlanningSurfaceResponse> {
	return apiMethod<GetStaffClassPlanningSurfaceResponse>(METHODS.getClassPlanningSurface, payload)
}

export async function getStaffCoursePlanIndex(): Promise<GetStaffCoursePlanIndexResponse> {
	return apiMethod<GetStaffCoursePlanIndexResponse>(METHODS.getCoursePlanIndex)
}

export async function getStaffCoursePlanSurface(
	payload: GetStaffCoursePlanSurfaceRequest
): Promise<GetStaffCoursePlanSurfaceResponse> {
	return apiMethod<GetStaffCoursePlanSurfaceResponse>(METHODS.getCoursePlanSurface, payload)
}

export async function getLearningStandardPicker(
	payload: GetLearningStandardPickerRequest
): Promise<GetLearningStandardPickerResponse> {
	return apiMethod<GetLearningStandardPickerResponse>(METHODS.getLearningStandardPicker, payload)
}

export async function createCoursePlan(
	payload: CreateCoursePlanRequest
): Promise<CreateCoursePlanResponse> {
	return apiMethod<CreateCoursePlanResponse>(METHODS.createCoursePlan, payload)
}

export async function createClassTeachingPlan(
	payload: CreateClassTeachingPlanRequest
): Promise<CreateClassTeachingPlanResponse> {
	return apiMethod<CreateClassTeachingPlanResponse>(METHODS.createPlan, payload)
}

export async function saveCoursePlan(
	payload: SaveCoursePlanRequest
): Promise<SaveCoursePlanResponse> {
	return apiMethod<SaveCoursePlanResponse>(METHODS.saveCoursePlan, payload)
}

export async function saveGovernedUnitPlan(
	payload: SaveGovernedUnitPlanRequest
): Promise<SaveGovernedUnitPlanResponse> {
	const { standards, reflections, ...rest } = payload
	return apiMethod<SaveGovernedUnitPlanResponse>(METHODS.saveGovernedUnit, {
		...rest,
		standards_json: JSON.stringify(standards || []),
		reflections_json: JSON.stringify(reflections || []),
	})
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

export async function saveQuizQuestionBank(
	payload: SaveQuizQuestionBankRequest
): Promise<SaveQuizQuestionBankResponse> {
	const { questions, ...rest } = payload
	return apiMethod<SaveQuizQuestionBankResponse>(METHODS.saveQuizQuestionBank, {
		...rest,
		questions_json: JSON.stringify(questions || []),
	})
}

export async function createPlanningReferenceMaterial(
	payload: CreatePlanningReferenceMaterialRequest
): Promise<CreatePlanningReferenceMaterialResponse> {
	return apiMethod<CreatePlanningReferenceMaterialResponse>(
		METHODS.createPlanningReferenceMaterial,
		payload
	)
}

export async function uploadPlanningMaterialFile(
	payload: UploadPlanningMaterialFileRequest,
	options: { onProgress?: UploadProgressCallback } = {}
): Promise<UploadPlanningMaterialFileResponse> {
	const formData = new FormData()
	formData.append('anchor_doctype', payload.anchor_doctype)
	formData.append('anchor_name', payload.anchor_name)
	formData.append('title', payload.title)
	if (payload.description?.trim()) formData.append('description', payload.description.trim())
	if (payload.placement_note?.trim())
		formData.append('placement_note', payload.placement_note.trim())
	if (payload.modality) formData.append('modality', payload.modality)
	if (payload.usage_role) formData.append('usage_role', payload.usage_role)
	formData.append('file', payload.file, payload.file.name)

	return apiUpload<UploadPlanningMaterialFileResponse>(
		METHODS.uploadPlanningMaterialFile,
		formData,
		options
	)
}

export async function removePlanningMaterial(
	payload: RemovePlanningMaterialRequest
): Promise<RemovePlanningMaterialResponse> {
	return apiMethod<RemovePlanningMaterialResponse>(METHODS.removePlanningMaterial, payload)
}
