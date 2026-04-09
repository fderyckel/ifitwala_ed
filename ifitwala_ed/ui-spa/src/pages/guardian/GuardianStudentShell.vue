<!-- ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue -->
<template>
	<div class="portal-page">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
				<div class="flex items-center gap-4">
					<div
						class="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-3xl border border-line-soft bg-surface-soft"
					>
						<img
							v-if="brief?.student.student_image_url"
							:src="brief.student.student_image_url"
							:alt="brief.student.full_name"
							class="h-full w-full object-cover"
							loading="lazy"
						/>
						<span v-else class="type-h3 text-ink/50">{{ studentInitials }}</span>
					</div>
					<div>
						<p class="type-caption text-ink/70">Guardian portal</p>
						<h1 class="type-h1 text-ink">{{ brief?.student.full_name || 'Student' }}</h1>
						<p class="type-body text-ink/70">
							{{ brief?.student.school || 'School unavailable' }} ·
							{{ studentId || 'Unknown student' }}
						</p>
						<p class="mt-1 type-caption text-ink/60">
							Current themes, next experiences, and simple ways to support at home.
						</p>
					</div>
				</div>
				<div class="flex items-center gap-2">
					<RouterLink :to="{ name: 'guardian-home' }" class="if-action">
						Back to Family Snapshot
					</RouterLink>
					<button type="button" class="if-action" :disabled="loading" @click="loadBrief">
						Refresh
					</button>
				</div>
			</div>
		</header>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading learning brief...</p>
		</section>

		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">Could not load the learning brief.</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<section v-else-if="!brief" class="card-surface p-5">
			<p class="type-body-strong text-flame">
				This student is not available in your guardian scope.
			</p>
		</section>

		<template v-else>
			<section class="card-surface p-5">
				<div class="flex items-center justify-between gap-3">
					<div>
						<h2 class="type-h3 text-ink">Learning Now</h2>
						<p class="mt-1 type-caption text-ink/70">
							Big themes, upcoming experiences, and simple ways to support at home.
						</p>
					</div>
					<span class="chip">{{ courseBriefs.length }} courses</span>
				</div>
			</section>

			<section v-if="!courseBriefs.length" class="card-surface p-5">
				<p class="type-body text-ink/70">
					No active class learning brief is available yet for this student.
				</p>
			</section>

			<section v-else class="grid gap-4">
				<article
					v-for="course in courseBriefs"
					:key="course.course"
					class="card-surface overflow-hidden"
				>
					<div class="grid gap-5 p-5 sm:p-6 xl:grid-cols-[minmax(0,1.15fr),minmax(0,0.85fr)]">
						<div>
							<p class="type-overline text-ink/60">Course</p>
							<h2 class="mt-2 type-h2 text-ink">{{ course.course_name }}</h2>
							<p class="mt-2 type-caption text-ink/70">
								{{ course.class_label || 'Current class' }}
								<span v-if="course.current_unit?.title">· {{ course.current_unit.title }}</span>
							</p>

							<p v-if="course.focus_statement" class="mt-4 type-body text-ink/80">
								{{ course.focus_statement }}
							</p>

							<div
								v-if="
									course.current_unit?.essential_understanding || course.current_unit?.overview
								"
								class="mt-5 rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Current theme</p>
								<p class="mt-2 type-body text-ink/80">
									{{
										course.current_unit?.essential_understanding || course.current_unit?.overview
									}}
								</p>
							</div>

							<div class="mt-5 grid gap-4 lg:grid-cols-3">
								<article
									v-if="course.current_unit?.content"
									class="rounded-2xl border border-line-soft bg-surface-soft p-4"
								>
									<p class="type-overline text-ink/60">What they are exploring</p>
									<p class="mt-2 type-body text-ink/80">{{ course.current_unit.content }}</p>
								</article>
								<article
									v-if="course.current_unit?.skills"
									class="rounded-2xl border border-line-soft bg-surface-soft p-4"
								>
									<p class="type-overline text-ink/60">Skills in practice</p>
									<p class="mt-2 type-body text-ink/80">{{ course.current_unit.skills }}</p>
								</article>
								<article
									v-if="course.current_unit?.concepts"
									class="rounded-2xl border border-line-soft bg-surface-soft p-4"
								>
									<p class="type-overline text-ink/60">Big ideas</p>
									<p class="mt-2 type-body text-ink/80">{{ course.current_unit.concepts }}</p>
								</article>
							</div>
						</div>

						<div class="space-y-4">
							<article class="rounded-2xl border border-line-soft bg-surface-soft p-4">
								<p class="type-overline text-ink/60">Coming up next</p>
								<p class="mt-2 type-body-strong text-ink">
									{{ course.next_step || 'No immediate next step published yet.' }}
								</p>
								<p v-if="course.next_step_supporting_text" class="mt-2 type-caption text-ink/70">
									{{ course.next_step_supporting_text }}
								</p>
							</article>

							<article
								v-if="course.current_session"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Next class experience</p>
								<p class="mt-2 type-body-strong text-ink">{{ course.current_session.title }}</p>
								<p
									v-if="course.current_session.session_date"
									class="mt-2 type-caption text-ink/70"
								>
									{{ course.current_session.session_date }}
								</p>
								<p
									v-if="course.current_session.learning_goal"
									class="mt-2 type-caption text-ink/70"
								>
									{{ course.current_session.learning_goal }}
								</p>
							</article>

							<article
								v-if="course.upcoming_experiences.length"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Upcoming learning experiences</p>
								<div class="mt-3 space-y-3">
									<div
										v-for="experience in course.upcoming_experiences"
										:key="experience.class_session"
										class="rounded-xl border border-line-soft bg-white p-3"
									>
										<p class="type-body-strong text-ink">{{ experience.title }}</p>
										<p v-if="experience.session_date" class="mt-1 type-caption text-ink/70">
											{{ experience.session_date }}
										</p>
										<p v-if="experience.learning_goal" class="mt-2 type-caption text-ink/70">
											{{ experience.learning_goal }}
										</p>
									</div>
								</div>
							</article>

							<article
								v-if="course.dinner_prompt"
								class="rounded-2xl border border-line-soft bg-white p-4"
							>
								<p class="type-overline text-ink/60">Talk at home</p>
								<p class="mt-2 type-body text-ink/80">{{ course.dinner_prompt }}</p>
							</article>

							<article
								v-if="course.support_resources?.length"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Helpful at home</p>
								<div class="mt-3 space-y-3">
									<div
										v-for="resource in course.support_resources"
										:key="resource.placement || resource.material"
									>
										<p class="type-caption text-ink/70">{{ resource.title }}</p>
										<a
											v-if="resource.open_url"
											:href="resource.open_url"
											target="_blank"
											rel="noreferrer"
											class="mt-1 inline-flex text-sm font-medium text-jacaranda transition hover:text-jacaranda/80"
										>
											Open resource
										</a>
									</div>
								</div>
							</article>
						</div>
					</div>
				</article>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import { getGuardianStudentLearningBrief } from '@/lib/services/guardianHome/guardianHomeService';

import type { Response as GuardianStudentLearningBriefResponse } from '@/types/contracts/guardian/get_guardian_student_learning_brief';

const route = useRoute();

const loading = ref<boolean>(true);
const errorMessage = ref<string>('');
const brief = ref<GuardianStudentLearningBriefResponse | null>(null);

const studentId = computed(() => String(route.params.student_id || ''));
const courseBriefs = computed(() => brief.value?.course_briefs ?? []);
const studentInitials = computed(() => {
	const parts = String(brief.value?.student.full_name || 'Student')
		.split(/\s+/)
		.filter(Boolean)
		.slice(0, 2);
	return parts.map(part => part[0]?.toUpperCase() || '').join('') || '?';
});

async function loadBrief() {
	loading.value = true;
	errorMessage.value = '';
	try {
		if (!studentId.value) {
			throw new Error('Missing student id in route.');
		}
		brief.value = await getGuardianStudentLearningBrief({ student_id: studentId.value });
	} catch (error) {
		brief.value = null;
		const message = error instanceof Error ? error.message : String(error || '');
		errorMessage.value = message || 'Unknown error';
	} finally {
		loading.value = false;
	}
}

watch(
	studentId,
	() => {
		void loadBrief();
	},
	{ immediate: true }
);
</script>
