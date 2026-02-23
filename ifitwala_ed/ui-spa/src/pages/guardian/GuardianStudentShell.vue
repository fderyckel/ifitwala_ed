<!-- ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue -->
<template>
	<div class="space-y-6">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-caption text-ink/70">Guardian portal</p>
					<h1 class="type-h1 text-ink">{{ selectedChild?.full_name || 'Student' }}</h1>
					<p class="type-body text-ink/70">
						{{ selectedChild?.school || 'School unavailable' }} ·
						{{ studentId || 'Unknown student' }}
					</p>
				</div>
				<div class="flex items-center gap-2">
					<RouterLink :to="{ name: 'guardian-home' }" class="if-action"
						>Back to Family Snapshot</RouterLink
					>
					<button type="button" class="if-action" :disabled="loading" @click="loadSnapshot">
						Refresh
					</button>
				</div>
			</div>
		</header>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading student view...</p>
		</section>

		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">Could not load student view.</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<section v-else-if="!selectedChild" class="card-surface p-5">
			<p class="type-body-strong text-flame">
				This student is not available in your guardian scope.
			</p>
		</section>

		<template v-else>
			<section class="card-surface p-5">
				<h2 class="mb-3 type-h3 text-ink">Timeline</h2>
				<div v-if="!studentTimeline.length" class="type-body text-ink/70">
					No timeline items in this window.
				</div>
				<div v-else class="space-y-3">
					<article
						v-for="day in studentTimeline"
						:key="day.date"
						class="rounded-xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="mb-2 flex items-center justify-between">
							<h3 class="type-body-strong text-ink">{{ day.label }}</h3>
							<span class="type-caption text-ink/60">{{ day.date }}</span>
						</div>

						<p class="type-caption text-ink/60">
							{{ day.child.day_summary.start_time || '--:--' }} -
							{{ day.child.day_summary.end_time || '--:--' }}
						</p>

						<ul v-if="day.child.blocks.length" class="mt-2 space-y-1">
							<li
								v-for="block in day.child.blocks"
								:key="`${day.date}-${block.start_time}-${block.title}`"
								class="type-body text-ink/80"
							>
								{{ block.start_time }} - {{ block.end_time }} · {{ block.title }}
								<span v-if="block.subtitle" class="text-ink/60">({{ block.subtitle }})</span>
							</li>
						</ul>
						<p v-else class="mt-2 type-caption text-ink/60">
							{{ day.child.day_summary.note || 'No scheduled blocks' }}
						</p>

						<div
							v-if="day.child.tasks_due.length || day.child.assessments_upcoming.length"
							class="mt-2 space-y-1"
						>
							<p v-if="day.child.tasks_due.length" class="type-caption text-ink/70">
								Due: {{ chipTitles(day.child.tasks_due) }}
							</p>
							<p v-if="day.child.assessments_upcoming.length" class="type-caption text-ink/70">
								Assessments: {{ chipTitles(day.child.assessments_upcoming) }}
							</p>
						</div>
					</article>
				</div>
			</section>

			<section class="card-surface p-5">
				<h2 class="mb-3 type-h3 text-ink">Attention Needed</h2>
				<div v-if="!studentAttention.length" class="type-body text-ink/70">
					No attention items right now.
				</div>
				<ul v-else class="space-y-2">
					<li
						v-for="(item, index) in studentAttention"
						:key="`attention-${index}`"
						class="rounded-lg border border-line-soft bg-white p-3"
					>
						<p class="type-body-strong text-ink">
							<span v-if="item.type === 'attendance'">Attendance</span>
							<span v-else-if="item.type === 'student_log'">Student Log</span>
							<span v-else>Communication</span>
						</p>
						<p class="type-caption text-ink/70">
							{{ item.date }}<span v-if="'time' in item && item.time"> · {{ item.time }}</span>
						</p>
						<p class="type-body text-ink/80">
							<span v-if="item.type === 'attendance'">{{ item.summary }}</span>
							<span v-else-if="item.type === 'student_log'">{{ item.summary }}</span>
							<span v-else>{{ item.title }}</span>
						</p>
					</li>
				</ul>
			</section>

			<section class="card-surface p-5">
				<h2 class="mb-3 type-h3 text-ink">Preparation & Support</h2>
				<div v-if="!studentPrep.length" class="type-body text-ink/70">
					No preparation cues in this window.
				</div>
				<ul v-else class="space-y-2">
					<li
						v-for="(item, index) in studentPrep"
						:key="`prep-${index}`"
						class="rounded-lg border border-line-soft bg-white p-3"
					>
						<p class="type-caption text-ink/70">{{ item.date }} · {{ item.source }}</p>
						<p class="type-body text-ink/80">{{ item.label }}</p>
					</li>
				</ul>
			</section>

			<section class="card-surface p-5">
				<h2 class="mb-3 type-h3 text-ink">Recent Activity</h2>
				<div v-if="!studentRecent.length" class="type-body text-ink/70">No recent activity.</div>
				<ul v-else class="space-y-2">
					<li
						v-for="(item, index) in studentRecent"
						:key="`recent-${index}`"
						class="rounded-lg border border-line-soft bg-white p-3"
					>
						<p class="type-body-strong text-ink">
							<span v-if="item.type === 'task_result'">Task Result</span>
							<span v-else-if="item.type === 'student_log'">Student Log</span>
							<span v-else>Communication</span>
						</p>
						<p class="type-caption text-ink/70">
							<span v-if="item.type === 'task_result'">{{ item.published_on }}</span>
							<span v-else>{{ item.date }}</span>
						</p>
						<p class="type-body text-ink/80">
							<span v-if="item.type === 'task_result'">{{ item.title }}</span>
							<span v-else-if="item.type === 'student_log'">{{ item.summary }}</span>
							<span v-else>{{ item.title }}</span>
						</p>
					</li>
				</ul>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import { getGuardianHomeSnapshot } from '@/lib/services/guardianHome/guardianHomeService';

