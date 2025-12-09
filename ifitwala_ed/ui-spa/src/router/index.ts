// apps/ifitwala_ed/ifitwala_ed/ui-spa/src/router/index.ts

import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  // redirect to a *named route* inside the /portal base, not to '/portal'
  {
    path: '/',
    redirect: () => {
      const section = (window as any).defaultPortal || 'student';
      return { name: `${section}-home` };
    },
  },

  // Student
  { path: '/student', name: 'student-home', component: () => import('@/pages/student/StudentHome.vue'), meta: { layout: 'student' } },
  { path: '/student/logs', name: 'student-logs', component: () => import('@/pages/student/StudentLogs.vue'), meta: { layout: 'student' } },
  { path: '/student/profile', name: 'student-profile', component: () => import('@/pages/student/Profile.vue'), meta: { layout: 'student' } },
  { path: '/student/courses', name: 'student-courses', component: () => import('@/pages/student/Courses.vue'), meta: { layout: 'student' } },
  { path: '/student/courses/:course_id', name: 'student-course-detail', component: () => import('@/pages/student/CourseDetail.vue'), props: route => ({ course_id: String(route.params.course_id || '') }), meta: { layout: 'student' }},

  // Guardian
  { path: '/guardian', name: 'guardian-home', component: () => import('@/pages/guardian/GuardianHome.vue'), meta: { layout: 'student' } },
  { path: '/guardian/students/:student_id', name: 'guardian-student', component: () => import('@/pages/guardian/GuardianStudentShell.vue'), meta: { layout: 'student' } },

 // Staff
  { path: '/staff', name: 'staff-home', component: () => import('@/pages/staff/StaffHome.vue'), meta: { layout: 'staff' } },

	{path: '/staff/morning-brief', name: 'MorningBriefing', component: () => import('@/pages/staff/morning_brief/MorningBriefing.vue'), meta: { layout: 'staff' } },
  { path: '/staff/student-groups', name: 'staff-student-groups', component: () => import('@/pages/staff/schedule/student-groups/StudentGroups.vue'), meta: { layout: 'staff' } },
  { path: '/staff/attendance', name: 'staff-attendance', component: () => import('@/pages/staff/schedule/student-attendance-tool/StudentAttendanceTool.vue'), meta: { layout: 'staff' } },
  { path: '/staff/gradebook', name: 'staff-gradebook', component: () => import('@/pages/staff/gradebook/Gradebook.vue'), meta: { layout: 'staff' } },
	{ path: '/staff/analytics/student-logs', name: 'staff-student-log-analytics', component: () => import('@/pages/staff/analytics/StudentLogAnalytics.vue'), meta: { layout: 'staff' } },
	{ path: '/staff/analytics/student-demographics', name: 'student-demographic-analytics', component: () => import('@/pages/staff/analytics/StudentDemographicAnalytics.vue'), meta: { layout: 'staff' } },
	{ path: '/staff/analytics/student-overview', name: 'staff-student-overview', component: () => import('@/pages/staff/analytics/StudentOverview.vue'), meta: { layout: 'staff' } },
  {
    path: '/staff/announcements',
    name: 'staff-announcements',
    component: () => import('@/pages/staff/OrgCommunicationArchive.vue'),
    meta: { layout: 'staff' }
  },

	{ path: '/staff/analytics/inquiry', name: 'staff-inquiry-analytics', component: () => import('@/pages/staff/analytics/InquiryAnalytics.vue'), meta: { layout: 'staff' } },
]

const router = createRouter({
  // important: keep base history at /portal (no trailing slash)
  history: createWebHistory('/portal'),
  routes,
})

router.beforeEach((to) => {
  const roles = (window as unknown as { portalRoles?: string[] }).portalRoles || []

  if (roles.includes('Student') && (to.path.startsWith('/staff') || to.path.startsWith('/guardian'))) {
    return { name: 'student-home' }
  }

  return true
})

export default router
