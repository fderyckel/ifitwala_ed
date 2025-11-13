<!-- ifitwala_ed/ifitwala_ed/ui-spa/src/pages/staff/schedule/StaffHome.vue -->
<template>
	<div class="space-y-10">
		<section class="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-blue-900 to-indigo-800 p-8 text-white shadow-xl">
			<div class="relative z-10 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
				<div>
					<p class="text-sm uppercase tracking-[0.35em] text-slate-300">Staff Portal</p>
					<h1 class="text-3xl font-semibold">
						Welcome back, <span class="text-sky-200">{{ staffName }}</span>
					</h1>
					<p class="mt-2 max-w-2xl text-base text-slate-200">
						Track your classes, meetings, and school events in one elegant calendar inspired by the best of ManageBac.
						Stay organised while keeping the Desk just one click away.
					</p>
				</div>

				<div class="grid gap-3 text-sm font-medium text-white sm:grid-cols-2">
					<RouterLink
						v-for="link in primaryLinks"
						:key="link.label"
						:to="link.to"
						class="group inline-flex items-center gap-2 rounded-2xl bg-white/5 px-4 py-3 text-left ring-1 ring-white/20 transition hover:bg-white/10"
					>
						<FeatherIcon :name="link.icon" class="h-5 w-5 text-sky-200 group-hover:text-white" />
						<div>
							<p class="text-xs uppercase tracking-wide text-slate-200">{{ link.meta }}</p>
							<p>{{ link.label }}</p>
						</div>
					</RouterLink>
				</div>
			</div>

			<div class="absolute -right-6 -top-6 h-48 w-48 rounded-full bg-white/10 blur-3xl"></div>
			<div class="absolute bottom-0 right-12 h-64 w-64 rounded-full bg-sky-500/10 blur-3xl"></div>
		</section>

		<section class="grid gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
			<ScheduleCalendar class="lg:col-span-1" />

			<aside class="space-y-6">
				<div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm">
					<p class="text-xs uppercase tracking-[0.3em] text-slate-400">Insights</p>
					<h3 class="mt-2 text-xl font-semibold text-slate-900">Today’s focus</h3>
					<p class="mt-2 text-sm text-slate-500">
						The calendar blends classes, meetings, and events. Toggle the chips above the calendar to zoom into one feed at a time.
						Data respects the system timezone, so your bells line up exactly with the school schedule.
					</p>
					<ul class="mt-4 space-y-3 text-sm text-slate-600">
						<li class="flex items-start gap-3">
							<FeatherIcon name="calendar" class="mt-0.5 h-4 w-4 text-blue-500" />
							<span>Classes pull their colour directly from the Course’s <code class="rounded bg-slate-100 px-1 text-xs">calendar_event_color</code>.</span>
						</li>
						<li class="flex items-start gap-3">
							<FeatherIcon name="users" class="mt-0.5 h-4 w-4 text-violet-500" />
							<span>Meetings inherit the hue of their Team’s meeting palette to stay consistent with the Desk.</span>
						</li>
						<li class="flex items-start gap-3">
							<FeatherIcon name="globe" class="mt-0.5 h-4 w-4 text-emerald-500" />
							<span>School and Frappe events respect participant lists, so staff only see what involves them.</span>
						</li>
					</ul>
				</div>

				<div class="rounded-3xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-6 shadow-sm">
					<p class="text-xs uppercase tracking-[0.3em] text-slate-400">Quick Actions</p>
					<div class="mt-4 space-y-4 text-sm">
						<RouterLink
							v-for="action in quickActions"
							:key="action.label"
							:to="action.to"
							class="group flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 transition hover:border-blue-400 hover:bg-white"
						>
							<div class="flex items-center gap-3">
								<div class="rounded-2xl bg-slate-100 p-2 text-slate-600 group-hover:bg-blue-50 group-hover:text-blue-600">
									<FeatherIcon :name="action.icon" class="h-5 w-5" />
								</div>
								<div>
									<p class="font-semibold text-slate-900">{{ action.label }}</p>
									<p class="text-xs text-slate-500">{{ action.caption }}</p>
								</div>
							</div>
							<FeatherIcon name="chevron-right" class="h-4 w-4 text-slate-300 group-hover:text-blue-600" />
						</RouterLink>
						<a
							href="/app"
							class="group flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 transition hover:border-slate-300"
						>
							<div class="flex items-center gap-3">
								<div class="rounded-2xl bg-slate-100 p-2 text-slate-600 group-hover:bg-slate-200">
									<FeatherIcon name="monitor" class="h-5 w-5" />
								</div>
								<div>
									<p class="font-semibold text-slate-900">Switch to Desk</p>
									<p class="text-xs text-slate-500">Open the classic ERP workspace</p>
								</div>
							</div>
							<FeatherIcon name="arrow-up-right" class="h-4 w-4 text-slate-300 group-hover:text-slate-500" />
						</a>
					</div>
				</div>
			</aside>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';

import ScheduleCalendar from '@/components/calendar/ScheduleCalendar.vue';

const staffName = computed(() => window.frappe?.session?.user_fullname || window.frappe?.session?.user || 'Staff');

const primaryLinks = [
	{ label: 'Student Groups', meta: 'Teaching', icon: 'layers', to: { name: 'staff-student-groups' } },
	{ label: 'Attendance Tool', meta: 'Daily check-ins', icon: 'check-square', to: { name: 'staff-attendance' } },
	{ label: 'Gradebook', meta: 'Assessments', icon: 'book-open', to: { name: 'staff-gradebook' } },
];

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
</script>