import type {
	AttentionItem,
	ChildTimeline,
	DueTaskChip,
	PrepItem,
	RecentActivityItem,
	Response as GuardianHomeSnapshot,
} from '@/types/contracts/guardian/get_guardian_home_snapshot';

type StudentDayTimeline = {
	date: string;
	label: string;
	is_school_day: boolean;
	child: ChildTimeline;
};

const route = useRoute();

const loading = ref<boolean>(true);
const errorMessage = ref<string>('');
const snapshot = ref<GuardianHomeSnapshot | null>(null);

const studentId = computed(() => String(route.params.student_id || ''));
const selectedChild = computed(
	() => snapshot.value?.family.children.find(child => child.student === studentId.value) ?? null
);

const studentTimeline = computed<StudentDayTimeline[]>(() => {
	if (!studentId.value) return [];
	const out: StudentDayTimeline[] = [];
	for (const day of snapshot.value?.zones.family_timeline ?? []) {
		const child = day.children.find(row => row.student === studentId.value);
		if (!child) continue;
		out.push({
			date: day.date,
			label: day.label,
			is_school_day: day.is_school_day,
			child,
		});
	}
	return out;
});

const studentAttention = computed<AttentionItem[]>(() =>
	(snapshot.value?.zones.attention_needed ?? []).filter(item =>
		'student' in item ? item.student === studentId.value : item.type === 'communication'
	)
);

const studentPrep = computed<PrepItem[]>(() =>
	(snapshot.value?.zones.preparation_and_support ?? []).filter(
		item => item.student === studentId.value
	)
);

const studentRecent = computed<RecentActivityItem[]>(() =>
	(snapshot.value?.zones.recent_activity ?? []).filter(item =>
		'student' in item ? item.student === studentId.value : item.type === 'communication'
	)
);

function chipTitles(chips: DueTaskChip[]): string {
	return chips.map(chip => chip.title).join(', ');
}

async function loadSnapshot() {
	loading.value = true;
	errorMessage.value = '';
	try {
		if (!studentId.value) {
			throw new Error('Missing student id in route.');
		}
		snapshot.value = await getGuardianHomeSnapshot({ school_days: 7 });
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		errorMessage.value = message || 'Unknown error';
	} finally {
		loading.value = false;
	}
}

watch(
	studentId,
	() => {
		void loadSnapshot();
	},
	{ immediate: true }
);
</script>
