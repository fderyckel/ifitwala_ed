<!-- ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue -->
<template>
	<div class="portal-page student-hub-page">
		<header class="student-hub-hero">
			<div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">Student Hub</p>
					<h1 class="type-h1 text-ink">Welcome, {{ greetingName }}.</h1>
					<p class="type-body text-ink/70">
						See what is happening now, what work matters next, and where to continue learning.
					</p>
				</div>
				<div class="flex items-center gap-2">
					<button
						type="button"
						class="if-button if-button--quiet"
						@click="scrollToSection('calendar')"
					>
						Calendar
					</button>
					<button
						type="button"
						class="if-button if-button--quiet"
						@click="scrollToSection('quick-links')"
					>
						Quick Links
					</button>
					<button
						type="button"
						class="if-button if-button--quiet"
						:disabled="loadingHome"
						@click="loadHome"
					>
						Refresh
					</button>
				</div>
			</div>
		</header>

		<section
			v-if="homeError"
			class="student-hub-section border border-flame/30 bg-[var(--flame)]/5"
		>
			<p class="type-body-strong text-flame">Could not load your Hub.</p>
			<p class="mt-2 type-caption text-ink/70">{{ homeError }}</p>
		</section>

		<section
			v-if="policySummary.pending_count"
			class="student-hub-section student-hub-section--warm"
		>
			<div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">Action Needed</p>
					<h2 class="type-h2 text-ink">Policies need your acknowledgement</h2>
					<p class="mt-1 type-body text-ink/70">
						{{ policySummary.pending_count }}
						{{ policySummary.pending_count === 1 ? 'policy is' : 'policies are' }}
						waiting for your signature.
					</p>
				</div>
				<RouterLink :to="{ name: 'student-policies' }" class="if-button if-button--primary">
					Open Policies
				</RouterLink>
			</div>
			<div class="mt-4 grid gap-3 lg:grid-cols-3">
				<article
					v-for="item in policySummary.items"
					:key="item.policy_version"
					class="student-hub-card student-hub-card--warm"
				>
					<div class="flex items-start justify-between gap-3">
						<div>
							<p class="type-body-strong text-ink">
								{{ item.policy_title }}
								<span v-if="item.version_label" class="text-ink/60"
									>· {{ item.version_label }}</span
								>
							</p>
							<p v-if="item.description" class="mt-2 type-caption text-ink/70">
								{{ item.description }}
							</p>
						</div>
						<span class="chip">{{ item.status_label }}</span>
					</div>
				</article>
			</div>
		</section>

		<section class="student-hub-section student-hub-section--focus">
			<div class="flex items-center justify-between gap-3">
				<div>
					<p class="type-overline text-ink/60">Today</p>
					<h2 class="type-h2 text-ink">{{ orientationTitle }}</h2>
					<p class="mt-1 type-body text-ink/70">{{ orientationSubtitle }}</p>
				</div>
				<RouterLink :to="{ name: 'student-courses' }" class="if-button if-button--primary">
					My Courses
				</RouterLink>
			</div>

			<p v-if="daySummary" class="mt-4 type-caption text-ink/60">{{ daySummary }}</p>

			<div v-if="loadingHome" class="mt-5 type-body text-ink/70">
				Loading today’s learning plan...
			</div>

			<div
				v-else-if="currentClass"
				class="mt-5 student-hub-highlight student-hub-highlight--focus"
			>
				<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
					<div>
						<p class="type-overline text-ink/60">Current Class</p>
						<p class="mt-1 type-h3 text-ink">{{ currentClass.course_name }}</p>
						<p class="mt-2 type-body text-ink/70">
							{{ classSubtitle(currentClass) }}
						</p>
					</div>
					<RouterLink :to="linkFor(currentClass.href)" class="if-button if-button--primary">
						Open Class
					</RouterLink>
				</div>
			</div>

			<div v-else-if="nextClass" class="mt-5 student-hub-highlight student-hub-highlight--warm">
				<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
					<div>
						<p class="type-overline text-ink/60">Next Up</p>
						<p class="mt-1 type-h3 text-ink">{{ nextClass.course_name }}</p>
						<p class="mt-2 type-body text-ink/70">
							{{ classSubtitle(nextClass) }}
						</p>
					</div>
					<RouterLink :to="linkFor(nextClass.href)" class="if-button if-button--primary">
						Prepare
					</RouterLink>
				</div>
			</div>

			<div
				v-else-if="nextLearningStep"
				class="mt-5 student-hub-highlight"
				:class="nextLearningStepHighlightClass(nextLearningStep)"
			>
				<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
					<div>
						<p class="type-overline text-ink/60">Continue Learning</p>
						<div class="mt-1 flex flex-wrap items-center gap-2">
							<p class="type-h3 text-ink">{{ nextLearningStep.title }}</p>
							<span v-if="nextLearningStep.status_label" class="chip">
								{{ nextLearningStep.status_label }}
							</span>
						</div>
						<p class="mt-2 type-body text-ink/70">{{ nextLearningStep.subtitle }}</p>
					</div>
					<RouterLink
						v-if="nextLearningStep.can_open && nextLearningStep.href"
						:to="linkFor(nextLearningStep.href)"
						class="if-button if-button--primary"
					>
						{{ nextLearningStepButtonLabel }}
					</RouterLink>
					<button v-else type="button" class="if-button if-button--primary" disabled>
						{{ nextLearningStepButtonLabel }}
					</button>
				</div>
			</div>

			<div v-else class="mt-5 student-hub-empty">
				<p class="type-body text-ink/70">No classes or work items are available yet.</p>
			</div>
		</section>

		<section class="space-y-4">
			<div class="flex items-center justify-between">
				<div>
					<p class="type-overline text-ink/60">My Work Board</p>
					<h2 class="type-h2 text-ink">What to work on next</h2>
				</div>
				<p class="type-caption text-ink/60">
					System-curated from scheduled work and official outcome state.
				</p>
			</div>

			<div v-if="loadingHome" class="student-hub-section type-body text-ink/70">
				Loading work board...
			</div>

			<div v-else class="grid gap-4 xl:grid-cols-4">
				<section
					v-for="lane in boardLanes"
					:key="lane.key"
					class="student-hub-lane"
					:class="laneSurfaceClass(lane.key)"
				>
					<div class="mb-4 flex items-center justify-between gap-3">
						<div>
							<h3 class="type-h3 text-ink">{{ lane.title }}</h3>
							<p class="type-caption text-ink/60">{{ lane.description }}</p>
						</div>
						<span class="chip">{{ lane.items.length }}</span>
					</div>

					<div v-if="!lane.items.length" class="student-hub-empty">
						<p class="type-caption text-ink/60">{{ lane.empty }}</p>
					</div>

					<div v-else class="space-y-3">
						<RouterLink
							v-for="item in lane.items"
							:key="item.task_delivery"
							:to="linkFor(item.href)"
							class="student-hub-card student-hub-card--interactive block"
							:class="workItemSurfaceClass(lane.key)"
						>
							<div class="flex flex-wrap items-center gap-2">
								<p class="type-body-strong text-ink">{{ item.title }}</p>
								<span class="chip">{{ item.status_label }}</span>
								<span v-if="item.task_type" class="chip">{{ item.task_type }}</span>
							</div>
							<p class="mt-2 type-caption text-ink/70">
								{{ item.course_name || item.course || 'Course' }}
							</p>
							<p class="mt-2 type-body text-ink/80">{{ workItemSummary(item) }}</p>
							<p class="mt-3 type-caption text-ink/60">{{ item.lane_reason }}</p>
						</RouterLink>
					</div>
				</section>
			</div>
		</section>

		<section class="student-hub-section student-hub-section--warm">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">Communications</p>
					<h2 class="type-h3 text-ink">Recent updates across your student Hub</h2>
					<p class="type-caption text-ink/70">
						Class, activity, and school updates stay connected to where they belong.
					</p>
				</div>
				<RouterLink :to="linkFor(communicationsCenterHref)" class="if-button if-button--primary">
					Open communication center
				</RouterLink>
			</div>

			<div v-if="!communicationHighlights.length" class="mt-4 student-hub-empty">
				<p class="type-body text-ink/70">
					No student-facing updates are visible right now. New class, activity, and school messages
					will appear here.
				</p>
			</div>

			<div v-else class="mt-4 grid gap-3 lg:grid-cols-3">
				<RouterLink
					v-for="item in communicationHighlights"
					:key="item.item_id || `${item.kind}-${item.title}`"
					:to="linkFor(item.href)"
					class="group student-hub-card student-hub-card--interactive student-hub-card--warm"
				>
					<div class="flex items-start justify-between gap-3">
						<div>
							<p class="type-caption text-ink/60">{{ item.source_label || 'Update' }}</p>
							<p class="mt-2 type-body-strong text-ink">{{ item.title }}</p>
						</div>
						<FeatherIcon
							name="arrow-up-right"
							class="h-4 w-4 shrink-0 text-ink/35 transition group-hover:text-jacaranda"
						/>
					</div>
					<p v-if="item.subtitle" class="mt-2 type-body text-ink/80">{{ item.subtitle }}</p>
					<p v-if="item.publish_at" class="mt-3 type-caption text-ink/60">
						{{ communicationDateLabel(item.publish_at) }}
					</p>
					<p class="mt-3 type-caption text-jacaranda">
						{{ item.href_label || 'Open' }}
					</p>
				</RouterLink>
			</div>
		</section>

		<section class="space-y-4">
			<div class="flex items-center justify-between">
				<div>
					<p class="type-overline text-ink/60">Timeline</p>
					<h2 class="type-h2 text-ink">Coming up</h2>
				</div>
				<RouterLink :to="{ name: 'student-courses' }" class="if-button if-button--primary">
					Open Courses
				</RouterLink>
			</div>

			<div v-if="loadingHome" class="student-hub-section type-body text-ink/70">
				Loading timeline...
			</div>

			<div v-else-if="!timelineDays.length" class="student-hub-empty">
				<p class="type-body text-ink/70">
					No dated learning events are scheduled in the current window.
				</p>
			</div>

			<div v-else class="space-y-4">
				<section
					v-for="day in timelineDays"
					:key="day.date"
					class="student-hub-section student-hub-section--support"
				>
					<div class="mb-4 flex items-center justify-between">
						<h3 class="type-h3 text-ink">{{ formatDayLabel(day.date) }}</h3>
						<span class="chip">{{ day.items.length }} items</span>
					</div>
					<div class="space-y-3">
						<RouterLink
							v-for="item in day.items"
							:key="`${day.date}-${item.kind}-${item.title}-${item.date_time}`"
							:to="linkFor(item.href)"
							class="student-hub-card student-hub-card--interactive block"
							:class="timelineItemSurfaceClass(item.kind)"
						>
							<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
								<div>
									<p class="type-body-strong text-ink">{{ item.title }}</p>
									<p class="mt-1 type-caption text-ink/70">{{ item.subtitle }}</p>
								</div>
								<div class="flex flex-wrap gap-2">
									<span class="chip">{{ timelineKindLabel(item.kind) }}</span>
									<span v-if="item.time_label" class="chip">{{ item.time_label }}</span>
									<span class="chip">{{ item.status_label }}</span>
								</div>
							</div>
						</RouterLink>
					</div>
				</section>
			</div>
		</section>

		<section id="student-home-calendar" class="student-hub-section student-hub-section--support">
			<h2 class="mb-3 type-h3 text-ink">Calendar</h2>
			<StudentCalendar :auto-refresh-interval="30 * 60 * 1000" />
		</section>

		<section id="student-home-quick-links" class="student-hub-section">
			<h2 class="mb-3 type-h3 text-ink">Quick Links</h2>
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
				<RouterLink
					v-for="item in quickLinks"
					:key="item.title"
					:to="item.to"
					class="action-tile student-hub-action-tile group"
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
import { formatLocalizedDate, formatLocalizedDateTime } from '@/lib/datetime';
import { getStudentHubHome } from '@/lib/services/student/studentLearningHubService';
import type {
	NextLearningStep,
	Response as StudentHubHomeResponse,
	RouteTarget,
	StudentCommunicationSummary,
	TimelineDay,
	WorkItem,
	TodayClass,
} from '@/types/contracts/student_hub/get_student_hub_home';

