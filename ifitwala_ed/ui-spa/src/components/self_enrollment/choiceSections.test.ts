// ui-spa/src/components/self_enrollment/choiceSections.test.ts

import { describe, expect, it } from 'vitest'

import { applyDefaultChoiceRanks } from '@/components/self_enrollment/choiceSections'
import type { SelfEnrollmentChoiceCourse } from '@/types/contracts/self_enrollment/get_self_enrollment_choice_state'

describe('applyDefaultChoiceRanks', () => {
	it('assigns sequential ranks to selected basket choices that do not have one yet', () => {
		const rows: SelfEnrollmentChoiceCourse[] = [
			{
				course: 'FRA',
				course_name: 'French',
				required: false,
				basket_groups: ['Languages'],
				applied_basket_group: 'Languages',
				choice_rank: null,
				is_selected: true,
				requires_basket_group_selection: false,
				is_explicit_choice: true,
				has_choice_rank: false,
			},
			{
				course: 'SPA',
				course_name: 'Spanish',
				required: false,
				basket_groups: ['Languages'],
				applied_basket_group: 'Languages',
				choice_rank: null,
				is_selected: true,
				requires_basket_group_selection: false,
				is_explicit_choice: true,
				has_choice_rank: false,
			},
		]

		expect(applyDefaultChoiceRanks(rows).map(row => row.choice_rank)).toEqual([1, 2])
	})

	it('keeps explicit ranks and appends new defaults after the highest existing rank in the basket', () => {
		const rows: SelfEnrollmentChoiceCourse[] = [
			{
				course: 'ESS',
				course_name: 'ESS',
				required: false,
				basket_groups: ['Group 4 Sciences'],
				applied_basket_group: 'Group 4 Sciences',
				choice_rank: 2,
				is_selected: true,
				requires_basket_group_selection: false,
				is_explicit_choice: true,
				has_choice_rank: true,
			},
			{
				course: 'BIO',
				course_name: 'Biology',
				required: false,
				basket_groups: ['Group 4 Sciences'],
				applied_basket_group: 'Group 4 Sciences',
				choice_rank: null,
				is_selected: true,
				requires_basket_group_selection: false,
				is_explicit_choice: true,
				has_choice_rank: false,
			},
			{
				course: 'ART',
				course_name: 'Art',
				required: false,
				basket_groups: [],
				applied_basket_group: null,
				choice_rank: null,
				is_selected: true,
				requires_basket_group_selection: false,
				is_explicit_choice: true,
				has_choice_rank: false,
			},
		]

		expect(applyDefaultChoiceRanks(rows).map(row => row.choice_rank)).toEqual([2, 3, null])
	})
})
