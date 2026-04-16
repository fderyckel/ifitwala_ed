<!-- ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue -->
<template>
	<div class="portal-page">
		<div>
			<RouterLink
				:to="{ name: 'student-courses' }"
				class="inline-flex items-center gap-2 type-body text-ink/70 transition hover:text-ink"
			>
				<span>←</span>
				<span>Back to Courses</span>
			</RouterLink>
		</div>

		<section
			v-if="errorMessage"
			class="rounded-2xl border border-flame/30 bg-[var(--flame)]/5 px-5 py-4"
		>
			<p class="type-body-strong text-flame">Could not load this learning space.</p>
			<p class="mt-1 type-caption text-ink/70">{{ errorMessage }}</p>
		</section>

		<section v-else-if="loading && !learningSpace" class="card-surface p-6">
			<p class="type-body text-ink/70">Loading learning space...</p>
		</section>

		<template v-else-if="learningSpace">
			<header class="card-surface overflow-hidden">
				<div class="grid gap-5 p-5 sm:gap-6 sm:p-6 xl:grid-cols-[minmax(0,9rem),minmax(0,1fr)]">
					<div class="flex justify-center xl:justify-start">
						<div
							class="w-full max-w-[7.5rem] overflow-hidden rounded-2xl border border-line-soft bg-surface-soft shadow-sm sm:max-w-[8.5rem] xl:max-w-[9rem]"
						>
							<img
								:src="learningSpace.course.course_image || PLACEHOLDER"
								:alt="learningSpace.course.course_name"
								class="aspect-square h-full w-full object-cover"
								loading="lazy"
							/>
						</div>
					</div>

					<div class="min-w-0">
						<p class="type-overline text-ink/60">Learning Space</p>
						<h1 class="mt-2 type-h1 text-ink">{{ learningSpace.course.course_name }}</h1>
						<p v-if="learningSpace.course.course_group" class="mt-2 type-caption text-ink/70">
							{{ learningSpace.course.course_group }}
						</p>
						<p class="mt-4 type-body text-ink/80">
							{{
								learningFocus.statement ||
								learningSpace.course.description ||
								'Your next learning steps appear here first.'
							}}
						</p>

						<div class="mt-4 flex flex-wrap gap-2">
							<span class="chip">{{ resolvedClassLabel }}</span>
							<button
								type="button"
								class="chip transition hover:border-jacaranda/40 hover:bg-jacaranda/5"
								@click="jumpToSection(SECTION_IDS.unitJourney)"
							>
								{{ learningSpace.curriculum.counts.units }} units
							</button>
							<button
								type="button"
								class="chip transition hover:border-jacaranda/40 hover:bg-jacaranda/5"
								@click="jumpToSection(SECTION_IDS.assignedWork)"
							>
								{{ learningSpace.curriculum.counts.assigned_work }} assignments
							</button>
						</div>

						<div
							class="mt-5 grid gap-4 rounded-2xl border border-line-soft bg-surface-soft p-4 lg:grid-cols-[minmax(0,1fr),auto]"
						>
							<div>
								<p class="type-caption text-ink/70">Current class</p>
								<p class="mt-1 type-body-strong text-ink">{{ resolvedClassLabel }}</p>
								<p class="mt-1 type-caption text-ink/70">
									Everything here is already filtered for your class, your current unit, and your
									next steps.
								</p>
							</div>

							<label
								v-if="learningSpace.access.student_group_options.length > 1"
								class="block space-y-2 lg:min-w-[16rem]"
							>
								<span class="type-caption text-ink/70">Switch class</span>
								<select
									:value="learningSpace.access.resolved_student_group || ''"
									class="if-input w-full"
									@change="handleStudentGroupChange"
								>
									<option
										v-for="option in learningSpace.access.student_group_options"
										:key="option.student_group"
										:value="option.student_group"
									>
										{{ option.label }}
									</option>
								</select>
							</label>
						</div>
					</div>
				</div>
			</header>

			<section
				v-if="learningSpace.message"
				class="rounded-2xl border border-line-soft bg-surface-soft px-5 py-4"
			>
				<p class="type-body text-ink/80">{{ learningSpace.message }}</p>
			</section>

			<section
				class="sticky top-4 z-20 rounded-[1.5rem] border border-white/70 bg-white/90 p-3 shadow-[0_18px_45px_-28px_rgba(33,53,71,0.45)] backdrop-blur-xl sm:p-4"
			>
				<div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
					<div class="flex flex-wrap gap-2">
						<button
							v-if="selectedSession"
							type="button"
							class="if-action"
							@click="jumpToSection(SECTION_IDS.sessionJourney)"
						>
							Current session
						</button>
						<button
							type="button"
							class="inline-flex items-center justify-center rounded-full border border-line-soft bg-white px-4 py-2 text-sm font-semibold text-ink transition hover:border-jacaranda/40 hover:bg-jacaranda/5"
							@click="jumpToSection(SECTION_IDS.assignedWork)"
						>
							Assignments
						</button>
						<button
							type="button"
							class="inline-flex items-center justify-center rounded-full border border-line-soft bg-white px-4 py-2 text-sm font-semibold text-ink transition hover:border-jacaranda/40 hover:bg-jacaranda/5"
							@click="jumpToSection(SECTION_IDS.resources)"
						>
							Resources
						</button>
						<RouterLink
							:to="classUpdatesHref"
							class="inline-flex items-center justify-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition"
							:class="
								courseUpdateSummary.unread_count || courseUpdateSummary.has_high_priority
									? 'border-jacaranda/40 bg-jacaranda/5 text-jacaranda'
									: 'border-line-soft bg-white text-ink hover:border-jacaranda/40 hover:bg-jacaranda/5'
							"
						>
							<span>Class Updates</span>
							<span
								v-if="classUpdatesBadge"
								class="rounded-full bg-white/90 px-2 py-0.5 text-xs font-semibold text-jacaranda"
							>
								{{ classUpdatesBadge }}
							</span>
						</RouterLink>
					</div>

					<nav
						aria-label="Jump to course sections"
						class="flex gap-2 overflow-x-auto pb-1 xl:flex-wrap xl:justify-end xl:overflow-visible xl:pb-0"
					>
						<button
							v-for="section in learningSections"
							:key="section.id"
							type="button"
							class="shrink-0 rounded-full border px-4 py-2 text-sm font-semibold transition"
							:class="
								activeSectionId === section.id
									? 'border-jacaranda bg-jacaranda/10 text-jacaranda'
									: 'border-line-soft bg-white text-ink/70 hover:border-jacaranda/30 hover:text-ink'
							"
							@click="jumpToSection(section.id)"
						>
							{{ section.label }}
						</button>
					</nav>
				</div>
			</section>

			<section class="grid gap-6 xl:grid-cols-[minmax(0,1.2fr),minmax(0,0.8fr)]">
				<article :id="SECTION_IDS.focus" class="card-surface scroll-mt-40 p-6">
					<p class="type-overline text-ink/60">Learning Focus</p>
					<h2 class="mt-2 type-h2 text-ink">
						{{ learningFocus.current_unit?.title || selectedUnit?.title || 'Current learning' }}
					</h2>
					<p class="mt-3 type-body text-ink/80">
						{{
							learningFocus.statement ||
							'Your class focus will appear here when the plan is published.'
						}}
					</p>

					<div class="mt-5 grid gap-4 lg:grid-cols-2">
						<article class="rounded-2xl border border-line-soft bg-surface-soft p-4">
							<p class="type-overline text-ink/60">Current Unit</p>
							<p class="mt-2 type-body-strong text-ink">
								{{
									learningFocus.current_unit?.title || selectedUnit?.title || 'Not available yet'
								}}
							</p>
							<p v-if="selectedUnit?.overview" class="mt-2 type-caption text-ink/70">
								{{ selectedUnit.overview }}
							</p>
						</article>

						<article class="rounded-2xl border border-line-soft bg-surface-soft p-4">
							<p class="type-overline text-ink/60">Next Class Experience</p>
							<p class="mt-2 type-body-strong text-ink">
								{{
									learningFocus.current_session?.title ||
									selectedSession?.title ||
									'Your next class will appear here soon'
								}}
							</p>
							<p class="mt-2 type-caption text-ink/70">
								{{
									learningFocus.current_session?.session_date ||
									selectedSession?.session_date ||
									'Date not published yet'
								}}
							</p>
							<p
								v-if="
									learningFocus.current_session?.learning_goal || selectedSession?.learning_goal
								"
								class="mt-2 type-caption text-ink/70"
							>
								{{
									learningFocus.current_session?.learning_goal || selectedSession?.learning_goal
								}}
							</p>
						</article>
					</div>

					<div class="mt-5 flex flex-wrap gap-2">
						<button
							v-if="selectedSession"
							type="button"
							class="if-action"
							@click="jumpToSection(SECTION_IDS.sessionJourney)"
						>
							Continue current session
						</button>
						<button
							type="button"
							class="inline-flex items-center justify-center rounded-full border border-line-soft bg-white px-4 py-2 text-sm font-semibold text-ink transition hover:border-jacaranda/40 hover:bg-jacaranda/5"
							@click="jumpToSection(SECTION_IDS.assignedWork)"
						>
							Open assignments
						</button>
					</div>
				</article>

				<article :id="SECTION_IDS.nextActions" class="card-surface scroll-mt-40 p-6">
					<div class="flex items-center justify-between gap-3">
						<div>
							<p class="type-overline text-ink/60">Next Actions</p>
							<h2 class="mt-2 type-h2 text-ink">What to do next</h2>
						</div>
						<span class="chip">{{ nextActions.length }}</span>
					</div>

					<div
						v-if="!nextActions.length"
						class="mt-5 rounded-2xl border border-dashed border-line-soft p-4"
					>
						<p class="type-body text-ink/70">
							You are up to date for now. Check back here for the next session or assignment.
						</p>
					</div>

					<div v-else class="mt-5 space-y-3">
						<article
							v-for="action in nextActions"
							:key="`${action.kind}-${action.task_delivery || action.class_session || action.unit_plan || action.label}`"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<div class="flex flex-wrap items-center gap-2">
								<p class="type-body-strong text-ink">{{ action.label }}</p>
								<span class="chip">{{ nextActionChip(action) }}</span>
							</div>
							<p v-if="action.supporting_text" class="mt-2 type-caption text-ink/70">
								{{ action.supporting_text }}
							</p>
							<p v-if="nextActionContext(action)" class="mt-1 type-caption text-ink/60">
								{{ nextActionContext(action) }}
							</p>
							<div class="mt-3">
								<RouterLink
									v-if="action.kind === 'quiz' && action.task_delivery"
									:to="quizRouteForAction(action)"
									class="if-action"
								>
									{{ nextActionButtonLabel(action) }}
								</RouterLink>
								<button v-else type="button" class="if-action" @click="handleNextAction(action)">
									{{ nextActionButtonLabel(action) }}
								</button>
							</div>
						</article>
					</div>
				</article>
			</section>

			<section
				class="grid gap-6 xl:grid-cols-[minmax(0,18rem),minmax(0,1fr)] 2xl:grid-cols-[minmax(0,20rem),minmax(0,1fr)]"
			>
				<aside class="space-y-6 xl:sticky xl:top-32 xl:self-start">
					<section :id="SECTION_IDS.unitJourney" class="card-surface scroll-mt-40 p-5">
						<div class="mb-4 flex items-center justify-between gap-3">
							<div>
								<h2 class="type-h3 text-ink">Unit Journey</h2>
								<p class="mt-1 type-caption text-ink/70">
									Follow the shared unit sequence for your class.
								</p>
							</div>
							<span class="chip">{{ unitNavigation.length }}</span>
						</div>

						<div
							v-if="!unitNavigation.length"
							class="rounded-2xl border border-dashed border-line-soft p-4"
						>
							<p class="type-body text-ink/70">No units are available yet.</p>
						</div>

						<div
							v-else
							class="flex gap-3 overflow-x-auto pb-1 xl:block xl:space-y-3 xl:overflow-visible xl:pb-0"
						>
							<button
								v-for="unit in unitNavigation"
								:key="unit.unit_plan"
								type="button"
								class="min-w-[14rem] shrink-0 rounded-2xl border p-4 text-left transition xl:min-w-0 xl:w-full"
								:class="
									selectedUnit?.unit_plan === unit.unit_plan
										? 'border-jacaranda bg-jacaranda/10 shadow-soft'
										: 'border-line-soft bg-surface-soft hover:border-jacaranda/30'
								"
								@click="selectUnit(unit.unit_plan)"
							>
								<p class="type-overline text-ink/60">Unit {{ unit.unit_order || '—' }}</p>
								<p class="mt-1 type-body-strong text-ink">{{ unit.title }}</p>
								<p class="mt-1 type-caption text-ink/70">
									{{ unit.session_count }} sessions · {{ unit.assigned_work_count }} tasks
								</p>
							</button>
						</div>
					</section>
				</aside>

				<div v-if="selectedUnit" class="space-y-6">
					<section
						:id="SECTION_IDS.sessionJourney"
						class="grid scroll-mt-40 gap-6 lg:grid-cols-[minmax(0,16rem),minmax(0,1fr)]"
					>
						<div class="card-surface p-5">
							<div class="mb-4 flex items-center justify-between gap-3">
								<div>
									<h2 class="type-h3 text-ink">Session Journey</h2>
									<p class="mt-1 type-caption text-ink/70">See the class flow for this unit.</p>
								</div>
								<span class="chip">{{ selectedUnit.sessions.length }}</span>
							</div>

							<div
								v-if="!selectedUnit.sessions.length"
								class="rounded-2xl border border-dashed border-line-soft p-4"
							>
								<p class="type-caption text-ink/70">
									Your teacher has not published class sessions for this unit yet.
								</p>
							</div>

							<div v-else class="space-y-3">
								<button
									v-for="session in selectedUnit.sessions"
									:key="session.class_session"
									type="button"
									class="w-full rounded-2xl border p-4 text-left transition"
									:class="
										selectedSession?.class_session === session.class_session
											? 'border-canopy bg-canopy/10 shadow-soft'
											: 'border-line-soft bg-surface-soft hover:border-canopy/30'
									"
									@click="selectSession(session.class_session)"
								>
									<p class="type-body-strong text-ink">{{ session.title }}</p>
									<p class="mt-1 type-caption text-ink/70">
										{{ sessionTimingLabel(session) }}
									</p>
								</button>
							</div>
						</div>

						<section v-if="selectedSession" class="card-surface p-6">
							<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
								<div>
									<p class="type-overline text-ink/60">Selected Class Experience</p>
									<h2 class="mt-2 type-h2 text-ink">{{ selectedSession.title }}</h2>
									<p class="mt-2 type-body text-ink/80">
										{{ sessionTimingLabel(selectedSession) }}
									</p>
								</div>
								<div class="flex flex-wrap gap-2">
									<span v-if="selectedSession.session_date" class="chip">
										{{ selectedSession.session_date }}
									</span>
									<span v-if="selectedSession.activities.length" class="chip">
										{{ selectedSession.activities.length }} activities
									</span>
								</div>
							</div>

							<div
								v-if="selectedSession.learning_goal"
								class="mt-5 rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Learning goal</p>
								<p class="mt-2 type-body text-ink/80">{{ selectedSession.learning_goal }}</p>
							</div>

							<div class="mt-6 space-y-4">
								<div class="flex items-center justify-between gap-3">
									<h3 class="type-h3 text-ink">How this session works</h3>
									<span class="chip">{{ selectedSession.activities.length }}</span>
								</div>

								<div
									v-if="!selectedSession.activities.length"
									class="rounded-2xl border border-dashed border-line-soft p-4"
								>
									<p class="type-caption text-ink/70">
										Activity details have not been published for this session yet.
									</p>
								</div>

								<div v-else class="space-y-3">
									<article
										v-for="activity in selectedSession.activities"
										:key="`${selectedSession.class_session}-${activity.sequence_index}-${activity.title}`"
										class="rounded-2xl border border-line-soft bg-surface-soft p-4"
									>
										<div class="flex flex-wrap items-center gap-2">
											<p class="type-body-strong text-ink">{{ activity.title }}</p>
											<span v-if="activity.activity_type" class="chip">
												{{ activity.activity_type }}
											</span>
											<span v-if="activity.estimated_minutes" class="chip">
												{{ activity.estimated_minutes }} min
											</span>
										</div>
										<p v-if="activity.student_direction" class="mt-3 type-body text-ink/80">
											{{ activity.student_direction }}
										</p>
										<p v-if="activity.resource_note" class="mt-2 type-caption text-ink/70">
											{{ activity.resource_note }}
										</p>
									</article>
								</div>
							</div>

							<div v-if="selectedSession.resources.length" class="mt-6 space-y-3">
								<div class="flex items-center justify-between gap-3">
									<h3 class="type-h3 text-ink">Resources for this session</h3>
									<span class="chip">{{ selectedSession.resources.length }}</span>
								</div>
								<div class="grid gap-3 lg:grid-cols-2">
									<article
										v-for="resource in selectedSession.resources"
										:key="resource.placement || resource.material"
										class="rounded-2xl border border-line-soft bg-surface-soft p-4"
									>
										<p class="type-body-strong text-ink">{{ resource.title }}</p>
										<p v-if="resource.description" class="mt-2 type-caption text-ink/70">
											{{ resource.description }}
										</p>
										<p v-if="resource.placement_note" class="mt-2 type-caption text-ink/60">
											{{ resource.placement_note }}
										</p>
										<a
											v-if="resource.open_url"
											:href="resource.open_url"
											target="_blank"
											rel="noreferrer"
											class="mt-3 inline-flex text-sm font-medium text-jacaranda transition hover:text-jacaranda/80"
										>
											Open resource
										</a>
									</article>
								</div>
							</div>

							<div v-if="selectedSession.assigned_work.length" class="mt-6 space-y-3">
								<div class="flex items-center justify-between gap-3">
									<h3 class="type-h3 text-ink">Work connected to this class</h3>
									<span class="chip">{{ selectedSession.assigned_work.length }}</span>
								</div>
								<div class="grid gap-3">
									<article
										v-for="item in selectedSession.assigned_work"
										:key="item.task_delivery"
										class="rounded-2xl border border-line-soft bg-surface-soft p-4"
									>
										<div class="flex flex-wrap items-center gap-2">
											<p class="type-body-strong text-ink">{{ item.title }}</p>
											<span v-if="item.task_type" class="chip">{{ item.task_type }}</span>
											<span v-if="item.quiz_state?.status_label" class="chip">
												{{ item.quiz_state.status_label }}
											</span>
										</div>
										<p v-if="item.due_date" class="mt-2 type-caption text-ink/70">
											Due {{ item.due_date }}
										</p>
										<div v-if="item.materials.length" class="mt-4 space-y-2">
											<p class="type-caption text-ink/60">What you may need</p>
											<div class="flex flex-wrap gap-2">
												<template
													v-for="resource in item.materials"
													:key="resource.placement || resource.material"
												>
													<a
														v-if="resource.open_url"
														:href="resource.open_url"
														target="_blank"
														rel="noreferrer"
														class="inline-flex items-center rounded-full border border-line-soft bg-white px-3 py-1 text-xs font-medium text-ink transition hover:border-jacaranda/40 hover:bg-jacaranda/5"
													>
														{{ resource.title }}
													</a>
												</template>
											</div>
										</div>
										<div class="mt-3 flex flex-wrap gap-2">
											<RouterLink
												v-if="isQuizAssignedWork(item)"
												:to="quizRouteFor(item)"
												class="if-action"
											>
												{{ quizActionLabel(item) }}
											</RouterLink>
											<button
												v-else
												type="button"
												class="if-action"
												@click="focusAssignedWork(item)"
											>
												{{ assignedWorkActionLabel(item) }}
											</button>
										</div>
									</article>
								</div>
							</div>
						</section>

						<section v-else class="card-surface p-6">
							<p class="type-body text-ink/70">
								Select a session to see what your class is doing.
							</p>
						</section>
					</section>

					<section :id="SECTION_IDS.unitOverview" class="card-surface scroll-mt-40 p-6">
						<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
							<div>
								<p class="type-overline text-ink/60">This Unit</p>
								<h2 class="mt-2 type-h2 text-ink">{{ selectedUnit.title }}</h2>
								<p v-if="selectedUnit.essential_understanding" class="mt-3 type-body text-ink/80">
									{{ selectedUnit.essential_understanding }}
								</p>
								<p v-else-if="selectedUnit.overview" class="mt-3 type-body text-ink/80">
									{{ selectedUnit.overview }}
								</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<span class="chip">Unit {{ selectedUnit.unit_order || '—' }}</span>
								<span v-if="selectedUnit.duration" class="chip">{{ selectedUnit.duration }}</span>
								<span v-if="selectedUnit.estimated_duration" class="chip">
									{{ selectedUnit.estimated_duration }}
								</span>
							</div>
						</div>

						<div class="mt-6 grid gap-4 xl:grid-cols-3">
							<article
								v-if="selectedUnit.content"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">What you will explore</p>
								<p class="mt-2 type-body text-ink/80">{{ selectedUnit.content }}</p>
							</article>
							<article
								v-if="selectedUnit.skills"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Skills you will practice</p>
								<p class="mt-2 type-body text-ink/80">{{ selectedUnit.skills }}</p>
							</article>
							<article
								v-if="selectedUnit.concepts"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Big ideas</p>
								<p class="mt-2 type-body text-ink/80">{{ selectedUnit.concepts }}</p>
							</article>
						</div>

						<details
							v-if="selectedUnit.standards.length"
							class="mt-6 rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<summary class="cursor-pointer list-none">
								<div class="flex items-center justify-between gap-3">
									<div>
										<p class="type-body-strong text-ink">Learning goals</p>
										<p class="mt-1 type-caption text-ink/70">
											See the published curriculum goals for this unit.
										</p>
									</div>
									<span class="chip">{{ selectedUnit.standards.length }}</span>
								</div>
							</summary>
							<div class="mt-4 space-y-3">
								<article
									v-for="standard in selectedUnit.standards"
									:key="`${selectedUnit.unit_plan}-${standard.standard_code}-${standard.standard_description}`"
									class="rounded-2xl border border-line-soft bg-white p-4"
								>
									<div class="flex flex-wrap items-center gap-2">
										<p class="type-body-strong text-ink">
											{{ standard.standard_code || 'Learning goal' }}
										</p>
										<span v-if="standard.coverage_level" class="chip">{{
											standard.coverage_level
										}}</span>
									</div>
									<p v-if="standard.standard_description" class="mt-2 type-body text-ink/80">
										{{ standard.standard_description }}
									</p>
								</article>
							</div>
						</details>
					</section>

					<section :id="SECTION_IDS.reflections" class="card-surface scroll-mt-40 p-6">
						<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
							<div>
								<p class="type-overline text-ink/60">Reflection & Journal</p>
								<h2 class="mt-2 type-h2 text-ink">Capture what you are learning</h2>
								<p class="mt-3 type-body text-ink/80">{{ reflectionPrompt }}</p>
								<p class="mt-2 type-caption text-ink/60">{{ reflectionContextNote }}</p>
							</div>
							<RouterLink :to="{ name: 'student-portfolio' }" class="if-action">
								Open full journal
							</RouterLink>
						</div>

						<div class="mt-6 grid gap-6 xl:grid-cols-[minmax(0,0.95fr),minmax(0,1.05fr)]">
							<article class="rounded-2xl border border-line-soft bg-surface-soft p-4">
								<p class="type-body-strong text-ink">New reflection</p>
								<p class="mt-2 type-caption text-ink/70">
									Keep a quick record of what clicked, what feels hard, or what you want to ask
									next.
								</p>
								<label class="mt-4 flex flex-col gap-2">
									<span class="type-caption text-ink/60">Reflection</span>
									<textarea
										v-model="reflectionBody"
										rows="5"
										placeholder="Write a short reflection..."
										class="if-input min-h-[9rem] resize-y"
									/>
								</label>
								<p v-if="reflectionError" class="mt-3 type-caption text-flame" role="alert">
									{{ reflectionError }}
								</p>
								<div class="mt-4 flex flex-wrap items-center gap-3">
									<button
										type="button"
										class="if-action"
										:disabled="reflectionSaving"
										@click="saveReflection"
									>
										{{ reflectionSaving ? 'Saving…' : 'Save reflection' }}
									</button>
									<span class="type-caption text-ink/60">Visible to you and your teachers.</span>
								</div>
							</article>

							<article class="rounded-2xl border border-line-soft bg-surface-soft p-4">
								<div class="flex items-center justify-between gap-3">
									<div>
										<p class="type-body-strong text-ink">Recent entries</p>
										<p class="mt-1 type-caption text-ink/70">
											Recent reflections from this class and course.
										</p>
									</div>
									<span class="chip">{{ reflectionEntries.length }}</span>
								</div>

								<div
									v-if="!reflectionEntries.length"
									class="mt-4 rounded-2xl border border-dashed border-line-soft bg-white p-4"
								>
									<p class="type-body text-ink/70">
										Your reflections will appear here after you save them.
									</p>
								</div>

								<div v-else class="mt-4 space-y-3">
									<article
										v-for="entry in reflectionEntries"
										:key="entry.name"
										class="rounded-2xl border border-line-soft bg-white p-4"
									>
										<div class="flex flex-wrap items-center gap-2">
											<p class="type-body-strong text-ink">
												{{ entry.entry_type || 'Reflection' }}
											</p>
											<span v-if="entry.entry_date" class="chip">{{ entry.entry_date }}</span>
											<span v-if="entry.visibility" class="chip">{{ entry.visibility }}</span>
										</div>
										<p class="mt-2 type-caption text-ink/60">
											{{ reflectionEntryContext(entry) }}
										</p>
										<p class="mt-3 type-body text-ink/80">
											{{ entry.body_preview || entry.body }}
										</p>
									</article>
								</div>
							</article>
						</div>
					</section>
				</div>

				<section v-else class="card-surface p-6">
					<p class="type-body text-ink/70">
						Select a unit to view the learning journey for this course.
					</p>
				</section>
			</section>

			<section
				v-if="selectedUnit || displayedAssignedWork.length"
				:id="SECTION_IDS.assignedWork"
				class="card-surface scroll-mt-40 p-6"
			>
				<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
					<div>
						<p class="type-overline text-ink/60">Assigned Work</p>
						<h2 class="mt-2 type-h2 text-ink">Keep track of what needs to be done</h2>
						<p class="mt-2 type-body text-ink/80">
							{{
								selectedUnit
									? `This work is connected to ${selectedUnit.title}.`
									: 'Published work for this course will appear here.'
							}}
						</p>
					</div>
					<span class="chip">{{ displayedAssignedWork.length }}</span>
				</div>

				<div
					v-if="!displayedAssignedWork.length"
					class="mt-5 rounded-2xl border border-dashed border-line-soft p-4"
				>
					<p class="type-body text-ink/70">
						No assigned work is published for this unit right now.
					</p>
				</div>

				<div v-else class="mt-5 grid gap-3 xl:grid-cols-2">
					<article
						v-for="item in displayedAssignedWork"
						:key="item.task_delivery"
						class="rounded-2xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="flex flex-wrap items-center gap-2">
							<p class="type-body-strong text-ink">{{ item.title }}</p>
							<span v-if="item.task_type" class="chip">{{ item.task_type }}</span>
							<span v-if="assignedWorkStatusLabel(item)" class="chip">
								{{ assignedWorkStatusLabel(item) }}
							</span>
						</div>
						<p v-if="assignedWorkTimingLabel(item)" class="mt-2 type-caption text-ink/70">
							{{ assignedWorkTimingLabel(item) }}
						</p>
						<p v-if="assignedWorkContextLine(item)" class="mt-1 type-caption text-ink/60">
							{{ assignedWorkContextLine(item) }}
						</p>
						<div v-if="item.materials.length" class="mt-4 space-y-2">
							<p class="type-caption text-ink/60">What you may need</p>
							<div class="flex flex-wrap gap-2">
								<template
									v-for="resource in item.materials"
									:key="resource.placement || resource.material"
								>
									<a
										v-if="resource.open_url"
										:href="resource.open_url"
										target="_blank"
										rel="noreferrer"
										class="inline-flex items-center rounded-full border border-line-soft bg-white px-3 py-1 text-xs font-medium text-ink transition hover:border-jacaranda/40 hover:bg-jacaranda/5"
									>
										{{ resource.title }}
									</a>
								</template>
							</div>
						</div>
						<div class="mt-3 flex flex-wrap gap-2">
							<RouterLink
								v-if="isQuizAssignedWork(item)"
								:to="quizRouteFor(item)"
								class="if-action"
							>
								{{ quizActionLabel(item) }}
							</RouterLink>
							<button
								v-else-if="item.class_session || item.unit_plan"
								type="button"
								class="if-action"
								@click="focusAssignedWork(item)"
							>
								{{ assignedWorkActionLabel(item) }}
							</button>
						</div>
					</article>
				</div>
			</section>

			<section
				v-if="
					selectedUnit ||
					learningSpace.resources.class_resources.length ||
					learningSpace.resources.shared_resources.length
				"
				:id="SECTION_IDS.resources"
				class="card-surface scroll-mt-40 p-6"
			>
				<div class="flex items-center justify-between gap-3">
					<div>
						<p class="type-overline text-ink/60">Helpful Resources</p>
						<h2 class="mt-2 type-h2 text-ink">What you may need</h2>
					</div>
				</div>

				<div class="mt-5 grid gap-4 xl:grid-cols-3">
					<article
						v-if="selectedUnit?.shared_resources.length"
						class="rounded-2xl border border-line-soft bg-surface-soft p-4"
					>
						<p class="type-body-strong text-ink">This unit</p>
						<div class="mt-3 space-y-3">
							<div
								v-for="resource in selectedUnit.shared_resources"
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

					<article
						v-if="learningSpace.resources.class_resources.length"
						class="rounded-2xl border border-line-soft bg-surface-soft p-4"
					>
						<p class="type-body-strong text-ink">Your class</p>
						<div class="mt-3 space-y-3">
							<div
								v-for="resource in learningSpace.resources.class_resources"
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

					<article
						v-if="learningSpace.resources.shared_resources.length"
						class="rounded-2xl border border-line-soft bg-surface-soft p-4"
					>
						<p class="type-body-strong text-ink">Across this course</p>
						<div class="mt-3 space-y-3">
							<div
								v-for="resource in learningSpace.resources.shared_resources"
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
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { toast } from 'frappe-ui';
import { RouterLink, useRoute, useRouter } from 'vue-router';

