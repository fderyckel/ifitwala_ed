<!-- ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue -->
<template>
	<div class="staff-shell space-y-10">
		<!-- ============================================================
		     HEADER / GREETING
		   ============================================================ -->
		<header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
			<div>
				<h1 class="type-h1">
					{{ greeting }},
					<span class="text-canopy">{{ firstName }}</span>
				</h1>
			</div>

			<RouterLink
				:to="{ name: 'MorningBriefing' }"
				target="_blank"
				class="inline-flex items-center gap-2 rounded-full bg-jacaranda px-5 py-2.5 type-button-label text-white shadow-soft
					transition-transform hover:-translate-y-0.5 hover:shadow-strong"
			>
				<FeatherIcon name="sun" class="h-4 w-4 text-yellow-300" />
				<span>Morning Brief</span>
			</RouterLink>
		</header>

		<!-- ============================================================
		     CALENDAR
		   ============================================================ -->
		<ScheduleCalendar />

		<!-- ============================================================
		     TWO-COLUMN GRID
		   ============================================================ -->
		<section class="grid grid-cols-1 gap-10 lg:grid-cols-12">
			<!-- LEFT COL: TASKS / FOCUS -------------------------------->
			<div class="lg:col-span-8 space-y-4">
				<!-- Section Title -->
				<div class="flex items-center justify-between px-1">
					<h3 class="flex items-center gap-2 type-h3 text-canopy">
						<FeatherIcon name="list" class="h-4 w-4 opacity-70" />
						Your Focus
					</h3>
					<span class="type-overline">
						Pending Tasks
					</span>
				</div>

				<!-- Palette card wrapper -->
				<div class="palette-card overflow-hidden">
					<!-- Example tasks (replace with real later) -->
					<div
						class="group flex cursor-pointer items-start gap-4 border-b border-[rgb(var(--sand-rgb) / 0.4)]
							bg-white px-6 py-4 transition-colors hover:bg-sky/20 last:border-0"
					>
						<div
							class="mt-1 h-5 w-5 rounded border-2 border-slate-token/60 transition-colors group-hover:border-jacaranda"
						></div>

						<div class="flex-1">
							<p class="text-sm font-medium text-ink transition-colors group-hover:text-jacaranda">
								Submit Semester Reports for Year 9
							</p>
							<div class="mt-1 flex items-center gap-3 text-xs text-slate-token/70">
								<span class="flex items-center gap-1 text-flame font-medium">
									<FeatherIcon name="alert-circle" class="h-3 w-3" />
									Due Today
								</span>
								<span>•</span>
								<span>Academics</span>
							</div>
						</div>
					</div>

					<div
						class="group flex cursor-pointer items-start gap-4 bg-white px-6 py-4 transition-colors hover:bg-sky/20"
					>
						<div
							class="mt-1 h-5 w-5 rounded border-2 border-slate-token/60 transition-colors group-hover:border-jacaranda"
						></div>

						<div class="flex-1">
							<p class="text-sm font-medium text-ink transition-colors group-hover:text-jacaranda">
								Approve Field Trip: Grade 10 Science
							</p>
							<div class="mt-1 flex items-center gap-3 text-xs text-slate-token/70">
								<span>Tomorrow</span>
								<span>•</span>
								<span>Approval</span>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- RIGHT COL: QUICK ACTIONS ------------------------------->
			<div class="lg:col-span-4 space-y-4">
				<h3 class="px-1 type-h3 text-canopy">
					Quick Actions
				</h3>

				<div class="grid gap-3">
					<!-- Standard Quick Actions -->
					<RouterLink
						v-for="action in quickActions"
						:key="action.label"
						:to="action.to"
						class="action-tile group"
					>
						<!-- Icon container -->
						<div class="action-tile__icon">
							<FeatherIcon :name="action.icon" class="h-6 w-6" />
						</div>

						<!-- Text -->
						<div class="flex-1 min-w-0">
							<p class="type-body-strong text-ink transition-colors group-hover:text-jacaranda">
								{{ action.label }}
							</p>
							<p class="truncate type-caption text-slate-token/70">
								{{ action.caption }}
							</p>
						</div>

						<FeatherIcon
							name="chevron-right"
							class="h-4 w-4 text-slate-token/40 transition-colors group-hover:text-jacaranda"
						/>
					</RouterLink>
				</div>
			</div>
		</section>

		<!-- ============================================================
		     ANALYTICS HUB
		   ============================================================ -->
		<section
			class="rounded-2xl border border-[rgb(var(--sand-rgb) / 0.35)] bg-gradient-to-br from-white via-white to-slate-50 shadow-soft"
		>
			<!-- Header -->
			<div
				class="flex flex-col gap-4 border-b border-[rgb(var(--sand-rgb) / 0.35)] px-6 pb-6 pt-7 sm:flex-row sm:items-center sm:justify-between"
			>
				<div class="space-y-2">
					<p class="type-overline text-slate-token/70">
						Analytics
					</p>
					<h3 class="type-h2">
						Insights & Dashboards
					</h3>
					<p class="max-w-2xl type-body text-slate-token/80">
						Jump straight into the dashboards you need. Start with the quick hitters, or browse by
						category when you are exploring trends.
					</p>
				</div>

				<RouterLink
					to="/analytics"
					target="_blank"
					rel="noopener"
					class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-ink shadow-sm
						transition hover:-translate-y-0.5 hover:border-jacaranda hover:text-jacaranda"
				>
					<FeatherIcon name="grid" class="h-4 w-4 text-slate-token/60" />
					<span>View all analytics</span>
				</RouterLink>
			</div>

			<!-- Quick analytics -->
			<div
				class="grid grid-cols-1 gap-3 border-b border-[rgb(var(--sand-rgb) / 0.35)] px-6 py-6 lg:grid-cols-3"
			>
				<RouterLink
					v-for="link in analyticsQuickLinks"
					:key="link.label"
					:to="link.to"
					target="_blank"
					rel="noopener"
					class="group flex items-center gap-4 rounded-xl border border-slate-200 bg-white/90 px-4 py-3 shadow-sm transition-all hover:-translate-y-0.5 hover:border-jacaranda/70 hover:shadow-md"
				>
					<div
						class="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-slate-50 text-canopy ring-1 ring-slate-200 transition group-hover:bg-sky/20"
					>
						<FeatherIcon :name="link.icon" class="h-5 w-5" />
					</div>

					<div class="min-w-0 flex-1">
						<p class="type-body-strong text-ink transition-colors group-hover:text-jacaranda">
							{{ link.label }}
						</p>
						<p class="truncate type-caption text-slate-token/70">
							{{ link.caption }}
						</p>
					</div>

					<span
						v-if="link.badge"
						class="rounded-full bg-jacaranda/10 px-2 py-0.5 type-badge-label text-jacaranda"
					>
						{{ link.badge }}
					</span>

					<FeatherIcon
						name="arrow-up-right"
						class="h-4 w-4 shrink-0 text-slate-token/40 transition group-hover:text-jacaranda"
					/>
				</RouterLink>
			</div>

			<!-- Categories grid -->
			<div class="grid grid-cols-1 gap-4 px-6 py-6 md:grid-cols-2 xl:grid-cols-3">
				<div
					v-for="category in analyticsCategories"
					:key="category.title"
					class="group flex h-full flex-col rounded-xl border border-slate-200 bg-white/90 p-4 shadow-sm transition-all hover:-translate-y-1 hover:border-jacaranda/70 hover:shadow-md"
				>
					<div class="flex items-start justify-between gap-3">
						<div class="flex items-start gap-3">
							<div
								class="mt-0.5 flex h-10 w-10 items-center justify-center rounded-full bg-slate-50 text-canopy ring-1 ring-slate-200 transition group-hover:bg-sky/20"
							>
								<FeatherIcon :name="category.icon" class="h-5 w-5" />
							</div>
							<div class="space-y-1">
								<p class="type-overline text-slate-token/70">
									{{ category.title }}
								</p>
								<p class="type-meta text-slate-token/70">
									{{ category.description }}
								</p>
							</div>
						</div>
						<span
							class="rounded-full bg-slate-100 px-3 py-1 type-badge-label text-slate-token/70"
						>
							{{ category.links.length }} links
						</span>
					</div>

					<div class="mt-4 space-y-2">
						<RouterLink
							v-for="link in category.links"
							:key="link.label"
							:to="link.to"
							target="_blank"
							rel="noopener"
							class="group/link flex items-center justify-between rounded-lg px-3 py-2 transition-colors hover:bg-sky/15"
						>
							<span
								class="type-body-strong text-ink transition-colors group-hover/link:text-jacaranda"
							>
								{{ link.label }}
							</span>
							<FeatherIcon
								name="arrow-up-right"
								class="h-4 w-4 text-slate-token/40 transition group-hover/link:text-jacaranda"
							/>
						</RouterLink>
					</div>
				</div>
			</div>
		</section>
	</div>
