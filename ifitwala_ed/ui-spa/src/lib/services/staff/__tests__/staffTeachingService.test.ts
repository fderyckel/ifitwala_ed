// ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'

const { apiMethodMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
}))

const fetchMock = vi.fn()

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

import {
	createPlanningReferenceMaterial,
	getStaffClassPlanningSurface,
	getStaffCoursePlanIndex,
	getStaffCoursePlanSurface,
	removePlanningMaterial,
	saveCoursePlan,
	saveGovernedUnitPlan,
	saveClassSession,
	uploadPlanningMaterialFile,
} from '@/lib/services/staff/staffTeachingService'

describe('staffTeachingService', () => {
	afterEach(() => {
		apiMethodMock.mockReset()
		fetchMock.mockReset()
		vi.unstubAllGlobals()
		delete (window as Window & { csrf_token?: string }).csrf_token
	})

	it('uses the canonical method for planning link resources', async () => {
		apiMethodMock.mockResolvedValue({ placement: 'MAT-PLC-1' })

		await createPlanningReferenceMaterial({
			anchor_doctype: 'Class Teaching Plan',
			anchor_name: 'CLASS-PLAN-1',
			title: 'Starter article',
			reference_url: 'https://example.com/article',
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.teaching_plans.create_planning_reference_material',
			{
				anchor_doctype: 'Class Teaching Plan',
				anchor_name: 'CLASS-PLAN-1',
				title: 'Starter article',
				reference_url: 'https://example.com/article',
			}
		)
	})

	it('uses the canonical method for the staff planning surface', async () => {
		apiMethodMock.mockResolvedValue({
			resources: { shared_resources: [], class_resources: [], general_assigned_work: [] },
			curriculum: { units: [], session_count: 0, assigned_work_count: 0 },
		})

		await getStaffClassPlanningSurface({
			student_group: 'GROUP-1',
			class_teaching_plan: 'CLASS-PLAN-1',
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.teaching_plans.get_staff_class_planning_surface',
			{
				student_group: 'GROUP-1',
				class_teaching_plan: 'CLASS-PLAN-1',
			}
		)
	})

	it('uses the canonical method for the shared course plan index', async () => {
		apiMethodMock.mockResolvedValue({ course_plans: [] })

		await getStaffCoursePlanIndex()

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.teaching_plans.list_staff_course_plans'
		)
	})

	it('uses the canonical method for the shared course plan workspace', async () => {
		apiMethodMock.mockResolvedValue({
			course_plan: { course_plan: 'COURSE-PLAN-1', can_manage_resources: 1 },
			resources: { course_plan_resources: [] },
			curriculum: { units: [], unit_count: 0 },
			resolved: { unit_plan: null },
		})

		await getStaffCoursePlanSurface({
			course_plan: 'COURSE-PLAN-1',
			unit_plan: 'UNIT-1',
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.teaching_plans.get_staff_course_plan_surface',
			{
				course_plan: 'COURSE-PLAN-1',
				unit_plan: 'UNIT-1',
			}
		)
	})

	it('uses the canonical method for saving a shared course plan', async () => {
		apiMethodMock.mockResolvedValue({ course_plan: 'COURSE-PLAN-1', plan_status: 'Active' })

		await saveCoursePlan({
			course_plan: 'COURSE-PLAN-1',
			title: 'Biology Plan',
			academic_year: '2026-2027',
			cycle_label: 'Semester 1',
			plan_status: 'Active',
			summary: 'Shared scope and sequence',
		})

		expect(apiMethodMock).toHaveBeenCalledWith('ifitwala_ed.api.teaching_plans.save_course_plan', {
			course_plan: 'COURSE-PLAN-1',
			title: 'Biology Plan',
			academic_year: '2026-2027',
			cycle_label: 'Semester 1',
			plan_status: 'Active',
			summary: 'Shared scope and sequence',
		})
	})

	it('serializes standards and reflections when saving a governed unit plan', async () => {
		apiMethodMock.mockResolvedValue({ unit_plan: 'UNIT-1', course_plan: 'COURSE-PLAN-1' })

		await saveGovernedUnitPlan({
			course_plan: 'COURSE-PLAN-1',
			unit_plan: 'UNIT-1',
			title: 'Cells and Systems',
			unit_order: 10,
			standards: [
				{
					standard_code: 'STD-1',
					standard_description: 'Explain how cells function.',
				},
			],
			reflections: [
				{
					academic_year: '2026-2027',
					prior_to_the_unit: 'Start with microscope norms.',
				},
			],
		})

		expect(apiMethodMock).toHaveBeenCalledWith('ifitwala_ed.api.teaching_plans.save_unit_plan', {
			course_plan: 'COURSE-PLAN-1',
			unit_plan: 'UNIT-1',
			title: 'Cells and Systems',
			unit_order: 10,
			standards_json: JSON.stringify([
				{
					standard_code: 'STD-1',
					standard_description: 'Explain how cells function.',
				},
			]),
			reflections_json: JSON.stringify([
				{
					academic_year: '2026-2027',
					prior_to_the_unit: 'Start with microscope norms.',
				},
			]),
		})
	})

	it('uploads planning resource files through the class-planning endpoint', async () => {
		fetchMock.mockResolvedValue({
			ok: true,
			json: vi.fn().mockResolvedValue({
				message: {
					placement: 'MAT-PLC-1',
					resource: { material: 'MAT-1', title: 'Graphic organizer' },
				},
			}),
		})
		vi.stubGlobal('fetch', fetchMock)
		Object.assign(window, { csrf_token: 'csrf-123' })

		const file = new File(['worksheet'], 'organizer.pdf', { type: 'application/pdf' })
		await uploadPlanningMaterialFile({
			anchor_doctype: 'Class Session',
			anchor_name: 'CLASS-SESSION-1',
			title: 'Graphic organizer',
			file,
			modality: 'Use',
		})

		expect(fetchMock).toHaveBeenCalledWith(
			'/api/method/ifitwala_ed.api.teaching_plans.upload_planning_material_file',
			expect.objectContaining({
				method: 'POST',
				credentials: 'same-origin',
				headers: { 'X-Frappe-CSRF-Token': 'csrf-123' },
				body: expect.any(FormData),
			})
		)
	})

	it('uses the canonical method when removing planning resources', async () => {
		apiMethodMock.mockResolvedValue({ removed: 1 })

		await removePlanningMaterial({
			anchor_doctype: 'Class Session',
			anchor_name: 'CLASS-SESSION-1',
			placement: 'MAT-PLC-1',
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.teaching_plans.remove_planning_material',
			{
				anchor_doctype: 'Class Session',
				anchor_name: 'CLASS-SESSION-1',
				placement: 'MAT-PLC-1',
			}
		)
	})

	it('serializes activities when saving a class session', async () => {
		apiMethodMock.mockResolvedValue({ class_session: 'CLASS-SESSION-1' })

		await saveClassSession({
			class_teaching_plan: 'CLASS-PLAN-1',
			unit_plan: 'UNIT-1',
			title: 'Evidence walk',
			activities: [
				{
					title: 'Observe',
					activity_type: 'Discuss',
					estimated_minutes: 10,
				},
			],
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.teaching_plans.save_class_session',
			{
				class_teaching_plan: 'CLASS-PLAN-1',
				unit_plan: 'UNIT-1',
				title: 'Evidence walk',
				activities_json: JSON.stringify([
					{
						title: 'Observe',
						activity_type: 'Discuss',
						estimated_minutes: 10,
					},
				]),
			}
		)
	})
})
