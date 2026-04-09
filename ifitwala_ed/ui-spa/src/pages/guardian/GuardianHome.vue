<!-- ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue -->
<template>
	<div class="portal-page">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">Guardian Portal</p>
					<h1 class="type-h1 text-ink">Family Snapshot</h1>
					<p class="type-body text-ink/70">
						Today and the next {{ meta.school_days }} school days for your family.
					</p>
				</div>
				<div class="flex items-center gap-2">
					<RouterLink class="if-action" :to="{ name: 'guardian-course-selection' }"
						>Course Selection</RouterLink
					>
					<RouterLink class="if-action" :to="{ name: 'guardian-activities' }"
						>Activity Booking</RouterLink
					>
					<button
						type="button"
						class="if-action self-start"
						:disabled="loading"
						@click="loadSnapshot"
					>
						Refresh
					</button>
				</div>
			</div>
		</header>

		<section class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			<article class="card-surface p-3">
				<p class="type-caption">Unread communications</p>
				<p class="type-h3 text-ink">{{ counts.unread_communications }}</p>
			</article>
			<article class="card-surface p-3">
				<p class="type-caption">Unread student logs</p>
				<p class="type-h3 text-ink">{{ counts.unread_visible_student_logs }}</p>
			</article>
			<article class="card-surface p-3">
				<p class="type-caption">Upcoming due tasks</p>
				<p class="type-h3 text-ink">{{ counts.upcoming_due_tasks }}</p>
			</article>
			<article class="card-surface p-3">
				<p class="type-caption">Upcoming assessments</p>
				<p class="type-h3 text-ink">{{ counts.upcoming_assessments }}</p>
			</article>
		</section>

		<section class="card-surface p-5">
			<h2 class="mb-3 type-h3 text-ink">Quick Links</h2>
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
				<RouterLink
					v-for="item in quickLinks"
					:key="item.title"
					:to="item.to"
					class="action-tile group"
				>
					<div class="action-tile__icon">
						<FeatherIcon :name="item.icon" class="h-5 w-5" />
					</div>
					<div class="min-w-0 flex-1">
						<p class="type-body-strong text-ink transition-colors group-hover:text-jacaranda">
							{{ item.title }}
						</p>
						<p class="truncate type-caption text-ink/70">{{ item.description }}</p>
					</div>
					<FeatherIcon name="chevron-right" class="h-4 w-4 text-ink/40" />
				</RouterLink>
			</div>
		</section>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading guardian home snapshot...</p>
		</section>

		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">Could not load guardian home snapshot.</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<template v-else>
			<section class="card-surface p-5">
				<div class="mb-4 flex items-center justify-between">
					<div>
						<h2 class="type-h3 text-ink">Learning Highlights</h2>
						<p class="mt-1 type-caption text-ink/70">
							Big themes, what is coming up next, and one simple prompt for home.
						</p>
					</div>
					<span class="chip">{{ learningHighlights.length }}</span>
				</div>
				<div v-if="!learningHighlights.length" class="type-body text-ink/70">
					Learning highlights will appear here once teachers publish the current class focus.
				</div>
				<div v-else class="grid gap-4 lg:grid-cols-2">
					<article
						v-for="highlight in learningHighlights"
						:key="`${highlight.student}-${highlight.course}`"
						class="rounded-xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="flex items-start justify-between gap-3">
							<div class="flex min-w-0 items-start gap-3">
								<div
									class="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-line-soft bg-white"
								>
									<img
										v-if="childImage(highlight.student)"
										:src="childImage(highlight.student)"
										:alt="highlight.student_name || childName(highlight.student)"
										class="h-full w-full object-cover"
										loading="lazy"
									/>
									<span v-else class="type-body-strong text-ink/50">
										{{ childInitials(highlight.student) }}
									</span>
								</div>
								<div class="min-w-0">
									<RouterLink
										:to="{ name: 'guardian-student', params: { student_id: highlight.student } }"
										class="type-body-strong text-jacaranda hover:underline"
									>
										{{ highlight.student_name || childName(highlight.student) }}
									</RouterLink>
									<p class="mt-1 type-caption text-ink/60">
										{{ highlight.course_name || 'Current course' }}
										<span v-if="highlight.class_label">· {{ highlight.class_label }}</span>
									</p>
								</div>
							</div>
							<span v-if="highlight.unit_title" class="chip">{{ highlight.unit_title }}</span>
						</div>

						<p v-if="highlight.focus_statement" class="mt-3 type-body text-ink/80">
							{{ highlight.focus_statement }}
						</p>
						<p v-if="highlight.next_step" class="mt-3 type-caption text-ink/70">
							Coming up: {{ highlight.next_step }}
							<span v-if="highlight.next_step_supporting_text">
								· {{ highlight.next_step_supporting_text }}
							</span>
						</p>
						<div
							v-if="highlight.dinner_prompt"
							class="mt-4 rounded-lg border border-line-soft bg-white p-3"
						>
							<p class="type-overline text-ink/60">Talk at home</p>
							<p class="mt-2 type-body text-ink/80">{{ highlight.dinner_prompt }}</p>
						</div>
						<div class="mt-4">
							<RouterLink
								:to="{ name: 'guardian-student', params: { student_id: highlight.student } }"
								class="inline-flex text-sm font-medium text-jacaranda transition hover:text-jacaranda/80"
							>
								View learning brief
							</RouterLink>
						</div>
					</article>
				</div>
			</section>

			<section class="card-surface p-5">
				<div class="mb-4 flex items-center justify-between">
					<h2 class="type-h3 text-ink">Family Timeline</h2>
				</div>
				<div v-if="!familyTimeline.length" class="type-body text-ink/70">
					No timeline items in this window.
				</div>
				<div v-else class="space-y-4">
					<article
						v-for="day in familyTimeline"
						:key="day.date"
						class="rounded-xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="mb-3 flex items-center justify-between">
							<h3 class="type-body-strong text-ink">{{ day.label }}</h3>
							<span class="type-caption text-ink/60">{{ day.date }}</span>
						</div>
						<div class="space-y-3">
							<div
								v-for="child in day.children"
								:key="`${day.date}-${child.student}`"
								class="rounded-lg border border-line-soft bg-white p-3"
							>
								<div class="mb-2 flex items-center justify-between">
									<RouterLink
										:to="{ name: 'guardian-student', params: { student_id: child.student } }"
										class="type-body-strong text-jacaranda hover:underline"
									>
										{{ childName(child.student) }}
									</RouterLink>
									<span class="type-caption text-ink/60">
										{{ child.day_summary.start_time || '--:--' }} -
										{{ child.day_summary.end_time || '--:--' }}
									</span>
								</div>

								<ul v-if="child.blocks.length" class="space-y-1">
									<li
										v-for="block in child.blocks"
										:key="`${child.student}-${block.start_time}-${block.title}`"
										class="type-body text-ink/80"
									>
										{{ block.start_time }} - {{ block.end_time }} · {{ block.title }}
										<span v-if="block.subtitle" class="text-ink/60">({{ block.subtitle }})</span>
									</li>
								</ul>
								<p v-else class="type-caption text-ink/60">
									{{ child.day_summary.note || 'No scheduled blocks' }}
								</p>

								<div
									v-if="child.tasks_due.length || child.assessments_upcoming.length"
									class="mt-2 space-y-1"
								>
									<p v-if="child.tasks_due.length" class="type-caption text-ink/70">
										Due: {{ chipTitles(child.tasks_due) }}
									</p>
									<p v-if="child.assessments_upcoming.length" class="type-caption text-ink/70">
										Assessments: {{ chipTitles(child.assessments_upcoming) }}
									</p>
								</div>
							</div>
						</div>
					</article>
				</div>
			</section>

			<section class="card-surface p-5">
				<h2 class="mb-3 type-h3 text-ink">Attention Needed</h2>
				<div v-if="!attentionItems.length" class="type-body text-ink/70">
					No attention items right now.
				</div>
				<ul v-else class="space-y-2">
					<li
						v-for="(item, index) in attentionItems"
						:key="`attention-${index}`"
						class="rounded-lg border border-line-soft bg-white p-3"
					>
						<p class="type-body-strong text-ink">
							<span v-if="item.type === 'attendance'"
								>Attendance · {{ childName(item.student) }}</span
							>
							<span v-else-if="item.type === 'student_log'"
								>Student Log · {{ childName(item.student) }}</span
							>
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
				<div v-if="!prepItems.length" class="type-body text-ink/70">
					No preparation cues in this window.
				</div>
				<ul v-else class="space-y-2">
					<li
						v-for="(item, index) in prepItems"
						:key="`prep-${index}`"
						class="rounded-lg border border-line-soft bg-white p-3"
					>
						<p class="type-body-strong text-ink">{{ childName(item.student) }}</p>
						<p class="type-caption text-ink/70">{{ item.date }} · {{ item.source }}</p>
						<p class="type-body text-ink/80">{{ item.label }}</p>
					</li>
				</ul>
			</section>

			<section class="card-surface p-5">
				<h2 class="mb-3 type-h3 text-ink">Recent Activity</h2>
				<div v-if="!recentActivity.length" class="type-body text-ink/70">No recent activity.</div>
				<ul v-else class="space-y-2">
					<li
						v-for="(item, index) in recentActivity"
						:key="`recent-${index}`"
						class="rounded-lg border border-line-soft bg-white p-3"
					>
						<p class="type-body-strong text-ink">
							<span v-if="item.type === 'task_result'"
								>Task Result · {{ childName(item.student) }}</span
							>
							<span v-else-if="item.type === 'student_log'"
								>Student Log · {{ childName(item.student) }}</span
							>
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
						<p
							v-if="item.type === 'task_result' && item.published_by"
							class="type-caption text-ink/60"
						>
							Published by {{ item.published_by }}
						</p>
					</li>
				</ul>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';

