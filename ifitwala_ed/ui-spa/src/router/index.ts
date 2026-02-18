// ui-spa/src/router/index.ts

import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { toast } from 'frappe-ui'

const routes: RouteRecordRaw[] = [
  // redirect to a named canonical portal namespace
  {
    path: '/',
    redirect: () => {
      const section = (window as any).defaultPortal || 'student';
      return { name: `${section}-home` };
    },
  },

  // Student
  { path: '/student', name: 'student-home', component: () => import('@/pages/student/StudentHome.vue'), meta: { layout: 'student' } },
  { path: '/student/activities', name: 'student-activities', component: () => import('@/pages/student/StudentActivities.vue'), meta: { layout: 'student' } },
  { path: '/student/portfolio', name: 'student-portfolio', component: () => import('@/pages/student/StudentPortfolioFeed.vue'), meta: { layout: 'student', portal: 'Student' } },
  { path: '/student/logs', name: 'student-logs', component: () => import('@/pages/student/StudentLogs.vue'), meta: { layout: 'student' } },
  { path: '/student/profile', name: 'student-profile', component: () => import('@/pages/student/Profile.vue'), meta: { layout: 'student' } },
  { path: '/student/courses', name: 'student-courses', component: () => import('@/pages/student/Courses.vue'), meta: { layout: 'student' } },
  { path: '/student/courses/:course_id', name: 'student-course-detail', component: () => import('@/pages/student/CourseDetail.vue'), props: route => ({ course_id: String(route.params.course_id || '') }), meta: { layout: 'student' }},

  // Guardian
  { path: '/guardian', name: 'guardian-home', component: () => import('@/pages/guardian/GuardianHome.vue'), meta: { layout: 'student' } },
  { path: '/guardian/activities', name: 'guardian-activities', component: () => import('@/pages/guardian/GuardianActivities.vue'), meta: { layout: 'student' } },
  { path: '/guardian/portfolio', name: 'guardian-portfolio', component: () => import('@/pages/guardian/GuardianPortfolioFeed.vue'), meta: { layout: 'student', portal: 'Guardian' } },
  { path: '/guardian/students/:student_id', name: 'guardian-student', component: () => import('@/pages/guardian/GuardianStudentShell.vue'), meta: { layout: 'student' } },

  // Staff
  { path: '/staff', name: 'staff-home', component: () => import('@/pages/staff/StaffHome.vue'), meta: { layout: 'staff' } },
  { path: '/staff/portfolio', name: 'staff-portfolio', component: () => import('@/pages/staff/StaffPortfolioFeed.vue'), meta: { layout: 'staff', portal: 'Staff' } },
  { path: '/staff/organization-chart', name: 'staff-organization-chart', component: () => import('@/pages/staff/organization_chart/OrganizationChart.vue'), meta: { layout: 'staff' } },
  { path: '/staff/class/:studentGroup', name: 'ClassHub', component: () => import('@/pages/staff/ClassHub.vue'), meta: { layout: 'staff' } },

	{path: '/staff/morning-brief', name: 'MorningBriefing', component: () => import('@/pages/staff/morning_brief/MorningBriefing.vue'), meta: { layout: 'staff' } },
  { path: '/staff/student-groups', name: 'staff-student-groups', component: () => import('@/pages/staff/schedule/student-groups/StudentGroups.vue'), meta: { layout: 'staff' } },
  { path: '/staff/attendance', name: 'staff-attendance', component: () => import('@/pages/staff/schedule/StudentAttendanceTool.vue'), meta: { layout: 'staff' } },
  { path: '/staff/gradebook', name: 'staff-gradebook', component: () => import('@/pages/staff/gradebook/Gradebook.vue'), meta: { layout: 'staff' } },
	{ path: '/staff/analytics/student-logs', name: 'staff-student-log-analytics', component: () => import('@/pages/staff/analytics/StudentLogAnalytics.vue'), meta: { layout: 'staff' } },
	{ path: '/staff/analytics/student-demographics', name: 'student-demographic-analytics', component: () => import('@/pages/staff/analytics/StudentDemographicAnalytics.vue'), meta: { layout: 'staff' } },
	{ path: '/staff/analytics/student-overview', name: 'staff-student-overview', component: () => import('@/pages/staff/analytics/StudentOverview.vue'), meta: { layout: 'staff' } },
	{ path: '/staff/analytics/attendance', name: 'staff-attendance-analytics', component: () => import('@/pages/staff/analytics/AttendanceAnalytics.vue'), meta: { layout: 'staff' } },
	{ path: '/staff/analytics/attendance-ledger', name: 'staff-attendance-ledger', component: () => import('@/pages/staff/analytics/AttendanceLedger.vue'), meta: { layout: 'staff' } },
	{ path: '/staff/analytics/enrollment', name: 'StaffEnrollmentAnalytics', component: () => import('@/pages/staff/analytics/EnrollmentAnalytics.vue'), meta: { layout: 'staff' } },
  { path: '/staff/announcements', name: 'staff-announcements', component: () => import('@/pages/staff/OrgCommunicationArchive.vue'), meta: { layout: 'staff' } },
	{ path: '/staff/analytics/inquiry', name: 'staff-inquiry-analytics', component: () => import('@/pages/staff/analytics/InquiryAnalytics.vue'), meta: { layout: 'staff' } },
	{ path: '/staff/room-utilization', name: 'staff-room-utilization', component: () => import('@/pages/staff/analytics/RoomUtilization.vue'), meta: { layout: 'staff' } },
	{ path: '/analytics/scheduling/room-utilization', redirect: { name: 'staff-room-utilization' } },
]

const router = createRouter({
  // Canonical portal namespace is /portal; route paths remain base-less inside SPA.
  history: createWebHistory('/portal'),
  routes,
})

router.beforeEach((to) => {
  const rawDefaultPortal = (window as unknown as { defaultPortal?: string }).defaultPortal || 'student'
  const defaultPortal = String(rawDefaultPortal || 'student').trim().toLowerCase() || 'student'

  const rawRoles = (window as unknown as { portalRoles?: unknown }).portalRoles
  const roles = (Array.isArray(rawRoles) ? rawRoles : [])
    .map((role) => String(role || '').trim().toLowerCase())
    .filter(Boolean)
  if (!roles.length && defaultPortal) {
    roles.push(defaultPortal)
  }

  const routePath = String(to.path || '')
  const sectionFromPath =
    routePath.startsWith('/staff')
      ? 'staff'
      : routePath.startsWith('/guardian')
        ? 'guardian'
        : routePath.startsWith('/student')
          ? 'student'
          : null

  if (sectionFromPath && !roles.includes(sectionFromPath)) {
    toast.error(`You do not have access to the ${sectionFromPath} portal.`)
    return { name: `${defaultPortal}-home` }
  }

  const required = ((to.meta as any)?.portal as string | undefined)?.trim().toLowerCase()
  if (required && !roles.includes(required)) {
    toast.error(`You do not have access to the ${required} portfolio view.`)
    return { name: `${defaultPortal}-home` }
  }
  return true
})


export default router
