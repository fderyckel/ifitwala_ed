<!-- ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue -->
<template>
	<div class="space-y-6 p-4 sm:p-6 lg:p-8">
		<div>
			<RouterLink
				:to="{ name: 'student-courses' }"
				class="inline-flex items-center type-body text-ink/70 transition hover:text-ink"
				aria-label="Back to courses"
			>
				<span class="mr-2">←</span>
				Back to Courses
			</RouterLink>
		</div>

		<div v-if="loading" class="card-surface p-6">
			<p class="type-body text-ink/70">Loading course space...</p>
		</div>

		<div
			v-else-if="errorMessage"
			class="card-surface border border-flame/30 bg-[var(--flame)]/5 p-6"
		>
			<p class="type-body-strong text-flame">Could not load this course.</p>
			<p class="mt-2 type-caption text-ink/70">{{ errorMessage }}</p>
		</div>

		<template v-else-if="courseDetail">
			<header class="card-surface overflow-hidden">
				<div class="grid gap-6 lg:grid-cols-[220px,1fr]">
					<div class="bg-surface-soft">
						<img
							:src="courseDetail.course.course_image || PLACEHOLDER"
							:alt="courseDetail.course.course_name"
							class="h-full w-full object-cover"
							loading="lazy"
						/>
					</div>
					<div class="p-6">
						<p class="type-overline text-ink/60">My Course</p>
						<h1 class="mt-2 type-h1 text-ink">{{ courseDetail.course.course_name }}</h1>
						<p v-if="courseDetail.course.course_group" class="mt-2 type-caption text-ink/70">
							{{ courseDetail.course.course_group }}
						</p>
						<p v-if="courseDetail.course.description" class="mt-4 type-body text-ink/80">
							{{ courseDetail.course.description }}
						</p>
						<div class="mt-4 flex flex-wrap gap-2">
							<span class="chip">{{ courseDetail.curriculum.counts.units }} units</span>
							<span class="chip">{{ courseDetail.curriculum.counts.lessons }} lessons</span>
							<span class="chip">{{ courseDetail.curriculum.counts.activities }} activities</span>
							<span class="chip">{{ totalLinkedTasks }} linked tasks</span>
						</div>
					</div>
				</div>
			</header>

			<section class="grid gap-6 xl:grid-cols-[320px,minmax(0,1fr)]">
				<aside class="space-y-6 xl:sticky xl:top-6 xl:self-start">
					<section class="card-surface p-5">
						<div class="mb-3 flex items-center justify-between">
							<h2 class="type-h3 text-ink">Entry Context</h2>
							<span class="chip">{{ courseDetail.deep_link.resolved.source }}</span>
						</div>
						<p class="type-body text-ink/80">{{ deepLinkSummary }}</p>
						<p
							v-if="courseDetail.deep_link.resolved.lesson_instance"
							class="mt-3 rounded-xl border border-line-soft bg-surface-soft p-3 type-caption text-ink/70"
						>
							This view was opened from lesson instance
							{{ courseDetail.deep_link.resolved.lesson_instance }}.
						</p>
						<p
							v-if="courseDetail.access.student_groups.length"
							class="mt-3 type-caption text-ink/70"
						>
							Available in
							{{ courseDetail.access.student_groups.length }}
							{{ courseDetail.access.student_groups.length > 1 ? 'groups' : 'group' }}.
						</p>
					</section>

					<section class="card-surface p-5">
						<div class="mb-4 flex items-center justify-between">
							<h2 class="type-h3 text-ink">Course Map</h2>
							<span class="chip">{{ lessonSequence.length }} lessons</span>
						</div>

						<div
							v-if="!units.length"
							class="rounded-xl border border-dashed border-line-soft p-4 type-body text-ink/70"
						>
							No learning units are available for this course yet.
						</div>

						<div v-else class="space-y-4">
							<div v-for="unit in units" :key="unit.name" class="space-y-2">
								<button
									type="button"
									class="w-full rounded-2xl border p-4 text-left transition"
									:class="
										isActiveUnit(unit.name)
											? 'border-jacaranda bg-jacaranda/10 shadow-soft'
											: 'border-line-soft bg-surface-soft hover:border-jacaranda/30'
									"
									@click="openUnit(unit)"
								>
									<p class="type-overline text-ink/60">Unit {{ unit.unit_order ?? '—' }}</p>
									<p class="mt-1 type-body-strong text-ink">{{ unit.unit_name }}</p>
									<p class="mt-1 type-caption text-ink/70">
										{{ unit.lessons.length }} lessons
										<span v-if="unit.estimated_duration">· {{ unit.estimated_duration }}</span>
									</p>
								</button>

								<div v-if="unit.lessons.length" class="space-y-2 border-l border-line-soft pl-3">
									<button
										v-for="lesson in unit.lessons"
										:key="lesson.name"
										type="button"
										class="w-full rounded-xl border p-3 text-left transition"
										:class="
											isActiveLesson(lesson.name)
												? 'border-jacaranda bg-white shadow-soft'
												: 'border-line-soft bg-white/70 hover:border-jacaranda/30'
										"
										:aria-current="isActiveLesson(lesson.name) ? 'true' : undefined"
										@click="openLesson(unit.name, lesson.name)"
									>
										<p class="type-body-strong text-ink">{{ lesson.title }}</p>
										<p class="mt-1 type-caption text-ink/70">
											{{ lesson.lesson_type || 'Lesson' }}
											<span v-if="lesson.duration">· {{ lesson.duration }} periods</span>
											<span v-if="lesson.lesson_activities.length">
												· {{ lesson.lesson_activities.length }} activities
											</span>
										</p>
									</button>
								</div>
							</div>
						</div>
					</section>

					<section v-if="courseDetail.curriculum.course_tasks.length" class="card-surface p-5">
						<div class="mb-4 flex items-center justify-between">
							<h2 class="type-h3 text-ink">Course-Level Work</h2>
							<span class="chip">{{ courseDetail.curriculum.course_tasks.length }} items</span>
						</div>

						<div class="space-y-3">
							<article
								v-for="task in courseDetail.curriculum.course_tasks"
								:key="task.task"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<div class="flex flex-wrap items-center gap-2">
									<p class="type-body-strong text-ink">{{ task.title }}</p>
									<span v-if="task.task_type" class="chip">{{ task.task_type }}</span>
									<span v-if="task.deliveries.length" class="chip">
										{{ task.deliveries.length }}
										{{ task.deliveries.length > 1 ? 'deliveries' : 'delivery' }}
									</span>
								</div>
								<div v-if="task.deliveries.length" class="mt-3 space-y-2">
									<div
										v-for="delivery in task.deliveries"
										:key="delivery.task_delivery"
										class="rounded-xl border border-line-soft bg-white p-3"
									>
										<div class="flex flex-wrap gap-2">
											<span class="chip">{{ delivery.student_group }}</span>
											<span v-if="delivery.delivery_mode" class="chip">
												{{ delivery.delivery_mode }}
											</span>
										</div>
										<p class="mt-2 type-caption text-ink/70">
											{{ deliverySummary(delivery) }}
										</p>
									</div>
								</div>
							</article>
						</div>
					</section>
				</aside>

				<div class="space-y-6">
					<section v-if="activeUnit" class="card-surface p-6">
						<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
							<div>
								<p class="type-overline text-ink/60">Current Unit</p>
								<h2 class="mt-2 type-h2 text-ink">{{ activeUnit.unit_name }}</h2>
								<p class="mt-2 type-body text-ink/80">
									{{ activeUnit.lessons.length }} lessons in this chapter.
								</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<span v-if="activeUnit.unit_status" class="chip">{{
									activeUnit.unit_status
								}}</span>
								<span v-if="activeUnit.estimated_duration" class="chip">
									{{ activeUnit.estimated_duration }}
								</span>
								<span v-if="activeUnit.linked_tasks.length" class="chip">
									{{ activeUnit.linked_tasks.length }} unit tasks
								</span>
							</div>
						</div>

						<p v-if="activeUnit.unit_overview" class="mt-4 type-body text-ink/80">
							{{ activeUnit.unit_overview }}
						</p>

						<div
							v-if="activeUnit.essential_understanding || activeUnit.misconceptions"
							class="mt-5 grid gap-4 lg:grid-cols-2"
						>
							<div
								v-if="activeUnit.essential_understanding"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Essential Understanding</p>
								<p class="mt-2 type-body text-ink/80">
									{{ activeUnit.essential_understanding }}
								</p>
							</div>
							<div
								v-if="activeUnit.misconceptions"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Common Misconceptions</p>
								<p class="mt-2 type-body text-ink/80">{{ activeUnit.misconceptions }}</p>
							</div>
						</div>
					</section>

					<section v-if="activeLesson" class="card-surface p-6">
						<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
							<div>
								<p class="type-overline text-ink/60">Current Lesson</p>
								<h2 class="mt-2 type-h2 text-ink">{{ activeLesson.title }}</h2>
								<p class="mt-2 type-body text-ink/80">
									Lesson {{ activeLessonOrdinal }} of {{ lessonSequence.length }} in this course.
								</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<span v-if="activeLesson.lesson_type" class="chip">
									{{ activeLesson.lesson_type }}
								</span>
								<span v-if="activeLesson.duration" class="chip">
									{{ activeLesson.duration }} periods
								</span>
								<span v-if="activeLesson.start_date" class="chip">
									Starts {{ formatLessonDate(activeLesson.start_date) }}
								</span>
								<span class="chip"> {{ activeLesson.lesson_activities.length }} activities </span>
							</div>
						</div>

						<div class="mt-5 grid gap-3 md:grid-cols-2">
							<button
								type="button"
								class="rounded-2xl border p-4 text-left transition"
								:class="
									adjacentLessons.previous
										? 'border-line-soft bg-surface-soft hover:border-jacaranda/30'
										: 'cursor-not-allowed border-line-soft bg-surface-soft/60 text-ink/40'
								"
								:disabled="!adjacentLessons.previous"
								@click="goToAdjacent(adjacentLessons.previous)"
							>
								<p class="type-overline text-ink/60">Previous Lesson</p>
								<p class="mt-1 type-body-strong text-ink">
									{{ adjacentLessons.previous?.lesson.title || 'Start of course' }}
								</p>
							</button>
							<button
								type="button"
								class="rounded-2xl border p-4 text-left transition"
								:class="
									adjacentLessons.next
										? 'border-line-soft bg-surface-soft hover:border-jacaranda/30'
										: 'cursor-not-allowed border-line-soft bg-surface-soft/60 text-ink/40'
								"
								:disabled="!adjacentLessons.next"
								@click="goToAdjacent(adjacentLessons.next)"
							>
								<p class="type-overline text-ink/60">Next Lesson</p>
								<p class="mt-1 type-body-strong text-ink">
									{{ adjacentLessons.next?.lesson.title || 'End of course' }}
								</p>
							</button>
						</div>
					</section>

					<section v-if="activeUnit && activeUnit.lessons.length > 1" class="card-surface p-5">
						<div class="mb-4 flex items-center justify-between">
							<h2 class="type-h3 text-ink">Lesson Sequence</h2>
							<span class="chip">{{ activeUnit.lessons.length }} lessons</span>
						</div>
						<div class="grid gap-3 lg:grid-cols-2">
							<button
								v-for="lesson in activeUnit.lessons"
								:key="lesson.name"
								type="button"
								class="rounded-2xl border p-4 text-left transition"
								:class="
									isActiveLesson(lesson.name)
										? 'border-jacaranda bg-jacaranda/10 shadow-soft'
										: 'border-line-soft bg-surface-soft hover:border-jacaranda/30'
								"
								@click="openLesson(activeUnit.name, lesson.name)"
							>
								<p class="type-body-strong text-ink">{{ lesson.title }}</p>
								<p class="mt-1 type-caption text-ink/70">
									{{ lesson.lesson_type || 'Lesson' }}
									<span v-if="lesson.duration">· {{ lesson.duration }} periods</span>
								</p>
							</button>
						</div>
					</section>

					<section v-if="activeUnit?.linked_tasks.length" class="card-surface p-5">
						<div class="mb-4 flex items-center justify-between">
							<h2 class="type-h3 text-ink">Unit Work</h2>
							<span class="chip">{{ activeUnit.linked_tasks.length }} items</span>
						</div>
						<div class="space-y-3">
							<article
								v-for="task in activeUnit.linked_tasks"
								:key="task.task"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<div class="flex flex-wrap items-center gap-2">
									<p class="type-body-strong text-ink">{{ task.title }}</p>
									<span v-if="task.task_type" class="chip">{{ task.task_type }}</span>
								</div>
								<div v-if="task.deliveries.length" class="mt-3 space-y-2">
									<div
										v-for="delivery in task.deliveries"
										:key="delivery.task_delivery"
										class="rounded-xl border border-line-soft bg-white p-3"
									>
										<p class="type-caption text-ink/70">{{ deliverySummary(delivery) }}</p>
									</div>
								</div>
							</article>
						</div>
					</section>

					<section v-if="activeLesson?.linked_tasks.length" class="card-surface p-5">
						<div class="mb-4 flex items-center justify-between">
							<h2 class="type-h3 text-ink">Lesson Work</h2>
							<span class="chip">{{ activeLesson.linked_tasks.length }} items</span>
						</div>
						<div class="space-y-3">
							<article
								v-for="task in activeLesson.linked_tasks"
								:key="task.task"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<div class="flex flex-wrap items-center gap-2">
									<p class="type-body-strong text-ink">{{ task.title }}</p>
									<span v-if="task.task_type" class="chip">{{ task.task_type }}</span>
								</div>
								<div v-if="task.deliveries.length" class="mt-3 space-y-2">
									<div
										v-for="delivery in task.deliveries"
										:key="delivery.task_delivery"
										class="rounded-xl border border-line-soft bg-white p-3"
									>
										<p class="type-caption text-ink/70">{{ deliverySummary(delivery) }}</p>
									</div>
								</div>
							</article>
						</div>
					</section>

					<section v-if="activeLesson" class="card-surface p-5">
						<div class="mb-4 flex items-center justify-between">
							<h2 class="type-h3 text-ink">Lesson Activities</h2>
							<span class="chip">{{ activeLesson.lesson_activities.length }} steps</span>
						</div>

						<div
							v-if="!activeLesson.lesson_activities.length"
							class="rounded-2xl border border-dashed border-line-soft p-4 type-body text-ink/70"
						>
							No lesson activities are defined for this lesson yet.
						</div>

						<div v-else class="space-y-4">
							<article
								v-for="(activity, index) in activeLesson.lesson_activities"
								:key="activity.name"
								class="rounded-2xl border p-5"
								:class="
									activity.is_required
										? 'border-jacaranda/30 bg-jacaranda/5'
										: 'border-line-soft bg-surface-soft'
								"
							>
								<div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
									<div>
										<p class="type-overline text-ink/60">Activity {{ index + 1 }}</p>
										<h3 class="mt-1 type-h3 text-ink">
											{{ activity.title || activity.activity_type || 'Activity' }}
										</h3>
										<p class="mt-1 type-caption text-ink/70">
											{{ activity.activity_type || 'Planned Activity' }}
											<span v-if="activity.estimated_duration">
												· {{ activity.estimated_duration }} minutes
											</span>
											<span v-if="activity.is_required">· Required</span>
										</p>
									</div>
									<div class="flex flex-wrap gap-2">
										<span v-if="activity.is_required" class="chip">Required</span>
										<span v-if="activity.activity_type" class="chip">
											{{ activity.activity_type }}
										</span>
									</div>
								</div>

								<p v-if="activityPreview(activity)" class="mt-4 type-body text-ink/80">
									{{ activityPreview(activity) }}
								</p>

								<div
									v-if="activity.reading_content"
									class="mt-4 rounded-2xl border border-line-soft bg-white p-4"
								>
									<p class="type-overline text-ink/60">Reading Preview</p>
									<p class="mt-2 type-body text-ink/80">
										{{ summarizeRichText(activity.reading_content, 320) }}
									</p>
								</div>

								<div
									v-if="activity.discussion_prompt"
									class="mt-4 rounded-2xl border border-line-soft bg-white p-4"
								>
									<p class="type-overline text-ink/60">Discussion Prompt</p>
									<p class="mt-2 type-body text-ink/80">{{ activity.discussion_prompt }}</p>
								</div>

								<div
									v-if="activity.video_url || activity.external_link"
									class="mt-4 flex flex-wrap gap-3"
								>
									<a
										v-if="activity.video_url"
										:href="activity.video_url"
										target="_blank"
										rel="noreferrer"
										class="if-action"
									>
										Open Video
									</a>
									<a
										v-if="activity.external_link"
										:href="activity.external_link"
										target="_blank"
										rel="noreferrer"
										class="if-action"
									>
										Open Resource
									</a>
								</div>
							</article>
						</div>
					</section>

					<section
						v-else-if="activeUnit"
						class="card-surface border border-dashed border-line-soft p-5"
					>
						<p class="type-body text-ink/70">This unit has no lessons available yet.</p>
					</section>
				</div>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink, useRouter } from 'vue-router';