type BrowserSessionUser = {
	fullname?: string | null;
	email?: string | null;
};

function getSessionUserInfo(): BrowserSessionUser {
	const browserWindow = window as Window & {
		frappe?: {
			session?: {
				user_info?: BrowserSessionUser | null;
			} | null;
		};
	};

	return browserWindow.frappe?.session?.user_info || { fullname: 'Student' };
}

const sessionUser = computed(() => getSessionUserInfo());

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

const nextLearningStep = computed<NextLearningStep | null>(
	() => homePayload.value?.learning?.next_learning_step ?? null
);
const policySummary = computed(
	() =>
		homePayload.value?.policies ?? {
			pending_count: 0,
			items: [],
		}
);
const currentClass = computed<TodayClass | null>(
	() => homePayload.value?.learning?.orientation?.current_class ?? null
);
const nextClass = computed<TodayClass | null>(
	() => homePayload.value?.learning?.orientation?.next_class ?? null
);
const workBoard = computed(() => {
	return (
		homePayload.value?.learning?.work_board ?? {
			now: [],
			soon: [],
			later: [],
			done: [],
		}
	);
});
const timelineDays = computed<TimelineDay[]>(() => homePayload.value?.learning?.timeline ?? []);
const communicationsCenterHref = computed<RouteTarget>(
	() => homePayload.value?.communications?.center_href || { name: 'student-communications' }
);
const communicationHighlights = computed<StudentCommunicationSummary[]>(() => {
	const items = [
		homePayload.value?.communications?.latest_course_update || null,
		homePayload.value?.communications?.latest_activity_update || null,
		homePayload.value?.communications?.latest_school_update || null,
	];
	return items.filter((item): item is StudentCommunicationSummary => Boolean(item));
});
const daySummary = computed(() => {
	const date = homePayload.value?.meta?.date ?? null;
	const weekday = homePayload.value?.meta?.weekday ?? null;
	if (date && weekday) return `${weekday}, ${date}`;
	return weekday || date || '';
});

