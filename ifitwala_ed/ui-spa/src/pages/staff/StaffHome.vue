<!-- ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue -->
<template>
	<div data-testid="staff-home-page" class="staff-shell space-y-5">
		<!-- ============================================================
		     HEADER / GREETING
		     Intent:
		     - Lightweight “welcome” + one high-signal shortcut (Morning Brief)
		     - No data-heavy calls here (header is cached server-side)
		   ============================================================ -->
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-ink">
					{{ greeting }},
					<span class="text-canopy">{{ firstName }}</span>
				</h1>
			</div>

			<!-- Morning Brief opens in a new tab by design (teacher keeps Home open) -->
			<div class="page-header__actions">
				<RouterLink
					:to="{ name: 'MorningBriefing' }"
					target="_blank"
					class="if-button if-button--primary"
				>
					<FeatherIcon name="sun" class="h-4 w-4 text-yellow-300" />
					<span>Morning Brief</span>
				</RouterLink>
			</div>
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
		<section class="staff-home__primary-grid">
			<!-- LEFT COL: TASKS / FOCUS -------------------------------->
			<div class="staff-home__focus-column min-w-0 space-y-4">
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
			<div class="staff-home__actions-column min-w-0 space-y-4 xl:sticky xl:top-6">
				<h3 class="px-1 type-h3 text-canopy">Quick Actions</h3>

				<div data-testid="staff-home-quick-actions" class="grid min-w-0 gap-3">
					<button
						v-if="userCapabilities.quick_action_class_hub"
						type="button"
						class="action-tile group w-full min-w-0 disabled:cursor-not-allowed disabled:opacity-70"
						:disabled="classHubQuickActionLoading"
						@click="openClassHubQuickAction"
					>
						<div class="action-tile__icon shrink-0">
							<FeatherIcon name="book-open" class="h-6 w-6" />
						</div>
						<div class="flex-1 min-w-0">
							<p class="type-body-strong text-ink transition-colors group-hover:text-jacaranda">
								Open Class Hub
							</p>
							<p class="truncate type-caption text-slate-token/70">
								{{
									classHubQuickActionLoading
										? 'Checking your teaching groups'
										: 'Choose one of your teaching groups and open the class workspace'
								}}
							</p>
						</div>
						<FeatherIcon
							name="chevron-right"
							class="h-4 w-4 shrink-0 text-slate-token/40 transition-colors group-hover:text-jacaranda"
						/>
					</button>

					<!-- Create student log uses overlay stack -->
					<button
						v-if="userCapabilities.quick_action_create_event"
						type="button"
						class="action-tile group w-full min-w-0"
						@click="openCreateEvent"
					>
						<div class="action-tile__icon shrink-0">
							<FeatherIcon name="calendar" class="h-6 w-6" />
						</div>
						<div class="flex-1 min-w-0">
							<p class="type-body-strong text-ink transition-colors group-hover:text-jacaranda">
								{{ eventQuickActionTitle }}
							</p>
							<p class="truncate type-caption text-slate-token/70">
								{{ eventQuickActionSubtitle }}
							</p>
						</div>
						<FeatherIcon
							name="chevron-right"
							class="h-4 w-4 shrink-0 text-slate-token/40 transition-colors group-hover:text-jacaranda"
						/>
					</button>

					<!-- Create student log uses overlay stack -->
					<button
						v-if="userCapabilities.quick_action_student_log"
						type="button"
						class="action-tile group w-full min-w-0"
						@click="openStudentLog"
					>
						<div class="action-tile__icon shrink-0">
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
							class="h-4 w-4 shrink-0 text-slate-token/40 transition-colors group-hover:text-jacaranda"
						/>
					</button>

					<button
						v-if="showOrgCommunicationQuickAction"
						type="button"
						class="action-tile group w-full min-w-0 disabled:cursor-not-allowed disabled:opacity-70"
						:disabled="!orgCommunicationQuickActionState.enabled"
						@click="openOrgCommunication"
					>
						<div class="action-tile__icon shrink-0">
							<FeatherIcon name="send" class="h-6 w-6" />
						</div>
						<div class="flex-1 min-w-0">
							<p class="type-body-strong text-ink transition-colors group-hover:text-jacaranda">
								Create communication
							</p>
							<p
								class="type-caption text-slate-token/70"
								:class="orgCommunicationQuickActionState.blocked_reason ? '' : 'truncate'"
							>
								{{ orgCommunicationQuickActionSubtitle }}
							</p>
						</div>
						<FeatherIcon
							name="chevron-right"
							class="h-4 w-4 shrink-0 text-slate-token/40 transition-colors group-hover:text-jacaranda"
						/>
					</button>

					<p
						v-if="!hasVisibleQuickActions"
						class="rounded-xl border border-dashed border-slate-300 bg-slate-50/70 px-4 py-3 type-caption text-slate-token/80"
					>
						No quick actions are assigned to your current role.
					</p>
				</div>
			</div>
		</section>

		<!-- ============================================================
		     EXPLORE HUB
		     Intent:
		     - Keep secondary destinations browseable without polluting the main action rail
		     - Start with high-value workspaces and records, then fan into analytics categories
		     - No data fetching here (it’s link-only)
		   ============================================================ -->
		<section v-if="hasVisibleAnalyticsLinks" class="rounded-2xl bg-surface shadow-soft">
			<div class="rounded-2xl border border-[rgb(var(--sand-rgb)/0.35)]">
				<div class="border-b border-[rgb(var(--sand-rgb)/0.35)] px-6 pb-6 pt-7">
					<div class="space-y-2">
						<p class="type-overline text-slate-token/70">Analytics</p>
						<h3 class="type-h2">Insights & Dashboards</h3>
					</div>
				</div>

				<div
					data-testid="staff-home-explore-links"
					class="staff-home__analytics-quick-links border-b border-[rgb(var(--sand-rgb)/0.35)] px-6 py-6"
				>
					<template v-for="link in visibleExploreLinks" :key="link.label">
						<button
							v-if="link.kind === 'action'"
							type="button"
							class="group flex w-full items-center gap-4 rounded-xl border border-slate-200 bg-white/90 px-4 py-3 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-jacaranda/70 hover:shadow-md"
							@click="link.action?.()"
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
								name="chevron-right"
								class="h-4 w-4 shrink-0 text-slate-token/40 transition group-hover:text-jacaranda"
							/>
						</button>

						<RouterLink
							v-else
							:to="link.to"
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
								name="chevron-right"
								class="h-4 w-4 shrink-0 text-slate-token/40 transition group-hover:text-jacaranda"
							/>
						</RouterLink>
					</template>
				</div>

				<div class="staff-home__analytics-category-grid px-6 py-6">
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
import { RouterLink, useRouter, type RouteLocationRaw } from 'vue-router';
import { FeatherIcon, toast } from 'frappe-ui';

