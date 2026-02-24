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
				class="inline-flex items-center gap-2 rounded-full bg-jacaranda px-5 py-2.5 type-button-label text-white shadow-soft transition-transform hover:-translate-y-0.5 hover:shadow-strong"
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
				<h3 class="px-1 type-h3 text-canopy">Quick Actions</h3>

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
		<section v-if="hasVisibleAnalyticsLinks" class="rounded-2xl bg-surface shadow-soft">
			<div class="rounded-2xl border border-[rgb(var(--sand-rgb)/0.35)]">
				<div
					class="flex flex-col gap-4 border-b border-[rgb(var(--sand-rgb)/0.35)] px-6 pb-6 pt-7 sm:flex-row sm:items-center sm:justify-between"
				>
					<div class="space-y-2">
						<p class="type-overline text-slate-token/70">Analytics</p>
						<h3 class="type-h2">Insights & Dashboards</h3>
						<p class="max-w-2xl type-body text-slate-token/80">
							Jump straight into the dashboards you need. Start with the quick hitters, or browse
							by category when you are exploring trends.
						</p>
					</div>

					<RouterLink
						to="/analytics"
						target="_blank"
						rel="noopener"
						class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-ink shadow-sm transition hover:-translate-y-0.5 hover:border-jacaranda hover:text-jacaranda"
					>
						<FeatherIcon name="grid" class="h-4 w-4 text-slate-token/60" />
						<span>View all analytics</span>
					</RouterLink>
				</div>

				<div
					class="grid grid-cols-1 gap-3 border-b border-[rgb(var(--sand-rgb)/0.35)] px-6 py-6 lg:grid-cols-3"
				>
					<RouterLink
						v-for="link in visibleAnalyticsQuickLinks"
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
							class="rounded-full bg-jacaranda/20 px-2 py-0.5 type-badge-label text-jacaranda ring-1 ring-jacaranda/25"
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
						v-for="category in visibleAnalyticsCategories"
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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { FeatherIcon, toast } from 'frappe-ui';

import ScheduleCalendar from '@/components/calendar/ScheduleCalendar.vue';
import FocusListCard from '@/components/focus/FocusListCard.vue';
import { useOverlayStack } from '@/composables/useOverlayStack';
import {
	getStaffHomeHeader,
	listFocusItems,
	type StaffHomeHeader,
} from '@/lib/services/staff/staffHomeService';
import type { FocusItem } from '@/types/focusItem';
import {
	uiSignals,
	SIGNAL_FOCUS_INVALIDATE,
	SIGNAL_STUDENT_LOG_INVALIDATE,
} from '@/lib/uiSignals';

/**
 * StaffHome (A+ refresh ownership)
 * ------------------------------------------------------------
 * StaffHome owns:
 * - When Focus refreshes (policy: mount + interval + visibility + invalidation)
 * - How refresh is coalesced (dedupe + throttle to avoid stampedes)
 * - UX feedback after success when triggered by signal semantics
 *
 * StaffHome does NOT own:
 * - Workflow completion
 * - Closing overlays
 * - Emitting invalidation
 *
 * A+ refined UX rule:
 * - Services emit invalidate signals after confirmed success
 * - Refresh owners refetch and may optionally show “Saved” toast after refetch success
 * - Overlays close independently and do zero UX signaling
 */

/* USER --------------------------------------------------------- */
const userDoc = ref<StaffHomeHeader | null>(null);

onMounted(async () => {
	try {
		userDoc.value = await getStaffHomeHeader();
	} catch (err) {
		console.error('[StaffHome] Failed to load header:', err);
	}
});

const firstName = computed(() => {
	const doc = userDoc.value;
	if (!doc) return 'Staff';
	if (doc.first_name) return doc.first_name;
	if (doc.full_name) return doc.full_name.split(' ')[0];
	return 'Staff';
});

const userCapabilities = computed<Record<string, boolean>>(
	() => userDoc.value?.capabilities ?? {}
);

/* QUICK ACTIONS ------------------------------------------------ */
const quickActions = [
	{
		label: 'Update Gradebook',
		caption: 'Capture evidence, notes, and marks',
		icon: 'edit-3',
		to: { name: 'staff-gradebook' },
	},
	{
		label: 'Portfolio Review',
		caption: 'Review student evidence feed',
		icon: 'layers',
		to: { name: 'staff-portfolio' },
	},
];

