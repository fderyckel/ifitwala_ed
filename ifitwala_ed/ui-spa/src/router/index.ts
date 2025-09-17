import { createRouter, createWebHistory } from 'vue-router'

const routes = [
	{ path: '/', redirect: '/portal' },
	{ path: '/portal', component: () => import('../pages/StudentHome.vue') },
	{ path: '/portal/student', component: () => import('../pages/StudentHome.vue') },
	{ path: '/portal/student/logs', component: () => import('../pages/StudentLogs.vue') },
	{ path: '/portal/guardian', component: () => import('../pages/GuardianHome.vue') },
	{ path: '/portal/guardian/students/:student_id', component: () => import('../pages/GuardianStudentShell.vue') },
	{ path: '/portal/student/profile', component: () => import('../pages/Profile.vue') }
]

const router = createRouter({
	history: createWebHistory('/portal'),
	routes
})

router.beforeEach(async (to, from, next) => {
	// minimal auth hook; we’ll wire a real ping later
	const isLoggedIn = true
	if (!isLoggedIn && to.path !== '/login') {
		window.location.href = `/login?redirect-to=${encodeURIComponent(to.fullPath)}`
		return
	}
	next()
})

export default router
