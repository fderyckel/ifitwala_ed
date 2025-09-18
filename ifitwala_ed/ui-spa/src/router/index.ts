// apps/ifitwala_ed/ifitwala_ed/ui-spa/src/router/index.ts

import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
	// everything below is relative to the base '/portal'
	{ path: '/', redirect: { name: 'student-home' } },

	{ path: '/student', name: 'student-home', component: () => import('@/pages/student/StudentHome.vue') },
	{ path: '/student/logs', name: 'student-logs', component: () => import('@/pages/student/StudentLogs.vue') },
	{ path: '/student/profile', name: 'student-profile', component: () => import('@/pages/common/Profile.vue') },

	{ path: '/guardian', name: 'guardian-home', component: () => import('@/pages/guardian/GuardianHome.vue') },
	{ path: '/guardian/students/:student_id', name: 'guardian-student', component: () => import('@/pages/guardian/GuardianStudentShell.vue') },

	// optional: 404 inside the SPA base
	{ path: '/:pathMatch(.*)*', redirect: { name: 'student-home' } }
]

export default createRouter({
	// IMPORTANT: history base is '/portal' because your Jinja route is /portal
	history: createWebHistory('/portal'),
	routes,
	scrollBehavior() { return { top: 0 } }
})
