// ui-spa/src/lib/services/staff/staffTeachingService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetStaffClassPlanningSurfaceRequest,
	Response as GetStaffClassPlanningSurfaceResponse,
	StaffPlanningActivity,
	StaffPlanningMaterial,
} from '@/types/contracts/staff_teaching/get_staff_class_planning_surface'

const METHODS = {
	getSurface: 'ifitwala_ed.api.teaching_plans.get_staff_class_planning_surface',
	createPlan: 'ifitwala_ed.api.teaching_plans.create_class_teaching_plan',
	savePlan: 'ifitwala_ed.api.teaching_plans.save_class_teaching_plan',
	saveUnit: 'ifitwala_ed.api.teaching_plans.save_class_teaching_plan_unit',
	saveSession: 'ifitwala_ed.api.teaching_plans.save_class_session',
	createPlanningReferenceMaterial:
		'ifitwala_ed.api.teaching_plans.create_class_planning_reference_material',
	uploadPlanningMaterialFile:
		'ifitwala_ed.api.teaching_plans.upload_class_planning_material_file',
	removePlanningMaterial: 'ifitwala_ed.api.teaching_plans.remove_class_planning_material',
} as const

export type PlanningMaterialAnchorDoctype = 'Class Teaching Plan' | 'Class Session'

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

export type CreateClassPlanningReferenceMaterialRequest = {
	anchor_doctype: PlanningMaterialAnchorDoctype
	anchor_name: string
	title: string
	reference_url: string
	description?: string
	modality?: string
	usage_role?: string
	placement_note?: string
}

export type CreateClassPlanningReferenceMaterialResponse = {
	anchor_doctype: PlanningMaterialAnchorDoctype
	anchor_name: string
	placement: string
	resource: StaffPlanningMaterial
}

export type UploadClassPlanningMaterialFileRequest = {
	anchor_doctype: PlanningMaterialAnchorDoctype
	anchor_name: string
	title: string
	file: File
	description?: string
	modality?: string
	usage_role?: string
	placement_note?: string
}

export type UploadClassPlanningMaterialFileResponse = {
	anchor_doctype: PlanningMaterialAnchorDoctype
	anchor_name: string
	placement: string
	resource: StaffPlanningMaterial
}

export type RemoveClassPlanningMaterialRequest = {
	anchor_doctype: PlanningMaterialAnchorDoctype
	anchor_name: string
	placement: string
}

export type RemoveClassPlanningMaterialResponse = {
	anchor_doctype: PlanningMaterialAnchorDoctype
	anchor_name: string
	placement: string
	removed: number
}

function parseServerMessages(raw: unknown): string[] {
	if (typeof raw !== 'string' || !raw.trim()) {
		return []
	}
	try {
		const entries = JSON.parse(raw)
		if (!Array.isArray(entries)) return []
		return entries
			.map((entry: unknown) => {
				if (typeof entry !== 'string') return String(entry || '')
				try {
					const payload = JSON.parse(entry)
					return typeof payload?.message === 'string' ? payload.message : entry
				} catch {
					return entry
				}
			})
			.filter((message: string) => Boolean((message || '').trim()))
	} catch {
		return []
	}
}

function csrfToken(): string {
	if (typeof window === 'undefined') return ''
	return (
		(window as Window & { csrf_token?: string }).csrf_token ||
		(window as Window & { frappe?: { csrf_token?: string } }).frappe?.csrf_token ||
		''
	)
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

export async function createClassPlanningReferenceMaterial(
	payload: CreateClassPlanningReferenceMaterialRequest
): Promise<CreateClassPlanningReferenceMaterialResponse> {
	return apiMethod<CreateClassPlanningReferenceMaterialResponse>(
		METHODS.createPlanningReferenceMaterial,
		payload
	)
}

export async function uploadClassPlanningMaterialFile(
	payload: UploadClassPlanningMaterialFileRequest
): Promise<UploadClassPlanningMaterialFileResponse> {
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

	const response = await fetch(`/api/method/${METHODS.uploadPlanningMaterialFile}`, {
		method: 'POST',
		credentials: 'same-origin',
		body: formData,
		headers: csrfToken() ? { 'X-Frappe-CSRF-Token': csrfToken() } : undefined,
	})

	const data = await response.json().catch(() => ({}))
	if (!response.ok || data?.exception || data?.exc) {
		const serverMessages = parseServerMessages(data?._server_messages)
		throw new Error(
			serverMessages.join('\n') || data?.message || response.statusText || 'Upload failed.'
		)
	}
	return (data?.message ?? data) as UploadClassPlanningMaterialFileResponse
}

export async function removeClassPlanningMaterial(
	payload: RemoveClassPlanningMaterialRequest
): Promise<RemoveClassPlanningMaterialResponse> {
	return apiMethod<RemoveClassPlanningMaterialResponse>(METHODS.removePlanningMaterial, payload)
}