const orientationTitle = computed(() => {
	if (currentClass.value) return 'You are in class';
	if (nextClass.value) return 'Next class is coming up';
	if (nextLearningStep.value && !nextLearningStep.value.can_open) {
		return 'A course is still being prepared';
	}
	if (nextLearningStep.value) return 'Continue your learning';
	return 'Your Hub is clear';
});

const orientationSubtitle = computed(() => {
	if (currentClass.value) return classSubtitle(currentClass.value);
	if (nextClass.value) return classSubtitle(nextClass.value);
	if (nextLearningStep.value) return nextLearningStep.value.subtitle;
	return 'We will place upcoming classes and work here as they become available.';
});

const boardLanes = computed(() => [
	{
		key: 'now',
		title: 'Now',
		description: 'Small active set',
		empty: 'No urgent work is in focus right now.',
		items: workBoard.value.now,
	},
	{
		key: 'soon',
		title: 'Soon',
		description: 'This week',
		empty: 'Nothing is queued for the next few days.',
		items: workBoard.value.soon,
	},
	{
		key: 'later',
		title: 'Later',
		description: 'Plan ahead',
		empty: 'No later work is visible yet.',
		items: workBoard.value.later,
	},
	{
		key: 'done',
		title: 'Done',
		description: 'Recent closure',
		empty: 'Completed and submitted work will appear here.',
		items: workBoard.value.done,
	},
]);

