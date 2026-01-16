<!-- ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue -->
<template>
	<div class="staff-shell space-y-5">
		<!-- ============================================================
		     HEADER / GREETING
		     Intent:
		     - Lightweight “welcome” + one high-signal shortcut (Morning Brief)
		     - No data-heavy calls here (header is cached server-side)
		   ============================================================ -->
		<header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
			<div>
				<h1 class="type-h1">
					{{ greeting }},
					<span class="text-canopy">{{ firstName }}</span>
				</h1>
			</div>

			<!-- Morning Brief opens in a new tab by design (teacher keeps Home open) -->
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
		     Intent:
		     - Day-to-day anchor for staff
		     - Opens overlays via the global overlay stack (not local modals)
		   ============================================================ -->
		<ScheduleCalendar />

		<!-- ============================================================
		     TWO-COLUMN GRID
		     Intent:
		     - Left: “what needs attention” (Focus)
		     - Right: “what can I do quickly” (Quick Actions)
		   ============================================================ -->
		<section class="grid grid-cols-1 gap-10 lg:grid-cols-12">
			<!-- LEFT COL: TASKS / FOCUS -------------------------------->
			<div class="lg:col-span-8 space-y-4">
				<!-- Focus is a read-only attention surface, not a task manager -->
				<FocusListCard
					:items="focusItems"
					:loading="focusLoading"
					title="Your Focus"
					meta="Pending"
					empty-text="Nothing urgent right now."
					:max-items="8"
					@open="openFocusItem"
				/>
			</div>

			<!-- RIGHT COL: QUICK ACTIONS ------------------------------->
			<div class="lg:col-span-4 space-y-4">
				<h3 class="px-1 type-h3 text-canopy">
					Quick Actions
				</h3>

				<div class="grid gap-3">
					<!-- Create task uses overlay stack (single overlay system) -->
					<button type="button" class="action-tile group" @click="openCreateTask">
						<div class="action-tile__icon">
							<FeatherIcon name="clipboard" class="h-6 w-6" />
						</div>
						<div class="flex-1 min-w-0">
							<p class="type-body-strong text-ink transition-colors group-hover:text-jacaranda">
								Create task
							</p>
							<p class="truncate type-caption text-slate-token/70">
								Assign work to a class in seconds
							</p>
						</div>
						<FeatherIcon
							name="chevron-right"
							class="h-4 w-4 text-slate-token/40 transition-colors group-hover:text-jacaranda"
						/>
					</button>

					<!-- Create student log uses overlay stack -->
					<button type="button" class="action-tile group" @click="openStudentLog">
						<div class="action-tile__icon">
							<FeatherIcon name="edit-3" class="h-6 w-6" />
						</div>
						<div class="flex-1 min-w-0">
							<p class="type-body-strong text-ink transition-colors group-hover:text-jacaranda">
								Add student log
							</p>
							<p class="truncate type-caption text-slate-token/70">
								Record a note, concern, or follow-up
							</p>
						</div>
						<FeatherIcon
							name="chevron-right"
							class="h-4 w-4 text-slate-token/40 transition-colors group-hover:text-jacaranda"
						/>
					</button>

					<!-- Standard Quick Actions (router links, not overlays) -->
					<RouterLink
						v-for="action in quickActions"
						:key="action.label"
						:to="action.to"
						class="action-tile group"
					>
						<div class="action-tile__icon">
							<FeatherIcon :name="action.icon" class="h-6 w-6" />
						</div>

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
		     Intent:
		     - Keep it “browseable”: quick hits + category clusters
		     - Links open new tab by default (analytics browsing is a side-activity)
		     - No data fetching here (it’s link-only)
		   ============================================================ -->
		<section class="rounded-2xl bg-surface shadow-soft">
			<div class="rounded-2xl border border-[rgb(var(--sand-rgb)/0.35)]">
				<div
					class="flex flex-col gap-4 border-b border-[rgb(var(--sand-rgb)/0.35)] px-6 pb-6 pt-7 sm:flex-row sm:items-center sm:justify-between"
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

				<div
					class="grid grid-cols-1 gap-3 border-b border-[rgb(var(--sand-rgb)/0.35)] px-6 py-6 lg:grid-cols-3"
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
							class="rounded-full bg-jacaranda/20 px-2 py-0.5 type-badge-label text-jacaranda
								ring-1 ring-jacaranda/25"
						>
							{{ link.badge }}
						</span>

						<FeatherIcon
							name="arrow-up-right"
							class="h-4 w-4 shrink-0 text-slate-token/40 transition group-hover:text-jacaranda"
						/>
					</RouterLink>
				</div>

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
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { FeatherIcon, createResource, toast } from 'frappe-ui'

