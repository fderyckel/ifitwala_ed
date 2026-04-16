<!-- ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue -->
<template>
	<div class="portal-page">
		<header class="card-surface monitoring-hero p-5 sm:p-6">
			<div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
				<div>
					<p class="type-overline text-ink/60">Guardian Portal</p>
					<h1 class="type-h1 text-ink">Family Monitoring</h1>
					<p class="type-body text-ink/70">
						View your child's or children's logs and published results in one place, then filter by
						child when needed.
					</p>
				</div>
				<div class="grid gap-3 sm:grid-cols-3">
					<label class="space-y-1">
						<span class="type-caption text-ink/60">Child filter</span>
						<select
							v-model="selectedStudent"
							class="w-full rounded-xl border border-line-soft bg-white px-3 py-2 type-body text-ink"
						>
							<option value="">All linked children</option>
							<option v-for="child in children" :key="child.student" :value="child.student">
								{{ child.full_name }}
							</option>
						</select>
					</label>
					<label class="space-y-1">
						<span class="type-caption text-ink/60">Window</span>
						<select
							v-model.number="selectedDays"
							class="w-full rounded-xl border border-line-soft bg-white px-3 py-2 type-body text-ink"
						>
							<option :value="14">14 days</option>
							<option :value="30">30 days</option>
							<option :value="60">60 days</option>
							<option :value="90">90 days</option>
						</select>
					</label>
					<div class="flex items-end">
						<button
							type="button"
							class="if-action w-full"
							:disabled="loading"
							@click="loadSnapshot"
						>
							Refresh
						</button>
					</div>
				</div>
			</div>
		</header>

		<section class="monitoring-summary" aria-label="Family monitoring summary">
			<article class="card-surface monitoring-metric-card monitoring-metric-card--visible p-4">
				<div class="monitoring-metric-card__row">
					<div>
						<p class="type-caption text-ink/65">Visible student logs</p>
						<p class="type-caption text-ink/50">Guardian-visible items in this window</p>
					</div>
					<p class="type-h2 text-ink">{{ counts.visible_student_logs }}</p>
				</div>
			</article>
			<article class="card-surface monitoring-metric-card monitoring-metric-card--unread p-4">
				<div class="monitoring-metric-card__row">
					<div>
						<p class="type-caption text-ink/65">Unread student logs</p>
						<p class="type-caption text-ink/50">Needs guardian review</p>
					</div>
					<p class="type-h2 text-flame">{{ counts.unread_visible_student_logs }}</p>
				</div>
			</article>
			<article class="card-surface monitoring-metric-card monitoring-metric-card--results p-4">
				<div class="monitoring-metric-card__row">
					<div>
						<p class="type-caption text-ink/65">Published results</p>
						<p class="type-caption text-ink/50">Shared outcomes for linked children</p>
					</div>
					<p class="type-h2 text-jacaranda">{{ counts.published_results }}</p>
				</div>
			</article>
		</section>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading family monitoring...</p>
		</section>

		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">Could not load family monitoring.</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<template v-else>
			<section class="card-surface monitoring-section monitoring-section--logs p-5">
				<div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
					<div>
						<p class="type-overline text-canopy/75">Student Logs</p>
						<h2 class="type-h3 text-ink">Guardian-visible updates</h2>
						<p class="type-caption text-ink/65">
							Review new notes across your family and mark them as seen once read.
						</p>
					</div>
					<div class="flex flex-wrap gap-2">
						<span class="chip">Visible {{ counts.visible_student_logs }}</span>
						<span class="rounded-full bg-flame/12 px-3 py-1 type-caption text-flame">
							Unread {{ counts.unread_visible_student_logs }}
						</span>
					</div>
				</div>
				<div v-if="!studentLogs.length" class="type-body text-ink/70">
					No guardian-visible student logs in this window.
				</div>
				<div v-else class="space-y-3">
					<article
						v-for="row in studentLogs"
						:key="row.student_log"
						class="monitoring-entry monitoring-entry--log rounded-xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
							<div>
								<p class="type-body-strong text-ink">{{ row.student_name }}</p>
								<p class="type-caption text-ink/60">
									{{ row.date }}<span v-if="row.time"> · {{ row.time }}</span>
									<span v-if="row.follow_up_status"> · {{ row.follow_up_status }}</span>
								</p>
							</div>
							<div class="flex flex-col items-start gap-2 sm:items-end">
								<p
									class="rounded-full px-3 py-1 type-caption"
									:class="row.is_unread ? 'bg-flame/15 text-flame' : 'bg-leaf/15 text-canopy'"
								>
									{{ row.is_unread ? 'Unread' : 'Seen' }}
								</p>
								<button
									v-if="row.is_unread"
									type="button"
									class="type-caption font-semibold text-jacaranda hover:underline disabled:text-ink/40"
									:disabled="markingLogName === row.student_log"
									@click="markAsSeen(row.student_log)"
								>
									{{ markingLogName === row.student_log ? 'Saving...' : 'Mark as seen' }}
								</button>
							</div>
						</div>
						<p class="mt-2 type-body text-ink/80">{{ row.summary }}</p>
					</article>
				</div>
			</section>

			<section class="card-surface monitoring-section monitoring-section--results p-5">
				<div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
					<div>
						<p class="type-overline text-jacaranda/80">Published Results</p>
						<h2 class="type-h3 text-ink">Latest shared outcomes</h2>
						<p class="type-caption text-ink/65">
							Published assessment results stay separate from logs so the page is easier to scan.
						</p>
					</div>
					<span class="rounded-full bg-jacaranda/12 px-3 py-1 type-caption text-jacaranda">
						Published {{ counts.published_results }}
					</span>
				</div>
				<div v-if="!publishedResults.length" class="type-body text-ink/70">
					No published results in this window.
				</div>
				<div v-else class="space-y-3">
					<article
						v-for="row in publishedResults"
						:key="row.task_outcome"
						class="monitoring-entry monitoring-entry--result rounded-xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
							<div>
								<p class="type-body-strong text-ink">{{ row.student_name }}</p>
								<p class="type-caption text-ink/60">{{ row.title }} · {{ row.published_on }}</p>
							</div>
							<p v-if="row.score" class="type-body-strong text-ink">{{ row.score.value }}</p>
						</div>
						<p v-if="row.published_by" class="mt-2 type-caption text-ink/60">
							Published by {{ row.published_by }}
						</p>
						<p v-if="row.narrative" class="type-body text-ink/80">{{ row.narrative }}</p>
					</article>
				</div>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { toast } from 'frappe-ui';