/* FOCUS -------------------------------------------------------- */
const overlay = useOverlayStack();
const focusLoading = ref(false);
const focusItems = ref<FocusItem[]>([]);

/**
 * Refresh focus (deduped + lightly throttled)
 * - Avoid request stampedes (signals, visibility, interval can collide)
 * - Coalesce burst invalidations into a single refresh
 */
const lastFocusRefreshAt = ref<number>(0);
const refreshInFlight = ref<Promise<void> | null>(null);
let refreshQueued = false;
let refreshThrottleTimer: ReturnType<typeof setTimeout> | null = null;

const FOCUS_LIMIT = 8;
const FOCUS_REFRESH_THROTTLE_MS = 800; // coalesce burst triggers
const FOCUS_VISIBILITY_STALE_MS = 60_000; // align with likely server TTL
const FOCUS_POLL_MS = 120_000;

function markRefreshed() {
	lastFocusRefreshAt.value = Date.now();
}

function shouldRefreshOnVisibility() {
	return Date.now() - lastFocusRefreshAt.value > FOCUS_VISIBILITY_STALE_MS;
}

async function doRefreshFocus(_reason: string) {
	focusLoading.value = true;
	try {
		const items = await listFocusItems({ open_only: 1, limit: FOCUS_LIMIT, offset: 0 });
		focusItems.value = items;
		markRefreshed();
	} catch (err) {
		console.error('[StaffHome] Failed to load focus list:', err);
	} finally {
		focusLoading.value = false;
	}
}

function refreshFocus(reason: string) {
	// If one is in flight, queue exactly one extra run (coalesce).
	if (refreshInFlight.value) {
		refreshQueued = true;
		return refreshInFlight.value;
	}

	// Throttle bursts (signals can fire rapidly after workflows)
	if (refreshThrottleTimer) {
		refreshQueued = true;
		return refreshInFlight.value ?? Promise.resolve();
	}

	// Guard: in non-browser contexts, skip throttling and run immediately.
	if (typeof window === 'undefined') {
		refreshInFlight.value = (async () => {
			try {
				await doRefreshFocus(reason);
			} finally {
				refreshInFlight.value = null;
				if (refreshQueued) {
					refreshQueued = false;
					await refreshFocus('queued');
				}
			}
		})();
		return refreshInFlight.value;
	}

	refreshThrottleTimer = setTimeout(() => {
		refreshThrottleTimer = null;
		if (refreshQueued && !refreshInFlight.value) {
			refreshQueued = false;
			refreshFocus('coalesced');
		}
	}, FOCUS_REFRESH_THROTTLE_MS);

	refreshInFlight.value = (async () => {
		try {
			await doRefreshFocus(reason);
		} catch (e) {
			// doRefreshFocus already logs; keep this calm
		} finally {
			refreshInFlight.value = null;
			if (refreshQueued) {
				refreshQueued = false;
				// Run one more time immediately after a completed in-flight refresh
				await refreshFocus('queued');
			}
		}
	})();

	return refreshInFlight.value;
}

/**
 * Focus refresh policy (A+):
 * - On mount: load once
 * - Every 120s: light polling (tab-visible only)
 * - On tab refocus: refresh if stale
 * - On workflow completion: UI Services emit invalidation signals
 *   and StaffHome refreshes (coalesced)
 */
let focusTimer: ReturnType<typeof setInterval> | null = null;
let disposeFocusInvalidate: (() => void) | null = null;
let disposeStudentLogInvalidate: (() => void) | null = null;

// Local intent flag: only toast “Saved” when StaffHome initiated the workflow.
// Avoids global spam if student_log:invalidate is emitted from other surfaces.
const pendingStudentLogSavedToast = ref(false);

function onVisibilityChange() {
	if (document.visibilityState === 'visible' && shouldRefreshOnVisibility()) {
		refreshFocus('visibility');
	}
}

function onFocusInvalidated() {
	refreshFocus('signal:focus:invalidate');
}

