<!-- ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelection.vue -->
<template>
	<div class="space-y-6">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">Guardian Course Selection</p>
					<h1 class="type-h1 text-ink">Family Course Selection Board</h1>
					<p class="type-body text-ink/70">
						See every child’s open program choices in one calm surface, with required rows locked
						and unresolved decisions clearly marked.
					</p>
				</div>
				<div class="flex items-center gap-2">
					<RouterLink class="if-action" :to="{ name: 'guardian-home' }">Back to Home</RouterLink>
					<button type="button" class="if-action" :disabled="loading" @click="loadBoard">
						Refresh
					</button>
				</div>
			</div>
		</header>

		<section class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Children</p>
				<p class="mini-kpi-value">{{ childrenCount }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Open windows</p>
				<p class="mini-kpi-value">{{ openWindowCount }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Pending selections</p>
				<p class="mini-kpi-value">{{ pendingCount }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Submitted</p>
				<p class="mini-kpi-value">{{ submittedCount }}</p>
			</article>
		</section>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading family course selection board...</p>
		</section>
		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">Could not load family course selection board.</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<template v-else>
			<section v-if="!windows.length" class="card-surface p-5">
				<h2 class="type-h3 text-ink">No active selection windows</h2>
				<p class="mt-2 type-body text-ink/70">
					When the school opens course selections for your family, they will appear here with one
					row per child.
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

					<div class="mt-5 space-y-3">
						<article
							v-for="student in window.students"
							:key="`${window.selection_window}-${student.student}`"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
								<div class="flex items-center gap-3">
									<img
										v-if="student.student_image"
										:src="student.student_image"
										:alt="student.full_name"
										class="h-12 w-12 rounded-2xl object-cover ring-1 ring-line-soft"
									/>
									<div>
										<p class="type-body-strong text-ink">{{ student.full_name }}</p>
										<p class="type-caption text-ink/70">
											{{ student.cohort || student.student }}
										</p>
									</div>
								</div>
								<div class="flex flex-wrap items-center gap-2">
									<span class="chip">{{ student.request?.status || 'Draft' }}</span>
									<span class="chip">{{
										selectionValidationLabel(student.request?.validation_status)
									}}</span>
								</div>
							</div>
							<p v-if="student.request?.locked_reason" class="mt-3 type-caption text-ink/70">
								{{ student.request.locked_reason }}
							</p>
							<div class="mt-4 flex justify-end">
								<RouterLink
									:to="{
										name: 'guardian-course-selection-detail',
										params: {
											selection_window: window.selection_window,
											student_id: student.student,
										},
									}"
									class="if-action"
								>
									{{ student.request?.can_edit ? __('Continue for Child') : __('View Selection') }}
								</RouterLink>
							</div>
						</article>
					</div>
				</article>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';

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
const childrenCount = computed(() => board.value?.students.length || 0);
const openWindowCount = computed(
	() => windows.value.filter(window => window.is_open_now === 1).length
);
const pendingCount = computed(() =>
	windows.value.reduce((total, window) => total + window.summary.pending_count, 0)
);
const submittedCount = computed(() =>
	windows.value.reduce((total, window) => total + window.summary.submitted_count, 0)
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

function selectionValidationLabel(status?: string | null) {
	const normalized = String(status || '').trim();
	if (normalized === 'Valid') return __('Ready to submit');
	if (normalized === 'Invalid') return __('Action needed');
	if (normalized === 'Not Validated') return __('Review choices');
	return normalized || __('Review choices');
}

async function loadBoard() {
	loading.value = true;
	errorMessage.value = '';
	try {
		board.value = await getSelfEnrollmentPortalBoard();
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