import ScheduleCalendar from '@/components/calendar/ScheduleCalendar.vue'
import FocusListCard from '@/components/focus/FocusListCard.vue'
import { useOverlayStack } from '@/composables/useOverlayStack'
import type { FocusItem } from '@/types/focusItem'
import { uiSignals, SIGNAL_FOCUS_INVALIDATE } from '@/lib/uiSignals'

/**
 * StaffHome (A+ refresh ownership)
 * ------------------------------------------------------------
 * StaffHome owns:
 * - When Focus refreshes (policy: mount + interval + visibility + invalidation)
 * - How refresh is coalesced (dedupe + throttle to avoid stampedes)
 *
 * StaffHome does NOT own:
 * - Workflow completion
 * - Closing overlays
 * - Emitting invalidation
 *
 * A+ contract:
 * - Workflows/services emit uiSignals (e.g. SIGNAL_FOCUS_INVALIDATE)
 * - Pages subscribe and refresh what they own
 * - Overlays close independently on success; refresh is not coupled to close
 *
 * This file must NOT rely on custom window events for SPA invalidation.
 * Window events are reserved only for explicit cross-runtime bridges (SPA ↔ Desk),
 * and must live in a dedicated bridge module (not in pages).
 */

/* USER --------------------------------------------------------- */
type StaffHomeHeader = {
	user: string
	first_name?: string | null
	full_name?: string | null
}

const userDoc = ref<StaffHomeHeader | null>(null)

const headerResource = createResource({
	url: 'ifitwala_ed.api.portal.get_staff_home_header',
	method: 'POST',
	auto: false,
	onSuccess(data: any) {
		const payload = data && typeof data === 'object' && 'message' in data ? data.message : data
		userDoc.value = (payload || null) as StaffHomeHeader | null
	},
	onError(err: any) {
		console.error('[StaffHome] Failed to load header:', err)
	},
})

onMounted(async () => {
	await headerResource.submit({})
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
		label: 'Update Gradebook',
		caption: 'Capture evidence, notes, and marks',
		icon: 'edit-3',
		to: { name: 'staff-gradebook' },
	},
]

/* FOCUS -------------------------------------------------------- */
const overlay = useOverlayStack()
const focusLoading = ref(false)
const focusItems = ref<FocusItem[]>([])

/**
 * Focus list resource:
 * - Single endpoint returning already-enriched FocusItem[]
 * - Keep limit small on StaffHome (8)
 */
const focusResource = createResource({
	url: 'ifitwala_ed.api.focus.list_focus_items',
	method: 'POST',
	auto: false,
	onSuccess(data: any) {
		const payload = data && typeof data === 'object' && 'message' in data ? data.message : data
		focusItems.value = Array.isArray(payload) ? (payload as FocusItem[]) : []
	},
	onError(err: any) {
		console.error('[StaffHome] Failed to load focus list:', err)
	},
})

/**
 * Refresh focus (deduped + lightly throttled)
 * - Avoid request stampedes (signals, visibility, interval can collide)
 * - Coalesce burst invalidations into a single refresh
 *
 * A+ note:
 * - uiSignals only triggers "something changed"
 * - StaffHome decides whether/when to refetch and how aggressively
 */
const lastFocusRefreshAt = ref<number>(0)
const refreshInFlight = ref<Promise<void> | null>(null)
let refreshQueued = false
let refreshThrottleTimer: number | null = null

const FOCUS_LIMIT = 8
const FOCUS_REFRESH_THROTTLE_MS = 800 // coalesce burst triggers
const FOCUS_VISIBILITY_STALE_MS = 60_000 // align with likely server TTL
const FOCUS_POLL_MS = 120_000

function markRefreshed() {
	lastFocusRefreshAt.value = Date.now()
}

function shouldRefreshOnVisibility() {
	return Date.now() - lastFocusRefreshAt.value > FOCUS_VISIBILITY_STALE_MS
}

async function doRefreshFocus(_reason: string) {
	focusLoading.value = true
	try {
		await focusResource.submit({ open_only: 1, limit: FOCUS_LIMIT, offset: 0 })
		markRefreshed()
	} finally {
		focusLoading.value = false
	}
}

function refreshFocus(reason: string) {
	// If one is in flight, queue exactly one extra run (coalesce).
	if (refreshInFlight.value) {
		refreshQueued = true
		return refreshInFlight.value
	}

	// Throttle bursts (signals can fire rapidly after workflows)
	if (refreshThrottleTimer) {
		refreshQueued = true
		return refreshInFlight.value ?? Promise.resolve()
	}

	refreshThrottleTimer = window.setTimeout(() => {
		refreshThrottleTimer = null
		if (refreshQueued && !refreshInFlight.value) {
			refreshQueued = false
			refreshFocus('coalesced')
		}
	}, FOCUS_REFRESH_THROTTLE_MS)

	refreshInFlight.value = (async () => {
		try {
			await doRefreshFocus(reason)
		} catch (e) {
			// focusResource.onError already logs; keep this calm
		} finally {
			refreshInFlight.value = null
			if (refreshQueued) {
				refreshQueued = false
				// Run one more time immediately after a completed in-flight refresh
				await refreshFocus('queued')
			}
		}
	})()

	return refreshInFlight.value
}

