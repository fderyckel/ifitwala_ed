<!-- ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue -->
<template>
	<div class="space-y-6">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">Student Portal</p>
					<h1 class="type-h1 text-ink">Welcome, {{ greetingName }}.</h1>
					<p class="type-body text-ink/70">
						Keep your day clear with one-click access to learning and activities.
					</p>
				</div>
				<div class="flex items-center gap-2">
					<RouterLink :to="{ name: 'student-activities' }" class="if-action">
						Book Activities
					</RouterLink>
					<button type="button" class="if-action" :disabled="loadingHome" @click="loadHome">
						Refresh
					</button>
				</div>
			</div>
		</header>

		<section class="card-surface p-5">
			<div class="mb-3 flex items-center justify-between">
				<h2 class="type-h3 text-ink">Next Learning Step</h2>
				<RouterLink :to="{ name: 'student-courses' }" class="if-action">My Courses</RouterLink>
			</div>

			<div v-if="loadingHome" class="type-body text-ink/70">Loading next step...</div>
			<div v-else-if="homeError" class="rounded-lg border border-line-soft bg-surface-soft p-3">
				<p class="type-body-strong text-flame">Could not load your Hub.</p>
				<p class="type-caption text-ink/70">{{ homeError }}</p>
			</div>
			<RouterLink
				v-else-if="nextLearningStep"
				:to="nextLearningStep.href"
				class="block rounded-xl border border-line-soft bg-surface-soft p-4 transition hover:shadow-soft"
			>
				<p class="type-overline text-ink/60">
					{{ nextLearningStep.kind === 'scheduled_class' ? 'Scheduled Class' : 'Course' }}
				</p>
				<p class="mt-1 type-body-strong text-ink">{{ nextLearningStep.title }}</p>
				<p class="mt-1 type-caption text-ink/70">{{ nextLearningStep.subtitle }}</p>
			</RouterLink>
			<div v-else class="rounded-lg border border-line-soft bg-surface-soft p-3">
				<p class="type-body text-ink/70">No learning step is available yet.</p>
			</div>
		</section>

		<section class="card-surface p-5">
			<div class="mb-3 flex items-center justify-between">
				<h2 class="type-h3 text-ink">Today’s Classes</h2>
				<RouterLink :to="{ name: 'student-courses' }" class="if-action">All Courses</RouterLink>
			</div>

			<p v-if="daySummary" class="mb-3 type-caption text-ink/70">{{ daySummary }}</p>

			<div v-if="loadingHome" class="type-body text-ink/70">Loading today’s classes...</div>
			<div v-else-if="homeError" class="rounded-lg border border-line-soft bg-surface-soft p-3">
				<p class="type-body-strong text-flame">Could not load classes.</p>
				<p class="type-caption text-ink/70">{{ homeError }}</p>
			</div>
			<div
				v-else-if="!todayCourses.length"
				class="rounded-lg border border-line-soft bg-surface-soft p-3"
			>
				<p class="type-body text-ink/70">No classes scheduled for today.</p>
			</div>
			<div v-else class="space-y-3">
				<RouterLink
					v-for="course in todayCourses"
					:key="course.student_group"
					:to="
						course.href ?? { name: 'student-course-detail', params: { course_id: course.course } }
					"
					class="block rounded-xl border border-line-soft bg-surface-soft p-4 transition hover:shadow-soft"
				>
					<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
						<div>
							<p class="type-body-strong text-ink">{{ course.course_name }}</p>
							<p
								v-if="
									course.student_group_name && course.student_group_name !== course.course_name
								"
								class="type-caption text-ink/70"
							>
								{{ course.student_group_name }}
							</p>
							<p v-if="course.instructors?.length" class="type-caption text-ink/70">
								{{ course.instructors.length > 1 ? 'Instructors' : 'Instructor' }}:
								{{ course.instructors.join(', ') }}
							</p>
						</div>
						<div class="flex flex-wrap gap-2">
							<span
								v-for="(slot, idx) in course.time_slots"
								:key="`${course.student_group}-${idx}`"
								class="chip"
							>
								{{ slot.block_number ? `B${slot.block_number}` : 'Slot' }}
								<span v-if="slot.time_range">· {{ slot.time_range }}</span>
							</span>
						</div>
					</div>
				</RouterLink>
			</div>
		</section>

		<section class="card-surface p-5">
			<h2 class="mb-3 type-h3 text-ink">Calendar</h2>
			<StudentCalendar :auto-refresh-interval="30 * 60 * 1000" />
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
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';

import StudentCalendar from '@/components/calendar/StudentCalendar.vue';
import { getStudentHubHome } from '@/lib/services/student/studentLearningHubService';
import type {
	NextLearningStep,
	Response as StudentHubHomeResponse,
	TodayClass,
} from '@/types/contracts/student_hub/get_student_hub_home';

const sessionUser = computed(() => window.frappe?.session?.user_info || { fullname: 'Student' });

const homePayload = ref<StudentHubHomeResponse | null>(null);
const loadingHome = ref(false);
const homeError = ref('');

const greetingName = computed(() => {
	const fromHub = (homePayload.value?.identity?.display_name || '').trim();
	if (fromHub) return fromHub;

	const fallbackFull = String(sessionUser.value?.fullname || '').trim();
	if (fallbackFull) return fallbackFull.split(' ')[0] || 'Student';

	return 'Student';
});

const todayCourses = computed<TodayClass[]>(
	() => homePayload.value?.learning?.today_classes ?? []
);
const nextLearningStep = computed<NextLearningStep | null>(
	() => homePayload.value?.learning?.next_learning_step ?? null
);
const daySummary = computed(() => {
	const date = homePayload.value?.meta?.date ?? null;
	const weekday = homePayload.value?.meta?.weekday ?? null;
	if (date && weekday) return `${weekday}, ${date}`;
	return weekday || date || '';
});

async function loadHome() {
	loadingHome.value = true;
	homeError.value = '';
	try {
		homePayload.value = await getStudentHubHome();
	} catch (error: unknown) {
		homePayload.value = null;
		if (error instanceof Error && error.message) {
			homeError.value = error.message;
		} else if (typeof error === 'string' && error) {
			homeError.value = error;
		} else {
			homeError.value = 'Unable to load your learning Hub.';
		}
	} finally {
		loadingHome.value = false;
	}
}

onMounted(() => {
	loadHome();
});

const quickLinks = [
	{
		title: 'Activity Booking',
		description: 'Browse and book extra-curricular activities.',
		icon: 'star',
		to: { name: 'student-activities' },
	},
	{
		title: 'My Courses',
		description: 'Open your course spaces.',
		icon: 'book-open',
		to: { name: 'student-courses' },
	},
	{
		title: 'Portfolio & Journal',
		description: 'Curate showcase evidence and reflections.',
		icon: 'layers',
		to: { name: 'student-portfolio' },
	},
	{
		title: 'Student Log',
		description: 'View notes shared with you.',
		icon: 'file-text',
		to: { name: 'student-logs' },
	},
	{
		title: 'Profile',
		description: 'Manage your personal details.',
		icon: 'user',
		to: { name: 'student-profile' },
	},
];
</script>