import { createReflectionEntry } from '@/lib/services/portfolio/portfolioService';
import { getStudentLearningSpace } from '@/lib/services/student/studentLearningHubService';
import type {
	Response as StudentLearningSpaceResponse,
	StudentAssignedWork,
	StudentCourseCommunicationSummary,
	StudentLearningNextAction,
	StudentLearningReflectionEntry,
	StudentLearningSession,
	StudentLearningUnit,
} from '@/types/contracts/student_learning/get_student_learning_space';

const PLACEHOLDER =
	'data:image/svg+xml;charset=UTF-8,' +
	encodeURIComponent(
		`<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600"><rect width="600" height="600" fill="#f3ede2"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="Arial, sans-serif" font-size="32" fill="#8a7963">Course</text></svg>`
	);

const EMPTY_COURSE_UPDATE_SUMMARY: StudentCourseCommunicationSummary = {
	total_count: 0,
	unread_count: 0,
	high_priority_count: 0,
	has_high_priority: 0,
	latest_publish_at: null,
};

const SECTION_IDS = {
	focus: 'learning-focus',
	nextActions: 'next-actions',
	unitJourney: 'unit-journey',
	sessionJourney: 'session-journey',
	unitOverview: 'unit-overview',
	reflections: 'reflection-journal',
	assignedWork: 'assigned-work',
	resources: 'resources',
} as const;

