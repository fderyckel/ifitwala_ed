// ifitwala_ed/ui-spa/src/lib/admission.ts

import { api } from './client'

export const ADMISSION_API = {
  dashboard: 'ifitwala_ed.api.inquiry.get_dashboard_data',
  admissionsCockpit: 'ifitwala_ed.api.admission_cockpit.get_admissions_cockpit_data',
  inquiryTypes: 'ifitwala_ed.api.inquiry.get_inquiry_types',
  organizations: 'ifitwala_ed.api.inquiry.get_inquiry_organizations',
  schools: 'ifitwala_ed.api.inquiry.get_inquiry_schools',
  // Reusing the existing link query if needed, though often we just want a simple list for dropdowns
  academicYears: 'ifitwala_ed.api.inquiry.academic_year_link_query',
  users: 'ifitwala_ed.api.inquiry.admission_user_link_query',
}

export type DashboardFilters = {
  date_mode?: 'preset' | 'custom' | 'academic_year'
  date_preset?: string
  from_date?: string
  to_date?: string
  academic_year?: string
  type_of_inquiry?: string
  assigned_to?: string
  sla_status?: string // 'Overdue', 'Due Today', 'Upcoming'
  organization?: string
  school?: string
}

export function getInquiryDashboardData(filters: DashboardFilters = {}) {
  return api(ADMISSION_API.dashboard, { filters })
}

export type AdmissionsCockpitFilters = {
  organization?: string
  school?: string
  assigned_to_me?: number
  include_terminal?: number
  application_statuses?: string[]
  limit?: number
}

export function getAdmissionsCockpitData(filters: AdmissionsCockpitFilters = {}) {
  return api(ADMISSION_API.admissionsCockpit, { filters })
}

export function getInquiryTypes() {
  return api(ADMISSION_API.inquiryTypes)
}

export function searchAcademicYears(txt: string) {
  return api(ADMISSION_API.academicYears, {
    doctype: 'Academic Year',
    txt,
    searchfield: 'name',
    start: 0,
    page_len: 20,
    filters: {},
  })
}

export function searchAdmissionUsers(txt: string) {
  return api(ADMISSION_API.users, {
    doctype: 'User',
    txt,
    searchfield: 'full_name',
    start: 0,
    page_len: 20,
    filters: {},
  })
}

export function getInquiryOrganizations() {
  return api(ADMISSION_API.organizations)
}

export function getInquirySchools() {
  return api(ADMISSION_API.schools)
}