function onStudentLogInvalidated() {
	const shouldToast = pendingStudentLogSavedToast.value;
	// Clear immediately so we never double-toast across coalesced runs.
	pendingStudentLogSavedToast.value = false;

	// Refresh what StaffHome owns (Focus). Then optionally toast after refetch success.
	refreshFocus('signal:student_log:invalidate')
		?.then(() => {
			if (shouldToast) {
				toast.create({
					title: 'Saved',
					text: 'Student note submitted.',
					icon: 'check',
				});
			}
		})
		.catch(() => {
			// If refresh fails, do not toast success.
		});
}

onMounted(async () => {
	// Initial load
	await refreshFocus('mount');

	// Poll (tab visible only)
	if (typeof window !== 'undefined') {
		focusTimer = setInterval(() => {
			if (document.visibilityState === 'visible') {
				refreshFocus('interval');
			}
		}, FOCUS_POLL_MS);
	}

	document.addEventListener('visibilitychange', onVisibilityChange);

	// A+ integration point: signals (subscribe returns disposer)
	disposeFocusInvalidate = uiSignals.subscribe(SIGNAL_FOCUS_INVALIDATE, onFocusInvalidated);
	disposeStudentLogInvalidate = uiSignals.subscribe(
		SIGNAL_STUDENT_LOG_INVALIDATE,
		onStudentLogInvalidated
	);
});

onBeforeUnmount(() => {
	if (focusTimer && typeof window !== 'undefined') window.clearInterval(focusTimer);
	document.removeEventListener('visibilitychange', onVisibilityChange);
	if (disposeFocusInvalidate) disposeFocusInvalidate();
	if (disposeStudentLogInvalidate) disposeStudentLogInvalidate();
});

function openFocusItem(item: FocusItem) {
	if (item.permissions?.can_open === false) {
		toast.create({
			title: 'Not available',
			text: 'You do not have access to open this item.',
			icon: 'info',
		});
		return;
	}

	overlay.open('focus-router', {
		focusItemId: item.id,
	});
}

/* ANALYTICS ---------------------------------------------------- */
type StaffHomeAnalyticsLink = {
	label: string;
	caption?: string;
	icon?: string;
	to: RouteLocationRaw;
	badge?: string;
	capability?: string;
};

type StaffHomeAnalyticsCategory = {
	title: string;
	description: string;
	icon: string;
	links: StaffHomeAnalyticsLink[];
};

const analyticsQuickLinks: StaffHomeAnalyticsLink[] = [
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
		capability: 'analytics_scheduling',
	},
];

