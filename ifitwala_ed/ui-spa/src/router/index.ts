// apps/ifitwala_ed/ifitwala_ed/ui-spa/src/router/index.ts

import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  // redirect to a *named route* inside the /portal base, not to '/portal'
  { path: '/', redirect: { name: 'student-home' } },

  // Student
  { path: '/student', name: 'student-home', component: () => import('@/pages/student/StudentHome.vue') },
  { path: '/student/logs', name: 'student-logs', component: () => import('@/pages/student/StudentLogs.vue') },
  { path: '/student/profile', name: 'student-profile', component: () => import('@/pages/Profile.vue') },

  // Guardian
  { path: '/guardian', name: 'guardian-home', component: () => import('@/pages/guardian/GuardianHome.vue') },
  { path: '/guardian/students/:student_id', name: 'guardian-student', component: () => import('@/pages/guardian/GuardianStudentShell.vue') },
]

export default createRouter({
  // important: keep base history at /portal (no trailing slash)
  history: createWebHistory('/portal'),
  routes,
})