</template>


<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { FeatherIcon } from 'frappe-ui'
import ScheduleCalendar from '@/components/calendar/ScheduleCalendar.vue'

/* USER --------------------------------------------------------- */
const userDoc = ref<any | null>(null)

onMounted(async () => {
  try {
    const whoRes = await fetch('/api/method/frappe.auth.get_logged_user', { credentials: 'include' })
    const whoJson = await whoRes.json()
    const userId = whoJson.message

    if (!userId || userId === 'Guest') return

    const userRes = await fetch(`/api/resource/User/${encodeURIComponent(userId)}`, {
      credentials: 'include',
    })
    const userJson = await userRes.json()
    userDoc.value = userJson.data || null
  } catch (err) {
    console.error('[StaffHome] Failed to load user doc:', err)
  }
})

const firstName = computed(() => {
  const doc = userDoc.value
  if (!doc) return 'Staff'
  if (doc.first_name) return doc.first_name
  if (doc.full_name) return doc.full_name.split(' ')[0]
  return 'Staff'
})

/* QUICK ACTIONS ------------------------------------------------ */
const quickActions = [
  {
    label: 'Plan Student Groups',
    caption: 'Manage rosters, rotation days & instructors',
    icon: 'layout',
    to: { name: 'staff-student-groups' },
  },
  {
    label: 'Take Attendance',
    caption: 'Record attendance for classes today',
    icon: 'check-square',
    to: { name: 'staff-attendance' },
  },
  {
    label: 'Update Gradebook',
    caption: 'Capture evidence, notes, and marks',
    icon: 'edit-3',
    to: { name: 'staff-gradebook' },
  },
]