type LearningSectionId = (typeof SECTION_IDS)[keyof typeof SECTION_IDS];

const props = defineProps<{
	course_id: string;
	student_group?: string;
	unit_plan?: string;
	class_session?: string;
}>();

const router = useRouter();
const route = useRoute();

const learningSpace = ref<StudentLearningSpaceResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');
const selectedUnitPlan = ref('');
const selectedSessionId = ref('');
const loadToken = ref(0);
const activeSectionId = ref<LearningSectionId>(SECTION_IDS.focus);
const scrollFrame = ref<number | null>(null);
const reflectionBody = ref('');
const reflectionError = ref('');
const reflectionSaving = ref(false);

const learningFocus = computed(() => learningSpace.value?.learning.focus || {});
const nextActions = computed(() => learningSpace.value?.learning.next_actions || []);
const reflectionEntries = computed<StudentLearningReflectionEntry[]>(
	() => learningSpace.value?.learning.reflection_entries || []
);
const unitNavigation = computed(() => learningSpace.value?.learning.unit_navigation || []);
const courseUpdateSummary = computed<StudentCourseCommunicationSummary>(
	() => learningSpace.value?.communications?.course_updates_summary || EMPTY_COURSE_UPDATE_SUMMARY
);

const selectedUnit = computed<StudentLearningUnit | null>(() => {
	return (
		learningSpace.value?.curriculum.units.find(
			unit => unit.unit_plan === selectedUnitPlan.value
		) || null
	);
});

