// ifitwala_ed/ui-spa/src/types/contracts/admissions/get_applicant_enrollment_choices.ts

export type Request = {
  student_applicant?: string
}

export type ApplicantEnrollmentChoiceCourse = {
  course: string
  course_name?: string | null
  required: boolean
  basket_groups: string[]
  applied_basket_group?: string | null
  choice_rank?: number | null
  is_selected: boolean
  requires_basket_group_selection: boolean
  is_explicit_choice: boolean
  has_choice_rank: boolean
}

export type Response = {
  plan: {
    name: string
    status: string
    academic_year?: string | null
    term?: string | null
    program?: string | null
    program_offering?: string | null
    offer_expires_on?: string | null
    can_edit_choices: boolean
    can_respond_to_offer: boolean
  } | null
  summary: {
    has_plan: boolean
    has_courses: boolean
    has_selectable_courses: boolean
    can_edit_choices: boolean
    ready_for_offer_response: boolean
    required_course_count: number
    optional_course_count: number
    selected_optional_count: number
    message?: string | null
  }
  validation: {
    status?: string | null
    ready_for_offer_response: boolean
    reasons: string[]
    violations: Array<{
      code?: string
      message?: string
      rule_type?: string
      rule_idx?: number
    }>
    missing_required_courses: string[]
    ambiguous_courses: string[]
    group_summary: Record<string, number>
  }
  required_basket_groups: string[]
  courses: ApplicantEnrollmentChoiceCourse[]
}