import {
	getGuardianMonitoringSnapshot,
	markGuardianStudentLogRead,
} from '@/lib/services/guardianMonitoring/guardianMonitoringService';

import type {
	MonitoringPublishedResult,
	MonitoringStudentLog,
	Response as GuardianMonitoringSnapshot,
} from '@/types/contracts/guardian/get_guardian_monitoring_snapshot';

const loading = ref(true);
const errorMessage = ref('');
const snapshot = ref<GuardianMonitoringSnapshot | null>(null);
const selectedStudent = ref('');
const selectedDays = ref(30);
const markingLogName = ref('');

const children = computed(() => snapshot.value?.family.children ?? []);
const counts = computed(
	() =>
		snapshot.value?.counts ?? {
			visible_student_logs: 0,
			unread_visible_student_logs: 0,
			published_results: 0,
		}
);
const studentLogs = computed<MonitoringStudentLog[]>(() => snapshot.value?.student_logs ?? []);
const publishedResults = computed<MonitoringPublishedResult[]>(
	() => snapshot.value?.published_results ?? []
);

async function markAsSeen(studentLog: string) {
	if (!studentLog || markingLogName.value === studentLog) return;

	markingLogName.value = studentLog;
	try {
		await markGuardianStudentLogRead({ log_name: studentLog });
		const row = snapshot.value?.student_logs.find(item => item.student_log === studentLog);
		if (row?.is_unread) {
			row.is_unread = false;
			if ((snapshot.value?.counts.unread_visible_student_logs || 0) > 0 && snapshot.value) {
				snapshot.value.counts.unread_visible_student_logs -= 1;
			}
		}
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		toast.error(message || 'Could not update read status.');
	} finally {
		markingLogName.value = '';
	}
}