import { getGuardianHomeSnapshot } from '@/lib/services/guardianHome/guardianHomeService';

import type { DueTaskChip } from '@/types/contracts/guardian/get_guardian_home_snapshot';
import type { Response as GuardianHomeSnapshot } from '@/types/contracts/guardian/get_guardian_home_snapshot';

const loading = ref<boolean>(true);
const errorMessage = ref<string>('');
const snapshot = ref<GuardianHomeSnapshot | null>(null);

const meta = computed(
	() =>
		snapshot.value?.meta ?? {
			generated_at: '',
			anchor_date: '',
			school_days: 7,
			guardian: { name: null },
		}
);
const counts = computed(
	() =>
		snapshot.value?.counts ?? {
			unread_communications: 0,
			unread_visible_student_logs: 0,
			upcoming_due_tasks: 0,
			upcoming_assessments: 0,
		}
);
const familyTimeline = computed(() => snapshot.value?.zones.family_timeline ?? []);
const attentionItems = computed(() => snapshot.value?.zones.attention_needed ?? []);
const prepItems = computed(() => snapshot.value?.zones.preparation_and_support ?? []);
const recentActivity = computed(() => snapshot.value?.zones.recent_activity ?? []);
const learningHighlights = computed(() => snapshot.value?.zones.learning_highlights ?? []);

