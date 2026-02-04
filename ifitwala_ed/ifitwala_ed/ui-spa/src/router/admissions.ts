// ifitwala_ed/ui-spa/src/router/admissions.ts

import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: { name: 'admissions-overview' } },
  { path: '/overview', name: 'admissions-overview', component: () => import('@/pages/admissions/ApplicantOverview.vue') },
  { path: '/health', name: 'admissions-health', component: () => import('@/pages/admissions/ApplicantHealth.vue') },
  { path: '/documents', name: 'admissions-documents', component: () => import('@/pages/admissions/ApplicantDocuments.vue') },
  { path: '/policies', name: 'admissions-policies', component: () => import('@/pages/admissions/ApplicantPolicies.vue') },
  { path: '/submit', name: 'admissions-submit', component: () => import('@/pages/admissions/ApplicantSubmit.vue') },
  { path: '/status', name: 'admissions-status', component: () => import('@/pages/admissions/ApplicantStatus.vue') },
]

const router = createRouter({
  history: createWebHistory('/admissions'),
  routes,
})

export default router