const selectedSession = computed<StudentLearningSession | null>(() => {
	return (
		selectedUnit.value?.sessions.find(
			session => session.class_session === selectedSessionId.value
		) || null
	);
});

const displayedAssignedWork = computed<StudentAssignedWork[]>(() => {
	if (selectedUnit.value) {
		return dedupeAssignedWork(selectedUnit.value.assigned_work || []);
	}
	return dedupeAssignedWork(learningSpace.value?.resources.general_assigned_work || []);
});

const resolvedClassLabel = computed(() => {
	const resolvedGroup = learningSpace.value?.access.resolved_student_group;
	if (!resolvedGroup) return 'Class not available';
	return (
		learningSpace.value?.access.student_group_options.find(
			option => option.student_group === resolvedGroup
		)?.label || resolvedGroup
	);
});

const hasVisibleResources = computed(() => {
	return !!(
		selectedUnit.value?.shared_resources.length ||
		learningSpace.value?.resources.class_resources.length ||
		learningSpace.value?.resources.shared_resources.length
	);
});

const classUpdatesHref = computed(() => ({
	name: 'student-communications' as const,
	query: {
		source: 'course',
		course_id: props.course_id,
		student_group:
			learningSpace.value?.access.resolved_student_group || props.student_group || undefined,
	},
}));

