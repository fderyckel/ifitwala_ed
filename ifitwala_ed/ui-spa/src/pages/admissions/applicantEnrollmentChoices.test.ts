// ifitwala_ed/ui-spa/src/pages/admissions/applicantEnrollmentChoices.test.ts

import { describe, expect, it } from 'vitest'

import {
  buildEnrollmentChoiceSections,
  enrollmentChoiceRowsForSubmit,
  haveEnrollmentChoiceRowsChanged,
} from '@/pages/admissions/applicantEnrollmentChoices'
import type { ApplicantEnrollmentChoiceCourse } from '@/types/contracts/admissions/get_applicant_enrollment_choices'

describe('applicantEnrollmentChoices', () => {
  it('groups multi-basket optional courses into each basket section with selection state', () => {
    const rows: ApplicantEnrollmentChoiceCourse[] = [
      {
        course: 'ESS',
        course_name: 'Environmental Systems and Societies',
        required: false,
        basket_groups: ['Group 3 Humanities', 'Group 4 Sciences'],
        applied_basket_group: 'Group 4 Sciences',
        choice_rank: 1,
        is_selected: true,
        requires_basket_group_selection: false,
        is_explicit_choice: true,
        has_choice_rank: true,
      },
    ]

    const sections = buildEnrollmentChoiceSections(rows, ['Group 3 Humanities'])
    expect(sections.basket_sections).toHaveLength(2)

    const humanities = sections.basket_sections.find(section => section.basket_group === 'Group 3 Humanities')
    const sciences = sections.basket_sections.find(section => section.basket_group === 'Group 4 Sciences')

    expect(humanities?.required_by_rule).toBe(true)
    expect(humanities?.courses[0].selected_elsewhere).toBe(true)
    expect(sciences?.courses[0].selected_in_group).toBe(true)
    expect(sciences?.selected_count).toBe(1)
  })

  it('submits selected optional rows and required basket resolutions only', () => {
    const rows: ApplicantEnrollmentChoiceCourse[] = [
      {
        course: 'ENG',
        course_name: 'English',
        required: true,
        basket_groups: ['Core'],
        applied_basket_group: null,
        choice_rank: null,
        is_selected: true,
        requires_basket_group_selection: false,
        is_explicit_choice: false,
        has_choice_rank: false,
      },
      {
        course: 'ESS',
        course_name: 'ESS',
        required: false,
        basket_groups: ['Group 3 Humanities', 'Group 4 Sciences'],
        applied_basket_group: 'Group 3 Humanities',
        choice_rank: 2,
        is_selected: true,
        requires_basket_group_selection: false,
        is_explicit_choice: true,
        has_choice_rank: true,
      },
      {
        course: 'ART',
        course_name: 'Art',
        required: false,
        basket_groups: [],
        applied_basket_group: null,
        choice_rank: null,
        is_selected: false,
        requires_basket_group_selection: false,
        is_explicit_choice: false,
        has_choice_rank: false,
      },
      {
        course: 'TOK',
        course_name: 'Theory of Knowledge',
        required: true,
        basket_groups: ['Group A', 'Group B'],
        applied_basket_group: 'Group A',
        choice_rank: null,
        is_selected: true,
        requires_basket_group_selection: false,
        is_explicit_choice: true,
        has_choice_rank: false,
      },
    ]

    expect(enrollmentChoiceRowsForSubmit(rows)).toEqual([
      {
        course: 'ESS',
        applied_basket_group: 'Group 3 Humanities',
        choice_rank: 2,
      },
      {
        course: 'TOK',
        applied_basket_group: 'Group A',
        choice_rank: null,
      },
    ])
  })

  it('detects meaningful row changes from the submit payload shape', () => {
    const savedRows: ApplicantEnrollmentChoiceCourse[] = [
      {
        course: 'ESS',
        course_name: 'ESS',
        required: false,
        basket_groups: ['Group 3 Humanities'],
        applied_basket_group: 'Group 3 Humanities',
        choice_rank: 1,
        is_selected: true,
        requires_basket_group_selection: false,
        is_explicit_choice: true,
        has_choice_rank: true,
      },
    ]

    const currentRows: ApplicantEnrollmentChoiceCourse[] = [
      {
        ...savedRows[0],
        applied_basket_group: ' Group 3 Humanities ',
      },
    ]

    expect(haveEnrollmentChoiceRowsChanged(currentRows, savedRows)).toBe(false)
    expect(
      haveEnrollmentChoiceRowsChanged(
        [
          {
            ...savedRows[0],
            choice_rank: 2,
          },
        ],
        savedRows
      )
    ).toBe(true)
  })
})