async function loadSnapshot() {
	loading.value = true;
	errorMessage.value = '';
	try {
		snapshot.value = await getGuardianMonitoringSnapshot({
			student: selectedStudent.value || undefined,
			days: selectedDays.value,
		});
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		errorMessage.value = message || 'Unknown error';
	} finally {
		loading.value = false;
	}
}

watch([selectedStudent, selectedDays], () => {
	void loadSnapshot();
});

onMounted(() => {
	void loadSnapshot();
});
</script>

<style scoped>
.monitoring-hero {
	position: relative;
	overflow: hidden;
	border-color: rgb(var(--sand-rgb) / 0.78);
	background:
		radial-gradient(circle at 0% 0%, rgb(var(--leaf-rgb) / 0.14), transparent 34%),
		radial-gradient(circle at 100% 0%, rgb(var(--jacaranda-rgb) / 0.16), transparent 38%),
		linear-gradient(180deg, rgb(var(--surface-strong-rgb) / 0.98), rgb(var(--sky-rgb) / 0.82));
	box-shadow: 0 16px 36px rgb(var(--ink-rgb) / 0.06);
}

.monitoring-summary {
	display: grid;
	grid-auto-flow: column;
	grid-auto-columns: minmax(16rem, 1fr);
	gap: 0.75rem;
	overflow-x: auto;
	padding-bottom: 0.25rem;
}

.monitoring-metric-card {
	position: relative;
	overflow: hidden;
	min-width: 0;
	border-color: rgb(var(--border-rgb) / 0.78);
	background: linear-gradient(
		180deg,
		rgb(var(--surface-strong-rgb) / 0.98),
		rgb(var(--surface-rgb) / 0.92)
	);
}

.monitoring-metric-card::before {
	content: '';
	position: absolute;
	inset: 0 auto auto 0;
	height: 0.3rem;
	width: 100%;
}

.monitoring-metric-card--visible::before {
	background: linear-gradient(90deg, rgb(var(--leaf-rgb) / 0.9), rgb(var(--canopy-rgb) / 0.78));
}

.monitoring-metric-card--unread::before {
	background: linear-gradient(90deg, rgb(var(--flame-rgb) / 0.92), rgb(var(--clay-rgb) / 0.82));
}

.monitoring-metric-card--results::before {
	background: linear-gradient(
		90deg,
		rgb(var(--jacaranda-rgb) / 0.94),
		rgb(var(--slate-rgb) / 0.8)
	);
}

.monitoring-metric-card__row {
	display: flex;
	align-items: flex-end;
	justify-content: space-between;
	gap: 1rem;
}

.monitoring-section {
	position: relative;
	overflow: hidden;
}

.monitoring-section::before {
	content: '';
	position: absolute;
	inset: 0 auto 0 0;
	width: 0.35rem;
}

.monitoring-section--logs {
	border-color: rgb(var(--leaf-rgb) / 0.18);
	background:
		radial-gradient(circle at 100% 0%, rgb(var(--leaf-rgb) / 0.08), transparent 34%),
		rgb(var(--surface-rgb) / 0.94);
}

.monitoring-section--logs::before {
	background: linear-gradient(180deg, rgb(var(--leaf-rgb) / 0.84), rgb(var(--canopy-rgb) / 0.82));
}

.monitoring-section--results {
	border-color: rgb(var(--jacaranda-rgb) / 0.18);
	background:
		radial-gradient(circle at 100% 0%, rgb(var(--jacaranda-rgb) / 0.08), transparent 36%),
		rgb(var(--surface-rgb) / 0.94);
}

.monitoring-section--results::before {
	background: linear-gradient(
		180deg,
		rgb(var(--jacaranda-rgb) / 0.88),
		rgb(var(--slate-rgb) / 0.8)
	);
}

.monitoring-entry {
	transition:
		border-color 120ms ease,
		transform 120ms ease,
		box-shadow 120ms ease;
}

.monitoring-entry:hover {
	transform: translateY(-1px);
	box-shadow: var(--shadow-soft);
}

.monitoring-entry--log:hover {
	border-color: rgb(var(--leaf-rgb) / 0.32);
}

.monitoring-entry--result:hover {
	border-color: rgb(var(--jacaranda-rgb) / 0.3);
}

@media (min-width: 640px) {
	.monitoring-summary {
		grid-auto-flow: initial;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		overflow: visible;
		padding-bottom: 0;
	}
}
</style>