const analyticsCategories: StaffHomeAnalyticsCategory[] = [
	{
		title: 'Enrollment & Census',
		description: 'Student body profile, admissions, and retention.',
		icon: 'trending-up',
		links: [
			{
				label: 'Demographics Overview',
				to: { name: 'student-demographic-analytics' },
				capability: 'analytics_demographics',
			},
			{
				label: 'Enrollment Analytics',
				to: { name: 'StaffEnrollmentAnalytics' },
				capability: 'analytics_admissions',
			},
		],
	},
	{
		title: 'Operations & Attendance',
		description: 'Coverage, punctuality, and daily health of the timetable.',
		icon: 'check-square',
		links: [
			{
				label: 'Attendance Analytics',
				to: { name: 'staff-attendance-analytics' },
				capability: 'analytics_attendance',
			},
			{
				label: 'Attendance Ledger',
				to: { name: 'staff-attendance-ledger' },
				capability: 'analytics_attendance',
			},
			{
				label: 'Late Arrivals',
				to: '/analytics/operations/late-arrivals',
				capability: 'analytics_attendance',
			},
			{
				label: 'Duty Coverage',
				to: '/analytics/operations/duty-coverage',
				capability: 'analytics_attendance_admin',
			},
		],
	},
	{
		title: 'Academic Performance',
		description: 'Grades, assessments, and intervention impact.',
		icon: 'book',
		links: [
			{
				label: 'Student Overview',
				to: { name: 'staff-student-overview' },
				capability: 'analytics_attendance',
			},
			{
				label: 'Assessment Trends',
				to: '/analytics/academic/assessment-trends',
				capability: 'analytics_attendance',
			},
		],
	},
	{
		title: 'Student Wellbeing',
		description: 'Referrals, caseloads, incidents, and follow-ups.',
		icon: 'heart',
		links: [
			{
				label: 'Student Log Analytics',
				to: { name: 'staff-student-log-analytics' },
				capability: 'analytics_wellbeing',
			},
			{
				label: 'Counseling Caseload',
				to: '/analytics/wellbeing/counseling-caseload',
				capability: 'analytics_wellbeing',
			},
		],
	},
	{
		title: 'Staff & HR',
		description: 'Availability, development, and evaluations.',
		icon: 'users',
		links: [
			{
				label: 'Organizational Chart',
				to: { name: 'staff-organization-chart' },
				capability: 'analytics_hr',
			},
			{ label: 'Leave Balance', to: '/analytics/staff/leave-balance', capability: 'analytics_hr' },
			{
				label: 'Training Progress',
				to: '/analytics/staff/training-progress',
				capability: 'analytics_hr',
			},
			{
				label: 'Evaluations Summary',
				to: '/analytics/staff/evaluations-summary',
				capability: 'analytics_hr',
			},
		],
	},
	{
		title: 'Scheduling & Capacity',
		description: 'Timetable load, rooms, and transport fill.',
		icon: 'calendar',
		links: [
			{
				label: 'Room Occupancy',
				to: { name: 'staff-room-utilization' },
				capability: 'analytics_scheduling',
			},
			{
				label: 'Bus & Route Load',
				to: '/analytics/scheduling/bus-route-load',
				capability: 'analytics_scheduling',
			},
		],
	},
	{
		title: 'Admission & Engagement',
		description: 'Family engagement, events, and surveys.',
		icon: 'message-circle',
		links: [
			{
				label: 'Admissions Cockpit',
				to: { name: 'staff-admission-cockpit' },
				capability: 'analytics_admissions',
			},
			{
				label: 'Inquiries Analytics',
				to: { name: 'staff-inquiry-analytics' },
				capability: 'analytics_admissions',
			},
			{
				label: 'Survey Results',
				to: '/analytics/engagement/survey-results',
				capability: 'analytics_admissions',
			},
		],
	},
	{
		title: 'Compliance & Risk',
		description: 'Safeguarding signals and audit readiness.',
		icon: 'shield',
		links: [
			{
				label: 'Audit Readiness',
				to: '/analytics/compliance/audit-readiness',
				capability: 'analytics_attendance_admin',
			},
			{
				label: 'Policy Acknowledgments',
				to: '/analytics/compliance/policy-acknowledgments',
				capability: 'analytics_attendance_admin',
			},
		],
	},
];

function isAnalyticsLinkVisible(link: StaffHomeAnalyticsLink) {
	if (!link.capability) return true;
	return Boolean(userCapabilities.value[link.capability]);
}

const visibleAnalyticsQuickLinks = computed(() =>
	analyticsQuickLinks.filter(isAnalyticsLinkVisible)
);
const visibleAnalyticsCategories = computed<StaffHomeAnalyticsCategory[]>(() =>
	analyticsCategories
		.map(category => ({
			...category,
			links: category.links.filter(isAnalyticsLinkVisible),
		}))
		.filter(category => category.links.length > 0)
);
const hasVisibleAnalyticsLinks = computed(
	() => visibleAnalyticsQuickLinks.value.length > 0 || visibleAnalyticsCategories.value.length > 0
);

/* GREETING ----------------------------------------------------- */
const greeting = computed(() => {
	const hour = new Date().getHours();
	return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
});

/* OVERLAY: Create Task ---------------------------------------- */
function openCreateTask() {
	overlay.open('create-task', {
		prefillStudentGroup: null,
		prefillDueDate: null,
		prefillAvailableFrom: null,
	});
}

/* OVERLAY: Student Log ---------------------------------------- */
function openStudentLog() {
	// Mark local intent for success feedback owned by this refresh owner.
	// Service will emit SIGNAL_STUDENT_LOG_INVALIDATE after confirmed success.
	// StaffHome will refetch and optionally toast after refetch success.
	pendingStudentLogSavedToast.value = true;

	overlay.open('student-log-create', {
		mode: 'school',
	});
}
</script>
