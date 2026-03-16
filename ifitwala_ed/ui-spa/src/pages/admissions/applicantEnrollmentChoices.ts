// ifitwala_ed/ui-spa/src/pages/admissions/applicantEnrollmentChoices.ts

import type { ApplicantEnrollmentChoiceCourse } from '@/types/contracts/admissions/get_applicant_enrollment_choices'

export type EnrollmentChoiceSubmitRow = {
  course: string
  applied_basket_group?: string | null
  choice_rank?: number | null
}

export type EnrollmentChoiceBasketSection = {
  basket_group: string
  required_by_rule: boolean
  selected_count: number
  courses: Array<
    ApplicantEnrollmentChoiceCourse & {
      selected_in_group: boolean
      selected_elsewhere: boolean
    }
  >
}

export type EnrollmentChoiceSections = {
  required_courses: ApplicantEnrollmentChoiceCourse[]
  basket_sections: EnrollmentChoiceBasketSection[]
  ungrouped_courses: ApplicantEnrollmentChoiceCourse[]
}

export function normalizeEnrollmentChoiceRow(
  row: ApplicantEnrollmentChoiceCourse
): ApplicantEnrollmentChoiceCourse {
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

export function buildEnrollmentChoiceSections(
  rows: ApplicantEnrollmentChoiceCourse[],
  requiredBasketGroups: string[]
): EnrollmentChoiceSections {
  const requiredCourses: ApplicantEnrollmentChoiceCourse[] = []
  const basketSections = new Map<string, EnrollmentChoiceBasketSection>()
  const ungroupedCourses: ApplicantEnrollmentChoiceCourse[] = []
  const requiredGroups = new Set(requiredBasketGroups || [])

  for (const rawRow of rows || []) {
    const row = normalizeEnrollmentChoiceRow(rawRow)
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

export function enrollmentChoiceRowsForSubmit(
  rows: ApplicantEnrollmentChoiceCourse[]
): EnrollmentChoiceSubmitRow[] {
  const output: EnrollmentChoiceSubmitRow[] = []

  for (const rawRow of rows || []) {
    const row = normalizeEnrollmentChoiceRow(rawRow)
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

export function haveEnrollmentChoiceRowsChanged(
  currentRows: ApplicantEnrollmentChoiceCourse[],
  savedRows: ApplicantEnrollmentChoiceCourse[]
): boolean {
  return (
    JSON.stringify(enrollmentChoiceRowsForSubmit(currentRows)) !==
    JSON.stringify(enrollmentChoiceRowsForSubmit(savedRows))
  )
}