import { formatLocalizedDate, formatLocalizedDateTime } from '@/lib/datetime';
import {
	buildLessonSequence,
	getAdjacentLessonRefs,
	resolveActiveContext,
	type CourseLessonRef,
} from '@/lib/studentCourseDetail';
import { getStudentCourseDetail } from '@/lib/services/student/studentLearningHubService';
import type {
	LessonActivity,
	LearningUnit,
	Response as StudentCourseDetailResponse,
	TaskDeliveryRef,
} from '@/types/contracts/student_hub/get_student_course_detail';

const PLACEHOLDER = '/assets/ifitwala_ed/images/course_placeholder.jpg';

const props = defineProps<{
	course_id: string;
	learning_unit?: string;
	lesson?: string;
	lesson_instance?: string;
}>();

const router = useRouter();

const courseDetail = ref<StudentCourseDetailResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');

const units = computed(() => courseDetail.value?.curriculum.units || []);
const lessonSequence = computed(() => buildLessonSequence(units.value));
const activeContext = computed(() =>
	resolveActiveContext(courseDetail.value, {
		learning_unit: props.learning_unit,
		lesson: props.lesson,
	})
);
const activeUnit = computed(() => activeContext.value.activeUnit);
const activeLesson = computed(() => activeContext.value.activeLesson);
const adjacentLessons = computed(() =>
	getAdjacentLessonRefs(units.value, activeLesson.value?.name)
);