const nextLearningStepButtonLabel = computed(() => {
	return nextLearningStep.value?.cta_label || 'Open course';
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

function linkFor(target?: RouteTarget | null) {
	return target || { name: 'student-courses' };
}

function classSubtitle(course: TodayClass): string {
	const parts: string[] = [];
	if (course.student_group_name && course.student_group_name !== course.course_name) {
		parts.push(course.student_group_name);
	}
	const timeLabel = (course.time_slots || [])
		.map(slot => slot.time_range)
		.filter((value): value is string => Boolean(value))
		.join(', ');
	if (timeLabel) {
		parts.push(timeLabel);
	}
	if (course.instructors?.length) {
		parts.push(course.instructors.join(', '));
	}
	return parts.join(' · ') || 'Scheduled class';
}

function workItemSummary(item: WorkItem): string {
	if (item.outcome?.completed_on) {
		return `Completed ${formatLocalizedDateTime(item.outcome.completed_on, { fallback: '' })}`;
	}
	if (item.due_date) {
		return `Due ${formatLocalizedDateTime(item.due_date, { fallback: '' })}`;
	}
	if (item.available_from) {
		return `Available ${formatLocalizedDateTime(item.available_from, { fallback: '' })}`;
	}
	if (item.lock_date) {
		return `Locks ${formatLocalizedDateTime(item.lock_date, { fallback: '' })}`;
	}
	return 'Open inside the linked course context.';
}

function formatDayLabel(value: string): string {
	return formatLocalizedDate(value, {
		fallback: value,
		includeWeekday: true,
		includeYear: false,
		month: 'long',
	});
}

function timelineKindLabel(kind: string): string {
	if (kind === 'scheduled_class') return 'Class';
	if (kind === 'task_due') return 'Due';
	return 'Opens';
}

function communicationDateLabel(value: string): string {
	return formatLocalizedDateTime(value, { fallback: value });
}

function laneSurfaceClass(key: string): string {
	if (key === 'now') return 'student-hub-lane--now';
	if (key === 'soon') return 'student-hub-lane--soon';
	if (key === 'done') return 'student-hub-lane--done';
	return 'student-hub-lane--later';
}

function workItemSurfaceClass(key: string): string {
	if (key === 'now') return 'student-hub-card--focus';
	if (key === 'soon') return 'student-hub-card--warm';
	if (key === 'done') return 'student-hub-card--success';
	return 'student-hub-card--neutral';
}

function timelineItemSurfaceClass(kind: string): string {
	if (kind === 'task_due') return 'student-hub-card--focus';
	if (kind === 'scheduled_class') return 'student-hub-card--warm';
	return 'student-hub-card--neutral';
}

function nextLearningStepHighlightClass(step: NextLearningStep): string {
	if (!step.can_open) return 'student-hub-highlight--warm';
	return 'student-hub-highlight--focus';
}

function scrollToSection(section: 'calendar' | 'quick-links') {
	const targetId = section === 'calendar' ? 'student-home-calendar' : 'student-home-quick-links';
	document.getElementById(targetId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

onMounted(() => {
	loadHome();
});

const quickLinks = [
	{
		title: 'Policies',
		description: 'Review and acknowledge active student policies.',
		icon: 'shield',
		to: { name: 'student-policies' },
	},
	{
		title: 'Course Selection',
		description: 'Review required rows and confirm your program choices.',
		icon: 'check-square',
		to: { name: 'student-course-selection' },
	},
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
		title: 'Communication Center',
		description: 'See all class, activity, and school updates together.',
		icon: 'message-square',
		to: { name: 'student-communications' },
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