const classUpdatesBadge = computed(() => {
	if (courseUpdateSummary.value.unread_count > 0) {
		return `${courseUpdateSummary.value.unread_count} new`;
	}
	if (courseUpdateSummary.value.total_count > 0) {
		return String(courseUpdateSummary.value.total_count);
	}
	return '';
});

const learningSections = computed(() => {
	const sections: Array<{ id: LearningSectionId; label: string }> = [
		{ id: SECTION_IDS.focus, label: 'Focus' },
		{ id: SECTION_IDS.nextActions, label: `Next Actions (${nextActions.value.length})` },
		{ id: SECTION_IDS.unitJourney, label: `Units (${unitNavigation.value.length})` },
	];

	if (selectedUnit.value) {
		sections.push(
			{
				id: SECTION_IDS.sessionJourney,
				label: `Sessions (${selectedUnit.value.sessions.length})`,
			},
			{ id: SECTION_IDS.unitOverview, label: 'Unit Summary' },
			{ id: SECTION_IDS.reflections, label: `Reflections (${reflectionEntries.value.length})` }
		);
	}

	if (selectedUnit.value || displayedAssignedWork.value.length) {
		sections.push({
			id: SECTION_IDS.assignedWork,
			label: `Assigned Work (${displayedAssignedWork.value.length})`,
		});
	}

	if (hasVisibleResources.value) {
		sections.push({ id: SECTION_IDS.resources, label: 'Resources' });
	}

	return sections;
});