const totalLinkedTasks = computed(() => {
	if (!courseDetail.value) return 0;
	const counts = courseDetail.value.curriculum.counts;
	return counts.course_tasks + counts.unit_tasks + counts.lesson_tasks;
});

const activeLessonOrdinal = computed(() => {
	const target = activeLesson.value?.name;
	if (!target) return 0;
	const index = lessonSequence.value.findIndex(ref => ref.lesson.name === target);
	return index === -1 ? 0 : index + 1;
});

const deepLinkSummary = computed(() => {
	if (!courseDetail.value) return '';
	const resolved = courseDetail.value.deep_link.resolved;
	if (resolved.lesson_instance) {
		return `Opened from lesson instance ${resolved.lesson_instance} and anchored to this lesson flow.`;
	}
	if (resolved.lesson) {
		return `Opened at lesson ${resolved.lesson} inside the current course structure.`;
	}
	if (resolved.learning_unit) {
		return `Opened at learning unit ${resolved.learning_unit}.`;
	}
	return 'Opened at the course level because no deeper context was available.';
});

async function loadCourseDetail() {
	loading.value = true;
	errorMessage.value = '';
	try {
		courseDetail.value = await getStudentCourseDetail({
			course_id: props.course_id,
			learning_unit: props.learning_unit || undefined,
			lesson: props.lesson || undefined,
			lesson_instance: props.lesson_instance || undefined,
		});
	} catch (error: unknown) {
		courseDetail.value = null;
		if (error instanceof Error && error.message) {
			errorMessage.value = error.message;
		} else if (typeof error === 'string' && error) {
			errorMessage.value = error;
		} else {
			errorMessage.value = 'Unable to load this course.';
		}
	} finally {
		loading.value = false;
	}
}