const quickLinks = [
	{
		title: 'Course Selection',
		description: 'Confirm each child’s program choices before the deadline.',
		icon: 'check-square',
		to: { name: 'guardian-course-selection' },
	},
	{
		title: 'Activity Booking',
		description: 'Book and manage activities for all children.',
		icon: 'star',
		to: { name: 'guardian-activities' },
	},
	{
		title: 'Attendance',
		description: 'Review daily attendance across all children.',
		icon: 'calendar',
		to: { name: 'guardian-attendance' },
	},
	{
		title: 'Family Timeline',
		description: 'Review upcoming classes and day summaries.',
		icon: 'calendar',
		to: { name: 'guardian-home' },
	},
	{
		title: 'Policies',
		description: 'Review and acknowledge guardian policies in scope.',
		icon: 'shield',
		to: { name: 'guardian-policies' },
	},
	{
		title: 'Finance',
		description: 'See invoices and payment history for your family.',
		icon: 'credit-card',
		to: { name: 'guardian-finance' },
	},
	{
		title: 'Monitoring',
		description: 'Track visible logs and published results across children.',
		icon: 'file-text',
		to: { name: 'guardian-monitoring' },
	},
	{
		title: 'Showcase Portfolio',
		description: 'View approved showcase evidence by child.',
		icon: 'layers',
		to: { name: 'guardian-portfolio' },
	},
];

const childNameMap = computed(() => {
	const map = new Map<string, string>();
	for (const child of snapshot.value?.family.children ?? []) {
		map.set(child.student, child.full_name);
	}
	return map;
});

const childImageMap = computed(() => {
	const map = new Map<string, string>();
	for (const child of snapshot.value?.family.children ?? []) {
		if (child.student_image_url) {
			map.set(child.student, child.student_image_url);
		}
	}
	return map;
});

function childName(student: string): string {
	return childNameMap.value.get(student) ?? student;
}

function childImage(student: string): string {
	return childImageMap.value.get(student) ?? '';
}

function childInitials(student: string): string {
	const parts = childName(student).split(/\s+/).filter(Boolean).slice(0, 2);
	return parts.map(part => part[0]?.toUpperCase() || '').join('') || '?';
}

function chipTitles(chips: DueTaskChip[]): string {
	return chips.map(chip => chip.title).join(', ');
}

async function loadSnapshot() {
	loading.value = true;
	errorMessage.value = '';
	try {
		snapshot.value = await getGuardianHomeSnapshot({ school_days: 7 });
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		errorMessage.value = message || 'Unknown error';
	} finally {
		loading.value = false;
	}
}

onMounted(() => {
	void loadSnapshot();
});
</script>
