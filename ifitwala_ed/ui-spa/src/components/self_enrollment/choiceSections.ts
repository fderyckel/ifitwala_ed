// ui-spa/src/components/self_enrollment/choiceSections.ts

import type { SelfEnrollmentChoiceCourse } from '@/types/contracts/self_enrollment/get_self_enrollment_choice_state'
import type { ChoiceSubmitRow } from '@/types/contracts/self_enrollment/save_self_enrollment_choices'

export type ChoiceBasketSection = {
	basket_group: string
	required_by_rule: boolean
	selected_count: number
	courses: Array<
		SelfEnrollmentChoiceCourse & {
			selected_in_group: boolean
			selected_elsewhere: boolean
		}
	>
}

export type ChoiceSections = {
	required_courses: SelfEnrollmentChoiceCourse[]
	basket_sections: ChoiceBasketSection[]
	ungrouped_courses: SelfEnrollmentChoiceCourse[]
}

export function normalizeChoiceRow(row: SelfEnrollmentChoiceCourse): SelfEnrollmentChoiceCourse {
	return {
		...row,
		course: (row.course || '').trim(),
		course_name: (row.course_name || '').trim(),
		basket_groups: [...(row.basket_groups || [])],
		applied_basket_group: (row.applied_basket_group || '').trim() || null,
		choice_rank:
			typeof row.choice_rank === 'number' && Number.isFinite(row.choice_rank) && row.choice_rank > 0
				? row.choice_rank
				: null,
		required: Boolean(row.required),
		is_selected: Boolean(row.is_selected),
		requires_basket_group_selection: Boolean(row.requires_basket_group_selection),
		is_explicit_choice: Boolean(row.is_explicit_choice),
		has_choice_rank: Boolean(row.has_choice_rank),
	}
}

export function buildChoiceSections(
	rows: SelfEnrollmentChoiceCourse[],
	requiredBasketGroups: string[]
): ChoiceSections {
	const requiredCourses: SelfEnrollmentChoiceCourse[] = []
	const basketSections = new Map<string, ChoiceBasketSection>()
	const ungroupedCourses: SelfEnrollmentChoiceCourse[] = []
	const requiredGroups = new Set(requiredBasketGroups || [])

	for (const rawRow of rows || []) {
		const row = normalizeChoiceRow(rawRow)
		if (!row.course) continue

		if (row.required) {
			requiredCourses.push(row)
			continue
		}

		if (!row.basket_groups.length) {
			ungroupedCourses.push(row)
			continue
		}

		for (const basketGroup of row.basket_groups) {
			if (!basketSections.has(basketGroup)) {
				basketSections.set(basketGroup, {
					basket_group: basketGroup,
					required_by_rule: requiredGroups.has(basketGroup),
					selected_count: 0,
					courses: [],
				})
			}

			const section = basketSections.get(basketGroup)!
			const selectedInGroup =
				row.is_selected &&
				((row.applied_basket_group || '') === basketGroup ||
					(!row.applied_basket_group && row.basket_groups.length === 1))
			const selectedElsewhere =
				row.is_selected &&
				Boolean(row.applied_basket_group) &&
				row.applied_basket_group !== basketGroup

			if (selectedInGroup) {
				section.selected_count += 1
			}

			section.courses.push({
				...row,
				selected_in_group: selectedInGroup,
				selected_elsewhere: selectedElsewhere,
			})
		}
	}

	return {
		required_courses: requiredCourses,
		basket_sections: Array.from(basketSections.values()),
		ungrouped_courses: ungroupedCourses,
	}
}

export function choiceRowsForSubmit(rows: SelfEnrollmentChoiceCourse[]): ChoiceSubmitRow[] {
	const output: ChoiceSubmitRow[] = []

	for (const rawRow of rows || []) {
		const row = normalizeChoiceRow(rawRow)
		if (!row.course) continue

		if (row.required) {
			if (!row.applied_basket_group && row.choice_rank == null) {
				continue
			}
			output.push({
				course: row.course,
				applied_basket_group: row.applied_basket_group || null,
				choice_rank: row.choice_rank ?? null,
			})
			continue
		}

		if (!row.is_selected) continue

		output.push({
			course: row.course,
			applied_basket_group: row.applied_basket_group || null,
			choice_rank: row.choice_rank ?? null,
		})
	}

	return output.sort((left, right) => left.course.localeCompare(right.course))
}

export function haveChoiceRowsChanged(
	currentRows: SelfEnrollmentChoiceCourse[],
	savedRows: SelfEnrollmentChoiceCourse[]
): boolean {
	return (
		JSON.stringify(choiceRowsForSubmit(currentRows)) !==
		JSON.stringify(choiceRowsForSubmit(savedRows))
	)
}