function summarizeRichText(value?: string | null, maxLength = 220): string {
	const normalized = String(value || '')
		.replace(/<[^>]+>/g, ' ')
		.replace(/\s+/g, ' ')
		.trim();
	if (!normalized) return '';
	if (normalized.length <= maxLength) return normalized;
	return `${normalized.slice(0, maxLength).trimEnd()}…`;
}

function activityPreview(activity: LessonActivity): string {
	if (activity.discussion_prompt) return activity.discussion_prompt;
	if (activity.reading_content) return 'Read the material below before moving to the next step.';
	if (activity.video_url) return 'Open the linked video as part of this lesson.';
	if (activity.external_link) return 'Open the linked resource for this lesson.';
	return '';
}

function formatLessonDate(value?: string | null): string {
	return formatLocalizedDate(value, { fallback: '' });
}

function deliverySummary(delivery: TaskDeliveryRef): string {
	const parts: string[] = [];

	if (delivery.available_from) {
		parts.push(`Available ${formatLocalizedDateTime(delivery.available_from, { fallback: '' })}`);
	}
	if (delivery.due_date) {
		parts.push(`Due ${formatLocalizedDateTime(delivery.due_date, { fallback: '' })}`);
	}
	if (delivery.lock_date) {
		parts.push(`Locks ${formatLocalizedDateTime(delivery.lock_date, { fallback: '' })}`);
	}
	if (delivery.lesson_instance) {
		parts.push(`Lesson instance ${delivery.lesson_instance}`);
	}

	return parts.join(' · ') || 'No dated delivery window is available yet.';
}

