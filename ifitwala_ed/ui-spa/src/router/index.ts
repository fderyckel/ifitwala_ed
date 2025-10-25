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
  { path: '/staff/student-groups', name: 'staff-student-groups', component: () => import('@/pages/staff/schedule/student-groups/StudentGroups.vue'), meta: { layout: 'staff' } },
  { path: '/staff/gradebook', name: 'staff-gradebook', component: () => import('@/pages/staff/gradebook/Gradebook.vue'), meta: { layout: 'staff' } },
]

export default createRouter({
  // important: keep base history at /portal (no trailing slash)
  history: createWebHistory('/portal'),
  routes,
})
