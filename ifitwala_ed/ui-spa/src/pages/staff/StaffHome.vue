<!-- ifitwala_ed/ui-spa/src/pages/staff/schedule/StaffHome.vue -->
<template>
	<div class="staff-shell space-y-6">
		<header class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
			<div>
				<h1 class="text-3xl font-bold tracking-tight text-heading sm:text-4xl">
					{{ greeting }}, <span class="text-leaf">{{ firstName }}</span>
				</h1>
			</div>

			<div class="flex items-center gap-3">
				<div class="flex items-center gap-2 text-lg font-medium text-slate/80">
					<FeatherIcon name="calendar" class="h-4 w-4 text-canopy" />
					<span>{{ todayLabel }}</span>
				</div>
			</div>
		</header>

		<ScheduleCalendar />

		<section class="grid grid-cols-1 gap-6 lg:grid-cols-12">
			<div class="flex flex-col gap-4 lg:col-span-8">
				<div class="flex items-center justify-between px-1">
					<h3 class="flex items-center gap-2 text-lg font-bold text-canopy">
						<FeatherIcon name="list" class="h-4 w-4 opacity-70" />
						Your Focus
					</h3>
					<span class="text-xs font-semibold uppercase tracking-wider text-slate-500">
						Pending Tasks
					</span>
				</div>

				<div class="overflow-hidden rounded-2xl border border-sand-300 bg-white/95 shadow-sm">
					<div class="bg-sand/20 p-8 text-center">
						<div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-leaf/10">
							<FeatherIcon name="coffee" class="h-6 w-6 text-leaf" />
						</div>
						<h4 class="text-base font-semibold text-canopy">
							All caught up!
						</h4>
						<p class="mx-auto mt-1 max-w-sm text-sm text-slate-600">
							Todo integration is landing soon. Tasks assigned to you (grading, approvals) will appear here.
						</p>
						<button
							type="button"
							class="mt-6 inline-flex items-center gap-2 rounded-lg border border-dashed border-leaf/40 px-4 py-2 text-sm font-medium text-leaf transition-colors hover:bg-leaf/5"
						>
							<FeatherIcon name="plus" class="h-4 w-4" />
							Add Personal Note
						</button>
					</div>

					<div
						class="group flex cursor-pointer items-start gap-4 border-t border-sand-200 bg-white px-6 py-4 transition-colors hover:bg-sky/20"
					>
						<div class="mt-1 h-5 w-5 rounded border-2 border-slate-300 transition-colors group-hover:border-jacaranda"></div>
						<div>
							<p class="text-sm font-medium text-ink transition-colors group-hover:text-jacaranda">
								Submit Semester Reports for Year 9
							</p>
							<div class="mt-1 flex items-center gap-3 text-xs text-slate-500">
								<span class="flex items-center gap-1 text-clay">
									<FeatherIcon name="alert-circle" class="h-3 w-3" /> Due Today
								</span>
								<span>•</span>
								<span>Academics</span>
							</div>
						</div>
					</div>
				</div>
			</div>

			<div class="flex flex-col gap-4 lg:col-span-4">
				<h3 class="px-1 text-lg font-bold text-canopy">
					Quick Actions
				</h3>

				<div class="grid gap-3">
					<RouterLink
						v-for="action in quickActions"
						:key="action.label"
						:to="action.to"
						class="group relative flex items-center gap-4 rounded-xl border border-border bg-white p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:border-jacaranda/30 hover:shadow-md"
					>
						<div
							class="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-sky text-canopy transition-colors group-hover:bg-jacaranda group-hover:text-white"
						>
							<FeatherIcon :name="action.icon" class="h-6 w-6" />
						</div>

						<div class="min-w-0 flex-1">
							<p class="font-bold text-ink transition-colors group-hover:text-jacaranda">
								{{ action.label }}
							</p>
							<p class="truncate text-xs text-slate-500">
								{{ action.caption }}
							</p>
						</div>

						<FeatherIcon name="chevron-right" class="h-4 w-4 text-slate-300 transition-colors group-hover:text-jacaranda" />
					</RouterLink>

					<a
						href="/app"
						class="group flex items-center gap-4 rounded-xl border border-dashed border-slate-300 p-4 transition-colors hover:bg-sand/30"
					>
						<div
							class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500 transition-colors group-hover:text-ink"
						>
							<FeatherIcon name="monitor" class="h-5 w-5" />
						</div>
						<div>
							<p class="text-sm font-semibold text-slate-600 transition-colors group-hover:text-ink">
								Switch to Desk
							</p>
							<p class="text-[10px] uppercase tracking-wider text-slate-400">
								Classic ERP View
							</p>
						</div>
					</a>
				</div>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';

import ScheduleCalendar from '@/components/calendar/ScheduleCalendar.vue';

// -----------------------------------------------------------------------------
// USER GREETING
// Fetch logged-in user via Frappe REST, then load User doc.
// -----------------------------------------------------------------------------

const userDoc = ref<any | null>(null);

onMounted(async () => {
	try {
		// 1) Who is logged in? (returns "Guest" or the user id)
		const whoRes = await fetch('/api/method/frappe.auth.get_logged_user', {
			credentials: 'include',
		});
		const whoJson = await whoRes.json();
		const userId = whoJson.message as string | undefined;

		if (!userId || userId === 'Guest') {
			console.warn('[StaffHome] Logged user is Guest or missing:', userId);
			return;
		}

		// 2) Fetch the full User document
		const userRes = await fetch(`/api/resource/User/${encodeURIComponent(userId)}`, {
			credentials: 'include',
		});
		const userJson = await userRes.json();

		// Frappe REST returns { data: { ...user fields... } }
		userDoc.value = userJson.data || null;

		// Debug: you should see this once on page load
		// eslint-disable-next-line no-console
		console.log('[StaffHome] Loaded user doc:', userDoc.value);
	} catch (error) {
		// eslint-disable-next-line no-console
		console.error('[StaffHome] Failed to load user doc:', error);
	}
});

const firstName = computed(() => {
	const doc = userDoc.value;
	if (!doc) return 'Staff';

	if (doc.first_name && typeof doc.first_name === 'string') {
		return doc.first_name;
	}
	if (doc.full_name && typeof doc.full_name === 'string') {
		return doc.full_name.split(' ')[0];
	}
	return 'Staff';
});

// -----------------------------------------------------------------------------
// QUICK ACTIONS
// -----------------------------------------------------------------------------

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
];

// -----------------------------------------------------------------------------
// TODAY LABEL + GREETING
// -----------------------------------------------------------------------------

const now = new Date();
const greeting = computed(() => {
	const hour = now.getHours();
	if (hour < 12) return 'Good morning';
	if (hour < 17) return 'Good afternoon';
	return 'Good evening';
});
const todayLabel = new Intl.DateTimeFormat(undefined, {
	weekday: 'long',
	month: 'long',
	day: 'numeric',
}).format(now);
</script>