function isActiveUnit(unitName: string): boolean {
	return activeUnit.value?.name === unitName;
}

function isActiveLesson(lessonName: string): boolean {
	return activeLesson.value?.name === lessonName;
}

function buildCourseQuery(learningUnit?: string, lesson?: string): Record<string, string> {
	const query: Record<string, string> = {};
	if (learningUnit) query.learning_unit = learningUnit;
	if (lesson) query.lesson = lesson;
	return query;
}

function openUnit(unit: LearningUnit) {
	const firstLesson = unit.lessons[0];
	void router.replace({
		name: 'student-course-detail',
		params: { course_id: props.course_id },
		query: buildCourseQuery(unit.name, firstLesson?.name),
	});
}

function openLesson(unitName: string, lessonName: string) {
	void router.replace({
		name: 'student-course-detail',
		params: { course_id: props.course_id },
		query: buildCourseQuery(unitName, lessonName),
	});
}

function goToAdjacent(target: CourseLessonRef | null) {
	if (!target) return;
	openLesson(target.unit.name, target.lesson.name);
}

watch(
	() => props.course_id,
	() => {
		loadCourseDetail();
	},
	{ immediate: true }
);

watch(
	() => props.lesson_instance,
	(nextLessonInstance, previousLessonInstance) => {
		if (!nextLessonInstance || nextLessonInstance === previousLessonInstance) return;
		loadCourseDetail();
	}
);
</script>