/**
 * Focus refresh policy (A+):
 * - On mount: load once
 * - Every 120s: light polling (tab-visible only)
 * - On tab refocus: refresh if stale
 * - On workflow completion: UI Services emit SIGNAL_FOCUS_INVALIDATE
 *   and StaffHome refreshes (coalesced)
 *
 * No custom window events for SPA invalidation.
 */
let focusTimer: number | null = null
let disposeFocusInvalidate: (() => void) | null = null

function onVisibilityChange() {
	if (document.visibilityState === 'visible' && shouldRefreshOnVisibility()) {
		refreshFocus('visibility')
	}
}

function onFocusInvalidated() {
	refreshFocus('signal:focus:invalidate')
}

onMounted(async () => {
	// Initial load
	await refreshFocus('mount')

	// Poll (tab visible only)
	focusTimer = window.setInterval(() => {
		if (document.visibilityState === 'visible') {
			refreshFocus('interval')
		}
	}, FOCUS_POLL_MS)

	document.addEventListener('visibilitychange', onVisibilityChange)

	// A+ integration point: signals (subscribe returns disposer)
	disposeFocusInvalidate = uiSignals.subscribe(SIGNAL_FOCUS_INVALIDATE, onFocusInvalidated)
})

onBeforeUnmount(() => {
	if (focusTimer) window.clearInterval(focusTimer)
	document.removeEventListener('visibilitychange', onVisibilityChange)
	if (disposeFocusInvalidate) disposeFocusInvalidate()
})

function openFocusItem(item: FocusItem) {
	if (item.permissions?.can_open === false) {
		toast({
			title: 'Not available',
			text: 'You do not have access to open this item.',
			icon: 'info',
		})
		return
	}

	overlay.open('focus-router', {
		focusItemId: item.id,
		referenceDoctype: item.reference_doctype,
		referenceName: item.reference_name,
		actionType: item.action_type,
	})
}

/* ANALYTICS ---------------------------------------------------- */
const analyticsQuickLinks = [
	{
		label: 'Annoucement Archive',
		caption: 'Check all current and past announcements',
		icon: 'activity',
		to: '/staff/announcements',
		badge: 'Hot',
	},
	{
		label: 'Room Utilization',
		caption: 'Which rooms are free, over or under-used this week',
		icon: 'clock',
		to: '/staff/room-utilization',
	},
]

const analyticsCategories = [
	{
		title: 'Enrollment & Census',
		description: 'Student body profile, admissions, and retention.',
		icon: 'trending-up',
		links: [
			{ label: 'Demographics Overview', to: { name: 'student-demographic-analytics' } },
			{ label: 'Enrollment Analytics', to: { name: 'StaffEnrollmentAnalytics' } },
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
			{ label: 'Student Overview', to: { name: 'staff-student-overview' } },
			{ label: 'Assessment Trends', to: '/analytics/academic/assessment-trends' },
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
			{ label: 'Organizational Chart', to: '/analytics/staff/staffing-levels' },
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
			{ label: 'Timetable Utilization', to: '../app/schedule_calendar' },
			{ label: 'Room Occupancy', to: { name: 'staff-room-utilization' } },
			{ label: 'Bus & Route Load', to: '/analytics/scheduling/bus-route-load' },
			{ label: 'Exam Schedules', to: '/analytics/scheduling/exam-schedules' },
		],
	},
	{
		title: 'Admission & Engagement',
		description: 'Family engagement, events, and surveys.',
		icon: 'message-circle',
		links: [
			{ label: 'Inquiries Analytics', to: { name: 'staff-inquiry-analytics' } },
			{ label: 'Survey Results', to: '/analytics/engagement/survey-results' },
		],
	},
	{
		title: 'Compliance & Risk',
		description: 'Safeguarding signals and audit readiness.',
		icon: 'shield',
		links: [
			{ label: 'Audit Readiness', to: '/analytics/compliance/audit-readiness' },
			{ label: 'Policy Acknowledgments', to: '/analytics/compliance/policy-acknowledgments' },
		],
	},
]

/* GREETING ----------------------------------------------------- */
const greeting = computed(() => {
	const hour = new Date().getHours()
	return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
})

/* OVERLAY: Create Task ---------------------------------------- */
function openCreateTask() {
	overlay.open('create-task', {
		prefillStudentGroup: null,
		prefillDueDate: null,
		prefillAvailableFrom: null,
	})
}

/* OVERLAY: Student Log ---------------------------------------- */
function openStudentLog() {
	overlay.open('student-log-create', {
		mode: 'school',
	})
}
</script>