function isLearningSectionId(value: string): value is LearningSectionId {
	return Object.values(SECTION_IDS).includes(value as LearningSectionId);
}

function getSectionElement(sectionId: LearningSectionId) {
	if (typeof document === 'undefined') return null;
	return document.getElementById(sectionId);
}

function syncActiveSectionFromViewport() {
	if (typeof window === 'undefined') return;
	const sections = learningSections.value;
	if (!sections.length) return;

	let currentSection = sections[0].id;
	for (const section of sections) {
		const element = getSectionElement(section.id);
		if (!element) continue;
		if (element.getBoundingClientRect().top <= 180) {
			currentSection = section.id;
		}
	}
	activeSectionId.value = currentSection;
}

function requestActiveSectionSync() {
	if (typeof window === 'undefined') return;
	if (scrollFrame.value !== null) {
		window.cancelAnimationFrame(scrollFrame.value);
	}
	scrollFrame.value = window.requestAnimationFrame(() => {
		scrollFrame.value = null;
		syncActiveSectionFromViewport();
	});
}

function scrollToSection(sectionId: LearningSectionId) {
	activeSectionId.value = sectionId;
	const sectionElement = getSectionElement(sectionId);
	if (!sectionElement) return;
	sectionElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
	requestActiveSectionSync();
}

async function jumpToSection(sectionId: LearningSectionId) {
	if (route.hash !== `#${sectionId}`) {
		await router.replace({
			query: { ...route.query },
			hash: `#${sectionId}`,
		});
	}
	await nextTick();
	scrollToSection(sectionId);
}

async function replaceLearningContextRoute(unitPlan: string, classSession: string) {
	const nextStudentGroup =
		learningSpace.value?.access.resolved_student_group || props.student_group || '';
	const nextQuery = {
		...route.query,
		student_group: nextStudentGroup || undefined,
		unit_plan: unitPlan || undefined,
		class_session: classSession || undefined,
	};
	if (
		String(route.query.student_group || '').trim() === nextStudentGroup &&
		String(route.query.unit_plan || '').trim() === unitPlan &&
		String(route.query.class_session || '').trim() === classSession
	) {
		return;
	}
	await router.replace({
		query: nextQuery,
		hash: route.hash || undefined,
	});
}

function applySelection(payload: StudentLearningSpaceResponse) {
	const requestedSession = String(props.class_session || '').trim();
	const requestedUnit = String(props.unit_plan || '').trim();
	const defaultUnit = String(payload.learning.selected_context.unit_plan || '').trim();
	const defaultSession = String(payload.learning.selected_context.class_session || '').trim();
	const requestedSessionUnit = requestedSession
		? payload.curriculum.units.find(unit =>
				unit.sessions.some(session => session.class_session === requestedSession)
			)
		: null;

	const currentUnitStillExists = payload.curriculum.units.some(
		unit => unit.unit_plan === selectedUnitPlan.value
	);
	if (requestedSessionUnit) {
		selectedUnitPlan.value = requestedSessionUnit.unit_plan;
	} else if (
		requestedUnit &&
		payload.curriculum.units.some(unit => unit.unit_plan === requestedUnit)
	) {
		selectedUnitPlan.value = requestedUnit;
	} else if (
		defaultUnit &&
		payload.curriculum.units.some(unit => unit.unit_plan === defaultUnit)
	) {
		selectedUnitPlan.value = defaultUnit;
	} else if (!currentUnitStillExists) {
		selectedUnitPlan.value = payload.curriculum.units[0]?.unit_plan || '';
	}

	const unit =
		payload.curriculum.units.find(row => row.unit_plan === selectedUnitPlan.value) || null;
	const requestedSessionStillExists = !!unit?.sessions.some(
		session => session.class_session === requestedSession
	);
	const currentSessionStillExists = !!unit?.sessions.some(
		session => session.class_session === selectedSessionId.value
	);
	if (requestedSessionStillExists) {
		selectedSessionId.value = requestedSession;
	} else if (
		defaultSession &&
		unit?.sessions.some(session => session.class_session === defaultSession)
	) {
		selectedSessionId.value = defaultSession;
	} else if (!currentSessionStillExists) {
		selectedSessionId.value = unit?.sessions[0]?.class_session || '';
	}
}

