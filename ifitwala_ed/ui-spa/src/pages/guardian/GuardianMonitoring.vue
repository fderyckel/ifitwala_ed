<!-- ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue -->
<template>
	<div class="space-y-6">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
				<div>
					<p class="type-overline text-ink/60">Guardian Portal</p>
					<h1 class="type-h1 text-ink">Family Monitoring</h1>
					<p class="type-body text-ink/70">
						One family-wide view of guardian-visible student logs and published results, with
						optional child filters.
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

		<section class="grid grid-cols-1 gap-3 sm:grid-cols-3">
			<article class="card-surface p-4">
				<p class="type-caption">Visible student logs</p>
				<p class="type-h3 text-ink">{{ counts.visible_student_logs }}</p>
			</article>
			<article class="card-surface p-4">
				<p class="type-caption">Unread student logs</p>
				<p class="type-h3 text-ink">{{ counts.unread_visible_student_logs }}</p>
			</article>
			<article class="card-surface p-4">
				<p class="type-caption">Published results</p>
				<p class="type-h3 text-ink">{{ counts.published_results }}</p>
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
			<section class="card-surface p-5">
				<h2 class="mb-3 type-h3 text-ink">Student Logs</h2>
				<div v-if="!studentLogs.length" class="type-body text-ink/70">
					No guardian-visible student logs in this window.
				</div>
				<div v-else class="space-y-3">
					<article
						v-for="row in studentLogs"
						:key="row.student_log"
						class="rounded-xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
							<div>
								<p class="type-body-strong text-ink">{{ row.student_name }}</p>
								<p class="type-caption text-ink/60">
									{{ row.date }}<span v-if="row.time"> · {{ row.time }}</span>
									<span v-if="row.follow_up_status"> · {{ row.follow_up_status }}</span>
								</p>
							</div>
							<p
								class="rounded-full px-3 py-1 type-caption"
								:class="row.is_unread ? 'bg-coral/15 text-flame' : 'bg-mint/15 text-forest'"
							>
								{{ row.is_unread ? 'Unread' : 'Seen' }}
							</p>
						</div>
						<p class="mt-2 type-body text-ink/80">{{ row.summary }}</p>
					</article>
				</div>
			</section>

			<section class="card-surface p-5">
				<h2 class="mb-3 type-h3 text-ink">Published Results</h2>
				<div v-if="!publishedResults.length" class="type-body text-ink/70">
					No published results in this window.
				</div>
				<div v-else class="space-y-3">
					<article
						v-for="row in publishedResults"
						:key="row.task_outcome"
						class="rounded-xl border border-line-soft bg-surface-soft p-4"
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

import { getGuardianMonitoringSnapshot } from '@/lib/services/guardianMonitoring/guardianMonitoringService';

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