/* ANALYTICS ---------------------------------------------------- */
const analyticsQuickLinks = [
  {
    label: 'Daily Attendance Pulse',
    caption: 'Morning attendance and late arrivals at a glance',
    icon: 'activity',
    to: '/analytics/operations/daily-attendance',
    badge: 'Hot',
  },
  {
    label: 'Grade Distribution',
    caption: 'Spot grade drift by course and cohort',
    icon: 'bar-chart-2',
    to: '/analytics/academic/grade-distribution',
  },
  {
    label: 'Room Utilization',
    caption: 'Which rooms are over or under-used this week',
    icon: 'clock',
    to: '/analytics/scheduling/room-utilization',
  },
]

const analyticsCategories = [
	{
    title: 'Enrollment & Census',
    description: 'Student body profile, admissions, and retention.',
    icon: 'id-card',
    links: [
      { label: 'Demographics Overview', to: { name: 'student-demographics' } },
      { label: 'Enrollment Trends', to: '/analytics/enrollment/enrollment-trends' },
      { label: 'Admissions Funnel', to: '/analytics/enrollment/admissions-funnel' },
      { label: 'Student Churn/Withdrawal', to: '/analytics/enrollment/churn-rates' },
    ],
  },
  {
    title: 'Operations & Attendance',
    description: 'Coverage, punctuality, and daily health of the timetable.',
    icon: 'check-square',
    links: [
      { label: 'Daily Attendance', to: '/analytics/operations/daily-attendance' },
      { label: 'Absence Trends', to: '/analytics/operations/absence-trends' },
      { label: 'Late Arrivals', to: '/analytics/operations/late-arrivals' },
      { label: 'Duty Coverage', to: '/analytics/operations/duty-coverage' },
    ],
  },
  {
    title: 'Academic Performance',
    description: 'Grades, assessments, and intervention impact.',
    icon: 'book',
    links: [
      { label: 'Grade Distribution', to: '/analytics/academic/grade-distribution' },
      { label: 'Assessment Trends', to: '/analytics/academic/assessment-trends' },
      { label: 'Course Completion', to: '/analytics/academic/course-completion' },
      { label: 'Intervention Impact', to: '/analytics/academic/intervention-impact' },
    ],
  },
  {
    title: 'Student Wellbeing',
    description: 'Referrals, caseloads, incidents, and follow-ups.',
    icon: 'heart',
    links: [
      { label: 'Student Log Analytics', to: { name: 'staff-student-log-analytics' } },
      { label: 'Counseling Caseload', to: '/analytics/wellbeing/counseling-caseload' },
      { label: 'Referral Outcomes', to: '/analytics/wellbeing/referral-outcomes' },
      { label: 'Support Plans', to: '/analytics/wellbeing/support-plans' },
    ],
  },
  {
    title: 'Staff & HR',
    description: 'Availability, development, and evaluations.',
    icon: 'users',
    links: [
      { label: 'Staffing Levels', to: '/analytics/staff/staffing-levels' },
      { label: 'Leave Balance', to: '/analytics/staff/leave-balance' },
      { label: 'Training Progress', to: '/analytics/staff/training-progress' },
      { label: 'Evaluations Summary', to: '/analytics/staff/evaluations-summary' },
    ],
  },
  {
    title: 'Scheduling & Capacity',
    description: 'Timetable load, rooms, and transport fill.',
    icon: 'calendar',
    links: [
      { label: 'Timetable Utilization', to: '/analytics/scheduling/timetable-utilization' },
      { label: 'Room Occupancy', to: '/analytics/scheduling/room-occupancy' },
      { label: 'Bus & Route Load', to: '/analytics/scheduling/bus-route-load' },
      { label: 'Exam Schedules', to: '/analytics/scheduling/exam-schedules' },
    ],
  },
  {
    title: 'Engagement & Communication',
    description: 'Family engagement, events, and surveys.',
    icon: 'message-circle',
    links: [
      { label: 'Portal Usage', to: '/analytics/engagement/portal-usage' },
      { label: 'Message Open Rates', to: '/analytics/engagement/message-open-rates' },
      { label: 'Event Participation', to: '/analytics/engagement/event-participation' },
      { label: 'Survey Results', to: '/analytics/engagement/survey-results' },
    ],
  },
  {
    title: 'Compliance & Risk',
    description: 'Safeguarding signals and audit readiness.',
    icon: 'shield',
    links: [
      { label: 'Safeguarding Alerts', to: '/analytics/compliance/safeguarding-alerts' },
      { label: 'Audit Readiness', to: '/analytics/compliance/audit-readiness' },
      { label: 'Policy Acknowledgments', to: '/analytics/compliance/policy-acknowledgments' },
      { label: 'Access Logs', to: '/analytics/compliance/access-logs' },
    ],
  },
]

/* GREETING ----------------------------------------------------- */
const now = new Date()
const greeting = computed(() => {
  const hour = now.getHours()
  return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
})
</script>