async function loadLearningSpace() {
	const ticket = loadToken.value + 1;
	loadToken.value = ticket;
	loading.value = true;
	errorMessage.value = '';

	try {
		const payload = await getStudentLearningSpace({
			course_id: props.course_id,
			student_group: props.student_group || undefined,
		});
		if (ticket !== loadToken.value) return;
		learningSpace.value = payload;
		applySelection(payload);
		await nextTick();
		const hashSection = String(route.hash || '')
			.replace(/^#/, '')
			.trim();
		if (isLearningSectionId(hashSection)) {
			scrollToSection(hashSection);
		} else {
			requestActiveSectionSync();
		}
	} catch (error) {
		if (ticket !== loadToken.value) return;
		learningSpace.value = null;
		errorMessage.value = error instanceof Error ? error.message : 'Unknown error';
	} finally {
		if (ticket === loadToken.value) {
			loading.value = false;
		}
	}
}

async function selectUnit(unitPlan: string) {
	selectedUnitPlan.value = unitPlan;
	selectedSessionId.value =
		learningSpace.value?.curriculum.units.find(unit => unit.unit_plan === unitPlan)?.sessions[0]
			?.class_session || '';
	await replaceLearningContextRoute(selectedUnitPlan.value, selectedSessionId.value);
	await nextTick();
	await jumpToSection(
		selectedSessionId.value ? SECTION_IDS.sessionJourney : SECTION_IDS.unitOverview
	);
}

async function selectSession(classSession: string) {
	const parentUnit = learningSpace.value?.curriculum.units.find(unit =>
		unit.sessions.some(session => session.class_session === classSession)
	);
	if (parentUnit && parentUnit.unit_plan !== selectedUnitPlan.value) {
		selectedUnitPlan.value = parentUnit.unit_plan;
	}
	selectedSessionId.value = classSession;
	await replaceLearningContextRoute(selectedUnitPlan.value, selectedSessionId.value);
	await nextTick();
	await jumpToSection(SECTION_IDS.sessionJourney);
}

function isQuizAssignedWork(item: StudentAssignedWork) {
	return (item.task_type || '').trim() === 'Quiz';
}

function dedupeAssignedWork(items: StudentAssignedWork[]) {
	const seen = new Set<string>();
	return items.filter(item => {
		const key = String(item.task_delivery || '').trim();
		if (!key || seen.has(key)) return false;
		seen.add(key);
		return true;
	});
}

function findUnitByPlan(unitPlan?: string | null) {
	const target = String(unitPlan || '').trim();
	if (!target) return null;
	return learningSpace.value?.curriculum.units.find(unit => unit.unit_plan === target) || null;
}

function findSessionById(classSession?: string | null) {
	const target = String(classSession || '').trim();
	if (!target) return null;
	for (const unit of learningSpace.value?.curriculum.units || []) {
		const session = unit.sessions.find(row => row.class_session === target);
		if (session) return session;
	}
	return null;
}

function findAssignedWorkByDelivery(taskDelivery?: string | null) {
	const target = String(taskDelivery || '').trim();
	if (!target) return null;
	for (const item of learningSpace.value?.resources.general_assigned_work || []) {
		if (String(item.task_delivery || '').trim() === target) return item;
	}
	for (const unit of learningSpace.value?.curriculum.units || []) {
		for (const item of unit.assigned_work || []) {
			if (String(item.task_delivery || '').trim() === target) return item;
		}
		for (const session of unit.sessions || []) {
			for (const item of session.assigned_work || []) {
				if (String(item.task_delivery || '').trim() === target) return item;
			}
		}
	}
	return null;
}

function sessionTimingLabel(session: StudentLearningSession) {
	return session.session_date || 'Details coming soon';
}

function nextActionContext(action: StudentLearningNextAction) {
	const session = findSessionById(action.class_session);
	if (session) {
		return session.session_date ? `${session.title} · ${session.session_date}` : session.title;
	}
	const unit = findUnitByPlan(action.unit_plan);
	return unit?.title || '';
}

function humanizeLabel(value?: string | null) {
	const text = String(value || '').trim();
	if (!text) return '';
	return text.replace(/_/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase());
}

function quizActionLabel(item: StudentAssignedWork) {
	if (!isQuizAssignedWork(item)) return 'Open task';
	if (item.quiz_state?.can_continue) return 'Continue quiz';
	if (item.quiz_state?.can_retry) return 'Retry quiz';
	if (item.quiz_state?.can_start) {
		return Number(item.quiz_state.attempts_used || 0) > 0 ? 'Start next attempt' : 'Start quiz';
	}
	if (item.quiz_state?.latest_attempt) return 'Review quiz';
	return 'Open quiz';
}

function quizRouteFor(item: StudentAssignedWork) {
	return {
		name: 'student-quiz',
		params: {
			course_id: props.course_id,
			task_delivery: item.task_delivery,
		},
		query: {
			student_group: learningSpace.value?.access.resolved_student_group || undefined,
			unit_plan: item.unit_plan || selectedUnitPlan.value || undefined,
			class_session: item.class_session || selectedSessionId.value || undefined,
		},
	};
}

function quizRouteForAction(action: StudentLearningNextAction) {
	return {
		name: 'student-quiz',
		params: {
			course_id: props.course_id,
			task_delivery: action.task_delivery,
		},
		query: {
			student_group: learningSpace.value?.access.resolved_student_group || undefined,
			unit_plan: action.unit_plan || undefined,
			class_session: action.class_session || undefined,
		},
	};
}

function nextActionChip(action: StudentLearningNextAction) {
	if (action.kind === 'quiz') return 'Quiz';
	if (action.kind === 'session') return 'Session';
	return 'Assigned work';
}

function nextActionButtonLabel(action: StudentLearningNextAction) {
	if (action.kind === 'quiz') return 'Open now';
	if (action.kind === 'session') return 'Open session';
	return 'Open task workspace';
}

function assignedWorkStatusLabel(item: StudentAssignedWork) {
	if (item.quiz_state?.status_label) return item.quiz_state.status_label;
	if (item.is_complete) return 'Completed';
	return humanizeLabel(item.submission_status || item.grading_status || '');
}

function assignedWorkTimingLabel(item: StudentAssignedWork) {
	if (item.due_date) return `Due ${item.due_date}`;
	if (item.available_from) return `Available ${item.available_from}`;
	return '';
}

function assignedWorkContextLine(item: StudentAssignedWork) {
	const session = findSessionById(item.class_session);
	if (session) {
		return session.session_date ? `${session.title} · ${session.session_date}` : session.title;
	}
	const unit = findUnitByPlan(item.unit_plan);
	if (unit) return `In ${unit.title}`;
	return '';
}

function assignedWorkActionLabel(item: StudentAssignedWork) {
	if (isQuizAssignedWork(item)) return quizActionLabel(item);
	if (item.class_session) return 'Open task workspace';
	if (item.unit_plan) return 'Open unit workspace';
	return 'Open course workspace';
}

const reflectionPrompt = computed(() => {
	if (selectedSession.value?.learning_goal) {
		return `After ${selectedSession.value.title}, note what evidence, question, or idea is shaping your understanding.`;
	}
	if (selectedUnit.value?.essential_understanding) {
		return `Capture how this unit is changing your understanding of ${selectedUnit.value.title}.`;
	}
	if (selectedUnit.value?.title) {
		return `Capture what you are noticing as you work through ${selectedUnit.value.title}.`;
	}
	return 'Capture what you understood, what still feels unclear, or what you want to ask next.';
});

const reflectionContextNote = computed(() => {
	if (selectedSession.value?.title) {
		return `This reflection will stay inside ${resolvedClassLabel.value} and be linked to ${selectedSession.value.title}.`;
	}
	if (selectedUnit.value?.title) {
		return `This reflection will stay inside ${resolvedClassLabel.value} for ${selectedUnit.value.title}.`;
	}
	return `This reflection will stay inside ${resolvedClassLabel.value}.`;
});

function reflectionEntryContext(entry: StudentLearningReflectionEntry) {
	const session = findSessionById(entry.class_session);
	if (session) {
		return session.session_date ? `${session.title} · ${session.session_date}` : session.title;
	}
	const task = findAssignedWorkByDelivery(entry.task_delivery);
	if (task) return task.title;
	if (
		entry.student_group &&
		entry.student_group === learningSpace.value?.access.resolved_student_group
	) {
		return resolvedClassLabel.value;
	}
	return 'Course reflection';
}

async function saveReflection() {
	const body = reflectionBody.value.trim();
	if (!body) {
		reflectionError.value = 'Write a short reflection before saving it.';
		return;
	}
	if (!learningSpace.value) return;

	reflectionSaving.value = true;
	reflectionError.value = '';
	try {
		const response = await createReflectionEntry({
			body,
			entry_type: 'Reflection',
			visibility: 'Teacher',
			course: props.course_id,
			student_group: learningSpace.value.access.resolved_student_group || undefined,
			class_session: selectedSessionId.value || undefined,
		});
		const nextEntry: StudentLearningReflectionEntry = {
			name: response.name,
			entry_date: response.entry_date,
			entry_type: 'Reflection',
			visibility: 'Teacher',
			moderation_state: response.moderation_state,
			body,
			body_preview: body.slice(0, 280),
			course: props.course_id,
			student_group: learningSpace.value.access.resolved_student_group || undefined,
			class_session: selectedSessionId.value || undefined,
		};
		learningSpace.value = {
			...learningSpace.value,
			learning: {
				...learningSpace.value.learning,
				reflection_entries: [nextEntry, ...reflectionEntries.value].slice(0, 8),
			},
		};
		reflectionBody.value = '';
		toast.success('Reflection saved.');
	} catch (error) {
		const message = error instanceof Error ? error.message : 'Could not save this reflection.';
		reflectionError.value = message;
		toast.error(message);
	} finally {
		reflectionSaving.value = false;
	}
}

async function handleNextAction(action: StudentLearningNextAction) {
	if (action.unit_plan) {
		await selectUnit(action.unit_plan);
	}
	if (action.class_session) {
		await selectSession(action.class_session);
		return;
	}
	await jumpToSection(
		action.kind === 'session' ? SECTION_IDS.sessionJourney : SECTION_IDS.assignedWork
	);
}

async function focusAssignedWork(item: StudentAssignedWork) {
	if (item.unit_plan) {
		await selectUnit(item.unit_plan);
	}
	if (item.class_session) {
		await selectSession(item.class_session);
		return;
	}
	await jumpToSection(item.unit_plan ? SECTION_IDS.unitOverview : SECTION_IDS.assignedWork);
}

async function handleStudentGroupChange(event: Event) {
	const target = event.target as HTMLSelectElement | null;
	const value = String(target?.value || '').trim();
	await router.replace({
		query: {
			student_group: value || undefined,
		},
		hash: route.hash || undefined,
	});
}

watch(
	() => [props.course_id, props.student_group],
	() => {
		loadLearningSpace();
	},
	{ immediate: true }
);

watch(
	() => [props.unit_plan, props.class_session],
	async () => {
		if (!learningSpace.value) return;
		applySelection(learningSpace.value);
		await nextTick();
		const hashSection = String(route.hash || '')
			.replace(/^#/, '')
			.trim();
		if (isLearningSectionId(hashSection)) {
			scrollToSection(hashSection);
		} else {
			requestActiveSectionSync();
		}
	}
);

watch(
	() => route.hash,
	async hash => {
		const hashSection = String(hash || '')
			.replace(/^#/, '')
			.trim();
		if (!isLearningSectionId(hashSection)) return;
		await nextTick();
		scrollToSection(hashSection);
	}
);

watch(learningSections, () => {
	if (!learningSections.value.some(section => section.id === activeSectionId.value)) {
		activeSectionId.value = learningSections.value[0]?.id || SECTION_IDS.focus;
	}
	requestActiveSectionSync();
});

onMounted(() => {
	if (typeof window === 'undefined') return;
	window.addEventListener('scroll', requestActiveSectionSync, { passive: true });
	requestActiveSectionSync();
});

onBeforeUnmount(() => {
	if (typeof window === 'undefined') return;
	window.removeEventListener('scroll', requestActiveSectionSync);
	if (scrollFrame.value !== null) {
		window.cancelAnimationFrame(scrollFrame.value);
		scrollFrame.value = null;
	}
});
</script>