import ScheduleCalendar from '@/components/calendar/ScheduleCalendar.vue';
import FocusListCard from '@/components/focus/FocusListCard.vue';
import { useOverlayStack } from '@/composables/useOverlayStack';
import { createClassHubService } from '@/lib/classHubService';
import {
	getStaffHomeHeader,
	type StaffHomeQuickActionState,
	listFocusItems,
	type StaffHomeHeader,
} from '@/lib/services/staff/staffHomeService';
import type { FocusItem } from '@/types/focusItem';
import {
	uiSignals,
	SIGNAL_FOCUS_INVALIDATE,
	SIGNAL_ORG_COMMUNICATION_INVALIDATE,
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
const router = useRouter();
const classHubService = createClassHubService();
const classHubQuickActionLoading = ref(false);

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

const orgCommunicationQuickActionState = computed<StaffHomeQuickActionState>(() => ({
	enabled:
		userDoc.value?.quick_actions?.org_communication?.enabled ??
		Boolean(userCapabilities.value.quick_action_org_communication),
	blocked_reason: userDoc.value?.quick_actions?.org_communication?.blocked_reason ?? null,
}));

const showOrgCommunicationQuickAction = computed(
	() =>
		Boolean(userCapabilities.value.quick_action_org_communication) ||
		Boolean(orgCommunicationQuickActionState.value.blocked_reason)
);

const orgCommunicationQuickActionSubtitle = computed(
	() =>
		orgCommunicationQuickActionState.value.blocked_reason ||
		'Publish to staff, a student group, or your wider school community'
);

/* QUICK ACTIONS ------------------------------------------------ */
const hasVisibleQuickActions = computed(
	() =>
		Boolean(userCapabilities.value.quick_action_class_hub) ||
		Boolean(userCapabilities.value.quick_action_create_event) ||
		Boolean(userCapabilities.value.quick_action_student_log) ||
		showOrgCommunicationQuickAction.value
);

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
let disposeOrgCommunicationInvalidate: (() => void) | null = null;

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

function onOrgCommunicationInvalidated(payload?: { reason?: string }) {
	if (payload?.reason !== 'quick_create') return;

	toast.create({
		title: 'Communication created',
		text: 'Your communication is ready on the relevant announcement surfaces.',
		icon: 'check',
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
	disposeOrgCommunicationInvalidate = uiSignals.subscribe(
		SIGNAL_ORG_COMMUNICATION_INVALIDATE,
		onOrgCommunicationInvalidated
	);
});

onBeforeUnmount(() => {
	if (focusTimer && typeof window !== 'undefined') window.clearInterval(focusTimer);
	document.removeEventListener('visibilitychange', onVisibilityChange);
	if (disposeFocusInvalidate) disposeFocusInvalidate();
	if (disposeStudentLogInvalidate) disposeStudentLogInvalidate();
	if (disposeOrgCommunicationInvalidate) disposeOrgCommunicationInvalidate();
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
	kind?: 'route';
	label: string;
	caption?: string;
	icon?: string;
	to: RouteLocationRaw;
	badge?: string;
	capability?: string;
};

type StaffHomeExploreAction = {
	kind: 'action';
	label: string;
	caption?: string;
	icon?: string;
	badge?: string;
	capability?: string;
	action: () => void;
};

type StaffHomeAnalyticsCategory = {
	title: string;
	description: string;
	icon: string;
	links: StaffHomeAnalyticsLink[];
};

const exploreLinks: Array<StaffHomeAnalyticsLink | StaffHomeExploreAction> = [
	{
		kind: 'route',
		label: 'Announcement Archive',
		caption: 'Check all current and past announcements',
		icon: 'activity',
		to: '/staff/announcements',
		badge: 'Hot',
	},
	{
		kind: 'action',
		label: 'Create task',
		caption: 'Assign work to a class in seconds',
		icon: 'clipboard',
		capability: 'quick_action_create_task',
		action: openCreateTask,
	},
	{
		kind: 'route',
		label: 'Update Gradebook',
		caption: 'Capture evidence, notes, and marks',
		icon: 'edit-3',
		to: { name: 'staff-gradebook' },
		capability: 'quick_action_gradebook',
	},
	{
		kind: 'route',
		label: 'Course Plans',
		caption: 'Open the governed curriculum backbone and shared resources',
		icon: 'layers',
		to: { name: 'staff-course-plan-index' },
	},
	{
		kind: 'route',
		label: 'Room Utilization',
		caption: 'Which rooms are free, over or under-used this week',
		icon: 'clock',
		to: '/staff/room-utilization',
		capability: 'room_utilization_page',
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
				capability: 'analytics_student_overview',
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
			},
			{
				label: 'My Growth',
				to: { name: 'staff-professional-development' },
				capability: 'staff_professional_development',
			},
		],
	},
	{
		title: 'Scheduling & Capacity',
		description: 'Timetable load, rooms, and transport fill.',
		icon: 'calendar',
		links: [
			{
				label: 'Academic Load',
				to: { name: 'staff-academic-load' },
				capability: 'analytics_academic_load',
			},
			{
				label: 'Room Occupancy',
				to: { name: 'staff-room-utilization' },
				capability: 'room_utilization_page',
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
		],
	},
	{
		title: 'Compliance & Risk',
		description: 'Safeguarding signals and audit readiness.',
		icon: 'shield',
		links: [
			{
				label: 'Policy Acknowledgments',
				to: { name: 'staff-policy-signature-analytics' },
				capability: 'analytics_policy_signatures',
			},
			{
				label: 'Forms & Signatures',
				to: { name: 'staff-forms-signatures-analytics' },
				capability: 'analytics_policy_signatures',
			},
			{
				label: 'Policy Library',
				to: { name: 'staff-policies' },
				capability: 'staff_policy_library',
			},
		],
	},
];

function isAnalyticsLinkVisible(link: StaffHomeAnalyticsLink) {
	if (!link.capability) return true;
	return Boolean(userCapabilities.value[link.capability]);
}

function isExploreLinkVisible(link: StaffHomeAnalyticsLink | StaffHomeExploreAction) {
	if (!link.capability) return true;
	return Boolean(userCapabilities.value[link.capability]);
}

const visibleExploreLinks = computed(() => exploreLinks.filter(isExploreLinkVisible));
const visibleAnalyticsCategories = computed<StaffHomeAnalyticsCategory[]>(() =>
	analyticsCategories
		.map(category => ({
			...category,
			links: category.links.filter(isAnalyticsLinkVisible),
		}))
		.filter(category => category.links.length > 0)
);
const hasVisibleAnalyticsLinks = computed(
	() => visibleExploreLinks.value.length > 0 || visibleAnalyticsCategories.value.length > 0
);

/* GREETING ----------------------------------------------------- */
const greeting = computed(() => {
	const hour = new Date().getHours();
	return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
});

const canCreateMeeting = computed(() =>
	Boolean(userCapabilities.value.quick_action_create_meeting)
);
const canCreateSchoolEvent = computed(() =>
	Boolean(userCapabilities.value.quick_action_create_school_event)
);
const eventQuickActionTitle = computed(() => {
	if (canCreateMeeting.value && !canCreateSchoolEvent.value) return 'Schedule meeting';
	return 'Create event';
});

const eventQuickActionSubtitle = computed(() => {
	if (canCreateMeeting.value && !canCreateSchoolEvent.value) {
		return 'Find a common time and invite colleagues, students, or guardians';
	}
	return 'Create a meeting or school event';
});

/* OVERLAY: Create Task ---------------------------------------- */
function openCreateTask() {
	overlay.open('create-task', {
		prefillStudentGroup: null,
		prefillDueDate: null,
		prefillAvailableFrom: null,
	});
}

async function openClassHubQuickAction() {
	if (!userCapabilities.value.quick_action_class_hub || classHubQuickActionLoading.value) return;

	classHubQuickActionLoading.value = true;
	try {
		const payload = await classHubService.resolveStaffHomeEntry();
		const groups = Array.isArray(payload.groups) ? payload.groups : [];

		if (payload.status === 'single' && groups.length === 1) {
			await router.push({
				name: 'ClassHub',
				params: { studentGroup: groups[0].student_group },
			});
			return;
		}

		overlay.open('class-hub-group-picker', {
			source_label: 'Staff Home',
			groups,
			message: payload.message ?? null,
		});
	} catch (err) {
		console.error('[StaffHome] Failed to resolve Class Hub quick action:', err);
		toast.create({
			title: 'Could not open Class Hub',
			text: 'Try again in a moment.',
			icon: 'info',
		});
	} finally {
		classHubQuickActionLoading.value = false;
	}
}

/* OVERLAY: Event Quick Create --------------------------------- */
function openCreateEvent() {
	if (!canCreateMeeting.value && !canCreateSchoolEvent.value) {
		toast.create({
			title: 'Not available',
			text: 'You do not have permission to create events.',
			icon: 'info',
		});
		return;
	}

	const lockEventType = canCreateMeeting.value !== canCreateSchoolEvent.value;
	const eventType = canCreateMeeting.value ? 'meeting' : 'school_event';

	overlay.open('event-quick-create', {
		eventType: lockEventType ? eventType : null,
		lockEventType,
		meetingMode: 'ad_hoc',
	});
}

/* OVERLAY: Student Log ---------------------------------------- */
function openStudentLog() {
	// Mark local intent for success feedback owned by this refresh owner.
	// Service will emit SIGNAL_STUDENT_LOG_INVALIDATE after confirmed success.
	// StaffHome will refetch and optionally toast after refetch success.
	pendingStudentLogSavedToast.value = true;

	overlay.open('student-log-create', {
		mode: 'home',
		sourceLabel: 'Staff Home',
	});
}

function openOrgCommunication() {
	if (!orgCommunicationQuickActionState.value.enabled) {
		toast.create({
			title: 'Communication unavailable',
			text:
				orgCommunicationQuickActionState.value.blocked_reason ||
				'You cannot create communications from Staff Home right now.',
			icon: 'info',
		});
		return;
	}

	overlay.open('org-communication-quick-create', {
		entryMode: 'staff-home',
		sourceLabel: 'Staff Home',
	});
}
</script>

<style scoped>
.staff-home__primary-grid {
	display: grid;
	grid-template-columns: minmax(0, 1fr);
	gap: 1.5rem;
	align-items: start;
}

.staff-home__analytics-quick-links {
	display: grid;
	grid-template-columns: minmax(0, 1fr);
	gap: 1rem;
}

.staff-home__analytics-category-grid {
	display: grid;
	grid-template-columns: minmax(0, 1fr);
	gap: 1rem;
}

@media (min-width: 1024px) {
	.staff-home__primary-grid {
		grid-template-columns: minmax(0, 1.9fr) minmax(21rem, 1fr);
		gap: 2rem;
	}

	.staff-home__analytics-quick-links {
		grid-template-columns: repeat(3, minmax(0, 1fr));
	}

	.staff-home__analytics-category-grid {
		grid-template-columns: repeat(3, minmax(0, 1fr));
	}
}

@media (min-width: 768px) and (max-width: 1023px) {
	.staff-home__analytics-quick-links {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}

	.staff-home__analytics-category-grid {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
}
</style>
