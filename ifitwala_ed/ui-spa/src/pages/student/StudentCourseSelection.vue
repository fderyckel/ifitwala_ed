<!-- ifitwala_ed/ui-spa/src/pages/student/StudentCourseSelection.vue -->
<template>
	<div class="space-y-6">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">Student Course Selection</p>
					<h1 class="type-h1 text-ink">Build Your Academic Basket</h1>
					<p class="type-body text-ink/70">
						Required courses stay locked. Use this space to confirm your language, electives, and
						other program choices before the deadline.
					</p>
				</div>
				<div class="flex items-center gap-2">
					<RouterLink class="if-action" :to="{ name: 'student-home' }">Back to Home</RouterLink>
					<button type="button" class="if-action" :disabled="loading" @click="loadBoard">
						Refresh
					</button>
				</div>
			</div>
		</header>

		<section class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Open windows</p>
				<p class="mini-kpi-value">{{ openWindowCount }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Pending</p>
				<p class="mini-kpi-value">{{ pendingCount }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Submitted</p>
				<p class="mini-kpi-value">{{ submittedCount }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Due soon</p>
				<p class="mini-kpi-value">{{ dueSoonCount }}</p>
			</article>
		</section>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading course selection windows...</p>
		</section>
		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">Could not load course selection.</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<template v-else>
			<section v-if="!windows.length" class="card-surface p-5">
				<h2 class="type-h3 text-ink">No active selection windows</h2>
				<p class="mt-2 type-body text-ink/70">
					When your school opens program choices, the requests will appear here with one-click
					access to the detail view.
				</p>
			</section>

			<section v-else class="space-y-4">
				<article v-for="window in windows" :key="window.selection_window" class="card-surface p-5">
					<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
						<div>
							<p class="type-overline text-ink/60">{{ window.program_label }}</p>
							<h2 class="type-h3 text-ink">{{ window.title }}</h2>
							<p class="mt-1 type-body text-ink/70">
								{{ window.school_label }} · {{ window.academic_year }}
							</p>
							<p v-if="window.instructions" class="mt-3 type-caption text-ink/70">
								{{ window.instructions }}
							</p>
						</div>
						<div class="flex flex-wrap items-center gap-2">
							<span class="chip">{{ window.status }}</span>
							<span class="chip">{{ dueLabel(window.due_on) }}</span>
						</div>
					</div>

					<div class="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1fr),240px]">
						<div class="rounded-2xl border border-line-soft bg-surface-soft p-4">
							<p class="type-body-strong text-ink">{{ requestSummary(window) }}</p>
							<p
								v-if="window.students[0]?.request?.locked_reason"
								class="mt-2 type-caption text-ink/70"
							>
								{{ window.students[0].request?.locked_reason }}
							</p>
						</div>
						<RouterLink
							:to="{
								name: 'student-course-selection-detail',
								params: { selection_window: window.selection_window },
							}"
							class="action-tile group"
						>
							<div class="action-tile__icon">
								<FeatherIcon name="edit-3" class="h-5 w-5" />
							</div>
							<div class="min-w-0 flex-1">
								<p class="type-body-strong text-ink transition-colors group-hover:text-jacaranda">
									{{
										window.students[0]?.request?.can_edit ? 'Continue Selection' : 'View Selection'
									}}
								</p>
								<p class="truncate type-caption text-ink/70">
									Open the full request and review every course row.
								</p>
							</div>
							<FeatherIcon name="chevron-right" class="h-4 w-4 text-ink/40" />
						</RouterLink>
					</div>
				</article>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';

import { __ } from '@/lib/i18n';
import { getSelfEnrollmentPortalBoard } from '@/lib/services/selfEnrollment/selfEnrollmentService';
import type {
	PortalSelectionWindow,
	Response as PortalBoardResponse,
} from '@/types/contracts/self_enrollment/get_self_enrollment_portal_board';

const loading = ref<boolean>(true);
const errorMessage = ref<string>('');
const board = ref<PortalBoardResponse | null>(null);

const windows = computed<PortalSelectionWindow[]>(() => board.value?.windows || []);
const openWindowCount = computed(
	() => windows.value.filter(window => window.is_open_now === 1).length
);
const pendingCount = computed(() =>
	windows.value.reduce((total, window) => total + window.summary.pending_count, 0)
);
const submittedCount = computed(() =>
	windows.value.reduce((total, window) => total + window.summary.submitted_count, 0)
);
const dueSoonCount = computed(
	() =>
		windows.value.filter(window => {
			if (!window.due_on) return false;
			const due = new Date(window.due_on).getTime();
			if (Number.isNaN(due)) return false;
			const delta = due - Date.now();
			return delta >= 0 && delta <= 1000 * 60 * 60 * 24 * 7;
		}).length
);

function dueLabel(value?: string | null) {
	if (!value) return __('No deadline');
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return value;
	return __('Due {0}').replace(
		'{0}',
		date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
	);
}

function requestSummary(window: PortalSelectionWindow) {
	const request = window.students[0]?.request;
	if (!request) return __('Your choices are being prepared.');
	if (request.status === 'Submitted')
		return __('Submitted. The school will review your choices next.');
	if (request.status === 'Approved') return __('Approved. Your choices are now confirmed.');
	if (request.status === 'Draft')
		return __('Your draft is open. Review your choices and submit before the deadline.');
	return `${request.status}.`;
}

async function loadBoard() {
	loading.value = true;
	errorMessage.value = '';
	try {
		board.value = await getSelfEnrollmentPortalBoard({});
	} catch (error) {
		errorMessage.value =
			error instanceof Error ? error.message : 'Could not load course selection.';
	} finally {
		loading.value = false;
	}
}

onMounted(() => {
	void loadBoard();
});
</script>
