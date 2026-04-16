<template>
	<div class="staff-shell space-y-6">
		<header class="card-surface p-5 sm:p-6">
			<div class="page-header">
				<div class="page-header__intro">
					<p class="type-overline text-ink/60">My Growth</p>
					<h1 class="type-h1 text-canopy">Professional Development</h1>
					<p class="type-meta text-slate-token/80">
						Track requests, budget fit, upcoming commitments, and completion follow-through inside
						the academic year.
					</p>
				</div>
				<div class="page-header__actions">
					<RouterLink class="if-action" :to="{ name: 'staff-home' }">Back to Home</RouterLink>
					<button type="button" class="if-action" @click="openRequestOverlay()">
						New request
					</button>
					<button type="button" class="if-action" :disabled="loading" @click="loadBoard">
						Refresh
					</button>
				</div>
			</div>
		</header>

		<section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Open requests</p>
				<p class="mini-kpi-value">{{ board?.summary.open_requests ?? 0 }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Upcoming PD</p>
				<p class="mini-kpi-value">{{ board?.summary.upcoming_records ?? 0 }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Completion backlog</p>
				<p class="mini-kpi-value">{{ board?.summary.completion_backlog ?? 0 }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Available budget</p>
				<p class="mini-kpi-value">{{ money(board?.summary.available_budget_total ?? 0) }}</p>
			</article>
		</section>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading professional development board...</p>
		</section>
		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">Could not load professional development.</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<template v-else-if="board">
			<section class="card-surface p-5">
				<div class="mb-4 flex items-center justify-between gap-3">
					<div>
						<h2 class="type-h3 text-ink">Budget Pools</h2>
						<p class="type-caption text-ink/60">
							Choose a pool first when you want a prefilled request.
						</p>
					</div>
					<p class="type-caption text-ink/60">
						{{ board.viewer.school }} · {{ board.viewer.academic_year || 'No academic year' }}
					</p>
				</div>
				<div v-if="!board.budget_rows.length" class="type-body text-ink/70">
					No active PD budgets are available in your current scope.
				</div>
				<div v-else class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
					<article
						v-for="budget in board.budget_rows"
						:key="budget.value"
						class="rounded-2xl border border-line-soft bg-surface-soft p-4"
					>
						<p class="type-body-strong text-ink">{{ budget.label }}</p>
						<p class="mt-1 type-caption text-ink/70">
							Available: {{ money(budget.available_amount) }}
						</p>
						<div class="mt-4">
							<button type="button" class="if-action" @click="openRequestOverlay(budget.value)">
								Request against this pool
							</button>
						</div>
					</article>
				</div>
			</section>

			<section class="card-surface p-5">
				<div class="mb-4 flex items-center justify-between gap-3">
					<div>
						<h2 class="type-h3 text-ink">My Requests</h2>
						<p class="type-caption text-ink/60">
							Snapshots are frozen at submission and approvals materialize committed records.
						</p>
					</div>
				</div>
				<div v-if="!board.requests.length" class="type-body text-ink/70">No requests yet.</div>
				<ul v-else class="space-y-3">
					<li
						v-for="request in board.requests"
						:key="request.name"
						class="rounded-2xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
							<div class="space-y-1">
								<p class="type-body-strong text-ink">{{ request.title }}</p>
								<p class="type-caption text-ink/70">
									{{ request.professional_development_type }} ·
									{{ formatDateTime(request.start_datetime) }}
								</p>
								<p class="type-caption text-ink/70">
									Status: {{ request.status }} · Validation: {{ request.validation_status }}
								</p>
								<p class="type-caption text-ink/70">
									Estimated: {{ money(request.estimated_total) }}
								</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<button
									v-if="canDecide && ['Submitted', 'Under Review'].includes(request.status)"
									type="button"
									class="if-action"
									@click="decide(request.name, 'approve')"
								>
									Approve
								</button>
								<button
									v-if="canDecide && ['Submitted', 'Under Review'].includes(request.status)"
									type="button"
									class="if-action"
									@click="decide(request.name, 'reject')"
								>
									Reject
								</button>
								<button
									v-if="canCancelRequest(request.status)"
									type="button"
									class="if-action"
									@click="cancel(request.name)"
								>
									Cancel
								</button>
							</div>
						</div>
					</li>
				</ul>
			</section>

			<section class="card-surface p-5">
				<div class="mb-4 flex items-center justify-between gap-3">
					<div>
						<h2 class="type-h3 text-ink">Committed Records</h2>
						<p class="type-caption text-ink/60">
							Approved requests project into bookings and completion follow-through.
						</p>
					</div>
				</div>
				<div v-if="!board.records.length" class="type-body text-ink/70">
					No committed records yet.
				</div>
				<ul v-else class="space-y-3">
					<li
						v-for="record in board.records"
						:key="record.name"
						class="rounded-2xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
							<div class="space-y-1">
								<p class="type-body-strong text-ink">{{ record.title }}</p>
								<p class="type-caption text-ink/70">
									{{ record.professional_development_type }} ·
									{{ formatDateTime(record.start_datetime) }}
								</p>
								<p class="type-caption text-ink/70">
									Status: {{ record.status }} · Estimated: {{ money(record.estimated_total) }}
									<span v-if="record.actual_total">
										· Actual: {{ money(record.actual_total) }}</span
									>
								</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<button
									v-if="canCompleteRecord(record)"
									type="button"
									class="if-action"
									@click="openCompletionOverlay(record)"
								>
									Complete
								</button>
								<button
									v-if="canLiquidate && record.status === 'Completed'"
									type="button"
									class="if-action"
									@click="liquidate(record.name)"
								>
									Liquidate
								</button>
							</div>
						</div>
					</li>
				</ul>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { toast } from 'frappe-ui';

import { useOverlayStack } from '@/composables/useOverlayStack';
import {
	cancelProfessionalDevelopmentRequest,
	decideProfessionalDevelopmentRequest,
	getProfessionalDevelopmentBoard,
	liquidateProfessionalDevelopmentRecord,
} from '@/lib/services/professionalDevelopment/professionalDevelopmentService';
import { getStaffHomeHeader, type StaffHomeHeader } from '@/lib/services/staff/staffHomeService';
import { SIGNAL_PROFESSIONAL_DEVELOPMENT_INVALIDATE, uiSignals } from '@/lib/uiSignals';
import type {
	ProfessionalDevelopmentBoard,
	ProfessionalDevelopmentRecordRow,
} from '@/types/contracts/professional_development/get_professional_development_board';

const overlay = useOverlayStack();

const loading = ref(true);
const errorMessage = ref('');
const board = ref<ProfessionalDevelopmentBoard | null>(null);
const header = ref<StaffHomeHeader | null>(null);

const canDecide = computed(() =>
	Boolean(header.value?.capabilities?.professional_development_decide)
);
const canLiquidate = computed(() =>
	Boolean(header.value?.capabilities?.professional_development_liquidate)
);

function money(value: number) {
	return new Intl.NumberFormat(undefined, {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	}).format(Number(value || 0));
}

function formatDateTime(value: string) {
	if (!value) return '';
	return new Intl.DateTimeFormat(undefined, {
		dateStyle: 'medium',
		timeStyle: 'short',
	}).format(new Date(value));
}

async function loadBoard() {
	loading.value = true;
	errorMessage.value = '';
	try {
		const [boardResponse, headerResponse] = await Promise.all([
			getProfessionalDevelopmentBoard(),
			getStaffHomeHeader(),
		]);
		board.value = boardResponse;
		header.value = headerResponse;
	} catch (error: any) {
		errorMessage.value = error?.message || 'Unknown error';
	} finally {
		loading.value = false;
	}
}

function openRequestOverlay(budgetName?: string | null) {
	overlay.open('staff-professional-development-request', {
		budgetName: budgetName ?? null,
	});
}

function openCompletionOverlay(record: ProfessionalDevelopmentRecordRow) {
	overlay.open('staff-professional-development-completion', {
		record,
	});
}

function canCancelRequest(status: string) {
	return ['Draft', 'Submitted', 'Under Review', 'Approved'].includes(status);
}

function canCompleteRecord(record: ProfessionalDevelopmentRecordRow) {
	return ['Planned', 'Attended'].includes(record.status);
}

async function cancel(requestName: string) {
	try {
		const response = await cancelProfessionalDevelopmentRequest({ request_name: requestName });
		board.value = response.board;
		toast.create({ title: 'Request cancelled', icon: 'check' });
	} catch (error: any) {
		toast.create({
			title: 'Could not cancel request',
			text: error?.message || '',
			icon: 'alert-circle',
		});
	}
}

async function decide(requestName: string, decision: 'approve' | 'reject') {
	try {
		const response = await decideProfessionalDevelopmentRequest({
			request_name: requestName,
			decision,
		});
		board.value = response.board;
		toast.create({
			title: decision === 'approve' ? 'Request approved' : 'Request rejected',
			icon: 'check',
		});
	} catch (error: any) {
		toast.create({
			title: 'Could not decide request',
			text: error?.message || '',
			icon: 'alert-circle',
		});
	}
}

async function liquidate(recordName: string) {
	try {
		const response = await liquidateProfessionalDevelopmentRecord({ record_name: recordName });
		board.value = response.board;
		toast.create({ title: 'Record liquidated', icon: 'check' });
	} catch (error: any) {
		toast.create({
			title: 'Could not liquidate record',
			text: error?.message || '',
			icon: 'alert-circle',
		});
	}
}

let disposeInvalidate: (() => void) | null = null;

onMounted(async () => {
	await loadBoard();
	disposeInvalidate = uiSignals.subscribe(SIGNAL_PROFESSIONAL_DEVELOPMENT_INVALIDATE, loadBoard);
});

onBeforeUnmount(() => {
	if (disposeInvalidate) disposeInvalidate();
});
</script>
