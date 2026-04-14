<template>
	<div class="staff-shell space-y-6">
		<section class="overflow-hidden rounded-[2rem] border border-line-soft bg-white shadow-soft">
			<div class="grid gap-6 px-6 py-6 lg:grid-cols-[minmax(0,1fr),auto] lg:items-end">
				<div class="space-y-4">
					<RouterLink
						:to="{ name: 'staff-course-plan-index' }"
						class="inline-flex items-center gap-2 type-caption text-ink/70 transition hover:text-ink"
					>
						<span>←</span>
						<span>Back to Course Plans</span>
					</RouterLink>
					<div>
						<p class="type-overline text-ink/60">Governed Curriculum</p>
						<h1 class="mt-2 type-h1 text-ink">
							{{ surface?.course_plan.title || coursePlan || 'Course Plan' }}
						</h1>
						<p class="mt-2 max-w-3xl type-body text-ink/80">
							Shape the shared course backbone, capture reusable unit guidance, and build quiz
							banks teachers can assign without leaving the staff SPA.
						</p>
					</div>
				</div>
				<div class="flex flex-wrap gap-2 lg:justify-end">
					<button
						type="button"
						class="chip cursor-pointer transition hover:border-jacaranda/40 hover:bg-sky/20 hover:text-ink"
						@click="jumpToSection(SECTION_IDS.overview)"
					>
						{{ surface?.course_plan.course_name || 'Course pending' }}
					</button>
					<button
						type="button"
						class="chip cursor-pointer transition hover:border-jacaranda/40 hover:bg-sky/20 hover:text-ink"
						@click="jumpToSection(SECTION_IDS.units)"
					>
						{{ surface?.curriculum.unit_count || 0 }} units
					</button>
					<button
						type="button"
						class="chip cursor-pointer transition hover:border-jacaranda/40 hover:bg-sky/20 hover:text-ink"
						@click="jumpToSection(SECTION_IDS.quizBanks)"
					>
						{{ surface?.assessment.quiz_question_banks.length || 0 }} quiz banks
					</button>
					<span class="chip">{{ surface?.course_plan.plan_status || 'Draft' }}</span>
					<span class="chip">{{ canManagePlan ? 'Editable' : 'Read only' }}</span>
				</div>
			</div>
		</section>

		<section
			v-if="errorMessage"
			class="rounded-2xl border border-flame/30 bg-[var(--flame)]/5 px-5 py-4"
		>
			<p class="type-body-strong text-flame">Could not load the shared course plan.</p>
			<p class="mt-1 type-caption text-ink/70">{{ errorMessage }}</p>
		</section>

		<section
			v-else-if="loading && !surface"
			class="rounded-2xl border border-line-soft bg-white px-5 py-8"
		>
			<p class="type-body text-ink/70">Loading shared course plan...</p>
		</section>

		<template v-else-if="surface">
			<section
				v-if="navigationSections.length"
				class="rounded-[1.75rem] border border-line-soft bg-white/92 px-5 py-4 shadow-soft"
			>
				<div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
					<div class="min-w-0">
						<p class="type-overline text-ink/55">Quick Access</p>
						<p class="mt-1 type-caption text-ink/65">
							Jump to the next planning area without losing your place.
						</p>
					</div>

					<div v-if="canManagePlan" class="flex flex-wrap gap-2">
						<button
							type="button"
							class="if-action if-action--subtle"
							:disabled="!selectedUnit"
							@click="quickEditUnit"
						>
							Edit Unit
						</button>
						<button
							type="button"
							class="if-action if-action--subtle"
							:disabled="!selectedUnit"
							@click="quickUploadUnitFile"
						>
							Upload Unit PDF
						</button>
						<button
							type="button"
							class="if-action if-action--subtle"
							:disabled="!selectedUnit"
							@click="quickAddReflection"
						>
							Add Reflection
						</button>
						<button type="button" class="if-action if-action--subtle" @click="quickStartQuizBank">
							New Quiz Bank
						</button>
					</div>
				</div>

				<div class="mt-3 flex gap-2 overflow-x-auto pb-1">
					<button
						v-for="section in navigationSections"
						:key="section.id"
						type="button"
						class="flex shrink-0 items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition"
						:class="
							activeSectionId === section.id
								? 'border-jacaranda bg-jacaranda/10 text-ink shadow-soft'
								: 'border-line-soft bg-white text-ink/70 hover:border-jacaranda/40 hover:text-ink'
						"
						@click="jumpToSection(section.id)"
					>
						<span>{{ section.label }}</span>
						<span
							v-if="section.count !== undefined && section.count !== null"
							class="rounded-full bg-white/80 px-2 py-0.5 text-xs text-ink/70"
						>
							{{ section.count }}
						</span>
					</button>
				</div>

				<p v-if="canManagePlan && !selectedUnit" class="mt-3 type-caption text-ink/65">
					Select a governed unit first to unlock reflection and unit-resource shortcuts.
				</p>
			</section>

			<section
				:id="SECTION_IDS.overview"
				class="scroll-mt-40 rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
			>
				<button
					type="button"
					class="flex w-full flex-col gap-4 text-left lg:flex-row lg:items-start lg:justify-between"
					:aria-expanded="!isSectionCollapsed(SECTION_IDS.overview)"
					@click="toggleSection(SECTION_IDS.overview)"
				>
					<div>
						<p class="type-overline text-ink/60">Course Plan Overview</p>
						<h2 class="mt-2 type-h2 text-ink">
							{{ surface.course_plan.course_name || surface.course_plan.course }}
						</h2>
						<p class="mt-2 type-body text-ink/80">
							{{
								isSectionCollapsed(SECTION_IDS.overview)
									? 'Open the shared plan metadata, summary, and publishing controls.'
									: 'This shared plan sets the governed backbone every linked class teaching plan uses.'
							}}
						</p>
					</div>
					<div class="flex flex-wrap items-center gap-2 lg:justify-end">
						<span v-if="surface.course_plan.course_group" class="chip">
							{{ surface.course_plan.course_group }}
						</span>
						<span v-if="surface.course_plan.academic_year" class="chip">
							{{ surface.course_plan.academic_year }}
						</span>
						<span v-if="surface.course_plan.cycle_label" class="chip">
							{{ surface.course_plan.cycle_label }}
						</span>
						<span class="chip">{{
							isSectionCollapsed(SECTION_IDS.overview) ? 'Show' : 'Hide'
						}}</span>
					</div>
				</button>

				<div
					v-if="!isSectionCollapsed(SECTION_IDS.overview) && canManagePlan"
					class="mt-6 grid gap-4 lg:grid-cols-2"
				>
					<label class="block space-y-2">
						<span class="type-caption text-ink/70">Course Plan Title</span>
						<input
							v-model="coursePlanForm.title"
							type="text"
							class="if-input w-full"
							placeholder="e.g. Biology Semester 1 Plan"
						/>
					</label>
					<label class="block space-y-2">
						<span class="type-caption text-ink/70">Academic Year</span>
						<select
							v-model="coursePlanForm.academic_year"
							class="if-input w-full"
							:disabled="!coursePlanAcademicYearOptions.length"
						>
							<option value="">Optional academic year</option>
							<option
								v-for="option in coursePlanAcademicYearOptions"
								:key="option.value"
								:value="option.value"
							>
								{{ option.label }}
							</option>
						</select>
						<p class="type-caption text-ink/60">
							{{
								coursePlanAcademicYearOptions.length
									? 'Only Academic Year records in this course school scope are available here.'
									: 'No Academic Year records are available for this course school yet.'
							}}
						</p>
					</label>
					<label class="block space-y-2">
						<span class="type-caption text-ink/70">Cycle Label</span>
						<input
							v-model="coursePlanForm.cycle_label"
							type="text"
							class="if-input w-full"
							placeholder="e.g. Semester 1"
						/>
					</label>
					<label class="block space-y-2">
						<span class="type-caption text-ink/70">Publishing Status</span>
						<select v-model="coursePlanForm.plan_status" class="if-input w-full">
							<option v-for="option in coursePlanStatusOptions" :key="option" :value="option">
								{{ option }}
							</option>
						</select>
					</label>
					<label class="block space-y-2 lg:col-span-2">
						<span class="type-caption text-ink/70">Summary</span>
						<PlanningRichTextField
							v-model="coursePlanForm.summary"
							placeholder="State the shared purpose, scope, and non-negotiables for this course plan."
							min-height-class="min-h-[9rem]"
						/>
					</label>
					<div class="flex justify-end lg:col-span-2">
						<button
							type="button"
							class="if-action"
							:disabled="coursePlanPending"
							@click="handleSaveCoursePlan"
						>
							{{ coursePlanPending ? 'Saving...' : 'Save Shared Course Plan' }}
						</button>
					</div>
				</div>

				<div
					v-else-if="!isSectionCollapsed(SECTION_IDS.overview)"
					class="mt-6 rounded-2xl border border-line-soft bg-surface-soft p-5"
				>
					<PlanningRichTextField
						v-if="hasRichTextContent(surface.course_plan.summary)"
						:model-value="surface.course_plan.summary"
						:editable="false"
						display-class="text-ink/80"
					/>
					<p v-else class="type-caption text-ink/70">
						No shared summary has been captured for this course plan yet.
					</p>
				</div>
			</section>

			<section
				:id="SECTION_IDS.timeline"
				class="scroll-mt-40 rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
			>
				<button
					type="button"
					class="flex w-full flex-col gap-4 text-left lg:flex-row lg:items-start lg:justify-between"
					:aria-expanded="!isSectionCollapsed(SECTION_IDS.timeline)"
					@click="toggleSection(SECTION_IDS.timeline)"
				>
					<div>
						<p class="type-overline text-ink/60">Curriculum Timeline</p>
						<h2 class="mt-2 type-h2 text-ink">Year-at-a-glance pacing</h2>
						<p class="mt-2 type-body text-ink/80">
							{{
								isSectionCollapsed(SECTION_IDS.timeline)
									? 'Open the calendar view to see unit pacing against the real school schedule.'
									: 'See the governed unit sequence against instructional dates, terms, and break periods.'
							}}
						</p>
					</div>
					<div class="flex flex-wrap items-center gap-2 lg:justify-end">
						<span v-if="timelineScopeLabel" class="chip">{{ timelineScopeLabel }}</span>
						<span v-if="timelineDateLabel" class="chip">{{ timelineDateLabel }}</span>
						<span class="chip">
							{{ surface.curriculum.timeline.summary.scheduled_unit_count || 0 }} scheduled units
						</span>
						<span v-if="surface.curriculum.timeline.holidays.length" class="chip">
							{{ surface.curriculum.timeline.holidays.length }} holiday spans
						</span>
						<span class="chip">{{
							isSectionCollapsed(SECTION_IDS.timeline) ? 'Show' : 'Hide'
						}}</span>
					</div>
				</button>

				<div v-if="!isSectionCollapsed(SECTION_IDS.timeline)" class="mt-6">
					<CoursePlanTimelineCard :timeline="surface.curriculum.timeline" hide-header embedded />
				</div>
			</section>

			<section class="grid gap-6 xl:grid-cols-[minmax(0,20rem),minmax(0,1fr)]">
				<aside class="space-y-6 xl:self-start">
					<section
						:id="SECTION_IDS.courseResources"
						class="scroll-mt-40 rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
					>
						<button
							type="button"
							class="flex w-full flex-col gap-4 text-left lg:flex-row lg:items-start lg:justify-between"
							:aria-expanded="!isSectionCollapsed(SECTION_IDS.courseResources)"
							@click="toggleSection(SECTION_IDS.courseResources)"
						>
							<div>
								<p class="type-overline text-ink/60">Shared Plan Resources</p>
								<h2 class="mt-2 type-h2 text-ink">Resources for every class using this plan</h2>
								<p class="mt-2 type-body text-ink/80">
									{{
										isSectionCollapsed(SECTION_IDS.courseResources)
											? 'Open the governed references, links, and shared files attached at the course-plan level.'
											: 'Keep governed references, anchor texts, and shared files at the course-plan level.'
									}}
								</p>
							</div>
							<div class="flex flex-wrap items-center gap-2 lg:justify-end">
								<span class="chip">{{ coursePlanResourceCount }} resources</span>
								<span class="chip">{{
									isSectionCollapsed(SECTION_IDS.courseResources) ? 'Show' : 'Hide'
								}}</span>
							</div>
						</button>

						<div v-if="!isSectionCollapsed(SECTION_IDS.courseResources)" class="mt-6">
							<PlanningResourcePanel
								anchor-doctype="Course Plan"
								:anchor-name="surface.course_plan.course_plan"
								:can-manage="canManagePlan"
								eyebrow="Shared Plan Resources"
								title="Resources for every class using this plan"
								description="Keep governed references, anchor texts, and shared files at the course-plan level."
								empty-message="No shared course-plan resources yet."
								blocked-message="Choose a course plan before sharing resources."
								read-only-message="Only approved curriculum staff can edit shared course-plan resources."
								:resources="surface.resources.course_plan_resources"
								hide-header
								embedded
								@changed="loadSurface"
							/>
						</div>
					</section>

					<section
						:id="SECTION_IDS.units"
						class="scroll-mt-40 rounded-[2rem] border border-line-soft bg-white p-5 shadow-soft"
					>
						<div class="mb-4 flex items-center justify-between gap-3">
							<div>
								<p class="type-overline text-ink/60">Unit Backbone</p>
								<h2 class="mt-1 type-h3 text-ink">Governed sequence</h2>
							</div>
							<span class="chip">{{ surface.curriculum.unit_count }}</span>
						</div>

						<div class="space-y-3">
							<button
								v-for="unit in surface.curriculum.units"
								:key="unit.unit_plan"
								type="button"
								class="w-full rounded-2xl border p-4 text-left transition"
								:class="
									selectedUnit?.unit_plan === unit.unit_plan && !creatingUnit
										? 'border-jacaranda bg-jacaranda/10 shadow-soft'
										: 'border-line-soft bg-surface-soft hover:border-jacaranda/40'
								"
								@click="selectUnit(unit.unit_plan)"
							>
								<div class="flex items-start justify-between gap-3">
									<div class="min-w-0">
										<p class="type-overline text-ink/60">Unit {{ unit.unit_order || '—' }}</p>
										<p class="mt-1 type-body-strong text-ink">{{ unit.title }}</p>
									</div>
									<span class="chip">{{ unit.shared_resources.length }} resources</span>
								</div>
							</button>

							<div
								v-if="!surface.curriculum.units.length"
								class="rounded-2xl border border-dashed border-line-soft p-4"
							>
								<p class="type-caption text-ink/70">
									Add the first unit plan to define the shared curriculum backbone.
								</p>
							</div>
						</div>

						<div v-if="canManagePlan" class="mt-4">
							<button type="button" class="if-action w-full" @click="startNewUnit">
								{{ creatingUnit ? 'Editing New Unit' : 'New Unit Plan' }}
							</button>
						</div>
					</section>
				</aside>

				<section
					v-if="showUnitEditor"
					:id="SECTION_IDS.unitEditor"
					class="scroll-mt-40 space-y-6 rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
				>
					<button
						type="button"
						class="flex w-full flex-col gap-4 text-left lg:flex-row lg:items-start lg:justify-between"
						:aria-expanded="!isSectionCollapsed(SECTION_IDS.unitEditor)"
						@click="toggleSection(SECTION_IDS.unitEditor)"
					>
						<div>
							<p class="type-overline text-ink/60">
								{{ creatingUnit ? 'New Unit Plan' : 'Selected Unit' }}
							</p>
							<h2 class="mt-2 type-h2 text-ink">
								{{ creatingUnit ? 'Draft a governed unit' : selectedUnit?.title || 'Unit Plan' }}
							</h2>
							<p class="mt-2 type-body text-ink/80">
								{{
									isSectionCollapsed(SECTION_IDS.unitEditor)
										? 'Open the governed unit content, standards, reflections, and shared resources.'
										: 'Keep the unit backbone shared while class teaching plans continue to own pacing, sessions, and local delivery choices.'
								}}
							</p>
						</div>
						<div class="flex flex-wrap items-center gap-2">
							<span v-if="!creatingUnit" class="chip">Unit {{ unitForm.unit_order || '—' }}</span>
							<span v-if="unitForm.unit_status" class="chip">{{ unitForm.unit_status }}</span>
							<span v-if="unitForm.duration" class="chip">{{ unitForm.duration }}</span>
							<span v-if="unitForm.estimated_duration" class="chip">
								{{ unitForm.estimated_duration }}
							</span>
							<span
								v-if="selectedUnitTimelineState?.start_date && selectedUnitTimelineState?.end_date"
								class="chip"
							>
								{{ selectedUnitTimelineState.start_date }} →
								{{ selectedUnitTimelineState.end_date }}
							</span>
							<span class="chip">{{
								isSectionCollapsed(SECTION_IDS.unitEditor) ? 'Show' : 'Hide'
							}}</span>
						</div>
					</button>

					<template v-if="!isSectionCollapsed(SECTION_IDS.unitEditor)">
						<div v-if="canManagePlan" class="grid gap-4 lg:grid-cols-2">
							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Unit Title</span>
								<input
									v-model="unitForm.title"
									data-quick-focus="unit-title"
									type="text"
									class="if-input w-full"
									placeholder="e.g. Cells and Systems"
								/>
							</label>
							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Program</span>
								<select v-model="unitForm.program" class="if-input w-full">
									<option value="">Optional program</option>
									<option
										v-for="option in courseProgramOptions"
										:key="option.value"
										:value="option.value"
									>
										{{ option.label }}
									</option>
								</select>
								<p class="type-caption text-ink/60">
									{{
										courseProgramOptions.length
											? 'Only Program records already linked to this course are available here.'
											: 'No Program records currently link to this course.'
									}}
								</p>
							</label>
							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Unit Code</span>
								<input
									v-model="unitForm.unit_code"
									type="text"
									class="if-input w-full"
									placeholder="Optional unit code"
								/>
							</label>
							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Unit Order</span>
								<input
									v-model.number="unitForm.unit_order"
									type="number"
									min="1"
									step="1"
									class="if-input w-full"
								/>
							</label>
							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Unit Status</span>
								<select v-model="unitForm.unit_status" class="if-input w-full">
									<option v-for="option in unitStatusOptions" :key="option" :value="option">
										{{ option }}
									</option>
								</select>
							</label>
							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Version</span>
								<input
									v-model="unitForm.version"
									type="text"
									class="if-input w-full"
									placeholder="Optional version"
								/>
							</label>
							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Duration</span>
								<input
									v-model="unitForm.duration"
									type="text"
									class="if-input w-full"
									placeholder="e.g. 6 weeks"
								/>
							</label>
							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Estimated Duration</span>
								<input
									v-model="unitForm.estimated_duration"
									type="text"
									class="if-input w-full"
									placeholder="e.g. 24 GLH"
								/>
							</label>
							<label
								class="flex items-center gap-3 rounded-2xl border border-line-soft bg-surface-soft px-4 py-4 lg:col-span-2"
							>
								<input v-model="unitForm.is_published" type="checkbox" class="h-4 w-4" />
								<div>
									<p class="type-body-strong text-ink">Published for class inheritance</p>
									<p class="type-caption text-ink/70">
										Use this when the governed unit is ready for linked classes to inherit.
									</p>
								</div>
							</label>
							<label class="block space-y-2 lg:col-span-2">
								<span class="type-caption text-ink/70">Overview & Rationale</span>
								<PlanningRichTextField
									v-model="unitForm.overview"
									placeholder="State the unit arc, rationale, and what makes this backbone important."
									min-height-class="min-h-[8rem]"
								/>
							</label>
							<label class="block space-y-2 lg:col-span-2">
								<span class="type-caption text-ink/70">Essential Understanding</span>
								<PlanningRichTextField
									v-model="unitForm.essential_understanding"
									placeholder="Capture the shared understanding every class should build."
									min-height-class="min-h-[8rem]"
								/>
							</label>
							<label class="block space-y-2 lg:col-span-2">
								<span class="type-caption text-ink/70">Likely Misconceptions</span>
								<PlanningRichTextField
									v-model="unitForm.misconceptions"
									placeholder="List likely misunderstandings students may bring into the unit."
									min-height-class="min-h-[8rem]"
								/>
							</label>
							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Content</span>
								<PlanningRichTextField
									v-model="unitForm.content"
									placeholder="What should students know?"
									min-height-class="min-h-[8rem]"
								/>
							</label>
							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Skills</span>
								<PlanningRichTextField
									v-model="unitForm.skills"
									placeholder="What should students be able to do?"
									min-height-class="min-h-[8rem]"
								/>
							</label>
							<label class="block space-y-2 lg:col-span-2">
								<span class="type-caption text-ink/70">Concepts</span>
								<PlanningRichTextField
									v-model="unitForm.concepts"
									placeholder="Which big ideas or concepts should anchor the unit?"
									min-height-class="min-h-[8rem]"
								/>
							</label>
						</div>

						<div v-else class="grid gap-4 lg:grid-cols-2">
							<div
								v-if="hasRichTextContent(selectedUnit?.overview)"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Overview</p>
								<PlanningRichTextField
									:model-value="selectedUnit?.overview"
									:editable="false"
									display-class="mt-2 text-ink/80"
								/>
							</div>
							<div
								v-if="hasRichTextContent(selectedUnit?.essential_understanding)"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Essential Understanding</p>
								<PlanningRichTextField
									:model-value="selectedUnit?.essential_understanding"
									:editable="false"
									display-class="mt-2 text-ink/80"
								/>
							</div>
							<div
								v-if="hasRichTextContent(selectedUnit?.content)"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Content</p>
								<PlanningRichTextField
									:model-value="selectedUnit?.content"
									:editable="false"
									display-class="mt-2 text-ink/80"
								/>
							</div>
							<div
								v-if="hasRichTextContent(selectedUnit?.skills)"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Skills</p>
								<PlanningRichTextField
									:model-value="selectedUnit?.skills"
									:editable="false"
									display-class="mt-2 text-ink/80"
								/>
							</div>
							<div
								v-if="hasRichTextContent(selectedUnit?.concepts)"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Concepts</p>
								<PlanningRichTextField
									:model-value="selectedUnit?.concepts"
									:editable="false"
									display-class="mt-2 text-ink/80"
								/>
							</div>
							<div
								v-if="hasRichTextContent(selectedUnit?.misconceptions)"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Likely Misconceptions</p>
								<PlanningRichTextField
									:model-value="selectedUnit?.misconceptions"
									:editable="false"
									display-class="mt-2 text-ink/80"
								/>
							</div>
						</div>

						<section :id="SECTION_IDS.standards" class="scroll-mt-40 space-y-3">
							<div class="flex items-center justify-between gap-3">
								<div>
									<p class="type-overline text-ink/60">Standards Alignment</p>
									<h3 class="mt-1 type-h3 text-ink">Shared alignment rows</h3>
								</div>
								<div class="flex items-center gap-2">
									<span class="chip">{{ unitForm.standards.length }}</span>
									<button
										v-if="canManagePlan"
										type="button"
										class="if-action if-action--subtle"
										@click="openStandardsOverlay"
									>
										Select Standards
									</button>
								</div>
							</div>

							<div
								v-if="legacyStandardsCount"
								class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3"
							>
								<p class="type-body-strong text-amber-950">
									{{ legacyStandardsCount }} standards row{{
										legacyStandardsCount > 1 ? 's need' : ' needs'
									}}
									re-selection
								</p>
								<p class="mt-1 type-caption text-amber-900/80">
									These rows do not yet carry a catalog link. Remove and re-add them through Select
									Standards so the unit saves against the approved learning-standards master.
								</p>
							</div>

							<div
								v-if="!unitForm.standards.length"
								class="rounded-2xl border border-dashed border-line-soft p-4"
							>
								<p class="type-caption text-ink/70">
									No standards have been captured for this unit yet.
								</p>
							</div>

							<div v-else class="space-y-4">
								<article
									v-for="standard in unitForm.standards"
									:key="standard.local_id"
									class="rounded-2xl border border-line-soft bg-surface-soft p-4"
								>
									<div class="grid gap-4 lg:grid-cols-2">
										<label class="block space-y-2">
											<span class="type-caption text-ink/70">Framework Name</span>
											<input
												v-model="standard.framework_name"
												type="text"
												class="if-input w-full"
												disabled
											/>
										</label>
										<label class="block space-y-2">
											<span class="type-caption text-ink/70">Framework Version</span>
											<input
												v-model="standard.framework_version"
												type="text"
												class="if-input w-full"
												disabled
											/>
										</label>
										<label class="block space-y-2">
											<span class="type-caption text-ink/70">Subject Area</span>
											<input
												v-model="standard.subject_area"
												type="text"
												class="if-input w-full"
												disabled
											/>
										</label>
										<label class="block space-y-2">
											<span class="type-caption text-ink/70">Program</span>
											<input
												v-model="standard.program"
												type="text"
												class="if-input w-full"
												disabled
											/>
										</label>
										<label class="block space-y-2">
											<span class="type-caption text-ink/70">Strand</span>
											<input
												v-model="standard.strand"
												type="text"
												class="if-input w-full"
												disabled
											/>
										</label>
										<label class="block space-y-2">
											<span class="type-caption text-ink/70">Substrand</span>
											<input
												v-model="standard.substrand"
												type="text"
												class="if-input w-full"
												disabled
											/>
										</label>
										<label class="block space-y-2">
											<span class="type-caption text-ink/70">Standard Code</span>
											<input
												v-model="standard.standard_code"
												type="text"
												class="if-input w-full"
												disabled
											/>
										</label>
										<label class="block space-y-2">
											<span class="type-caption text-ink/70">Coverage Level</span>
											<select
												v-model="standard.coverage_level"
												class="if-input w-full"
												:disabled="!canManagePlan"
											>
												<option value="">Select</option>
												<option
													v-for="option in coverageLevelOptions"
													:key="option"
													:value="option"
												>
													{{ option }}
												</option>
											</select>
										</label>
										<label class="block space-y-2">
											<span class="type-caption text-ink/70">Alignment Strength</span>
											<select
												v-model="standard.alignment_strength"
												class="if-input w-full"
												:disabled="!canManagePlan"
											>
												<option value="">Select</option>
												<option
													v-for="option in alignmentStrengthOptions"
													:key="option"
													:value="option"
												>
													{{ option }}
												</option>
											</select>
										</label>
										<label class="block space-y-2">
											<span class="type-caption text-ink/70">Alignment Type</span>
											<input
												v-model="standard.alignment_type"
												type="text"
												class="if-input w-full"
												disabled
											/>
										</label>
										<label class="block space-y-2 lg:col-span-2">
											<span class="type-caption text-ink/70">Standard Description</span>
											<textarea
												v-model="standard.standard_description"
												rows="3"
												class="if-input min-h-[6rem] w-full resize-y"
												disabled
											/>
										</label>
										<label class="block space-y-2 lg:col-span-2">
											<span class="type-caption text-ink/70">Notes</span>
											<textarea
												v-model="standard.notes"
												rows="3"
												class="if-input min-h-[6rem] w-full resize-y"
												:disabled="!canManagePlan"
											/>
										</label>
									</div>
									<div v-if="canManagePlan" class="mt-4 flex justify-end">
										<button
											type="button"
											class="if-action if-action--subtle"
											@click="removeStandard(standard.local_id)"
										>
											Remove Standard
										</button>
									</div>
								</article>
							</div>
						</section>

						<section :id="SECTION_IDS.reflections" class="scroll-mt-40 space-y-3">
							<div class="flex items-center justify-between gap-3">
								<div>
									<p class="type-overline text-ink/60">Shared Reflections</p>
									<h3 class="mt-1 type-h3 text-ink">Bird's-eye planning notes</h3>
								</div>
								<div class="flex items-center gap-2">
									<span class="chip">{{ unitForm.reflections.length }}</span>
									<button
										v-if="canManagePlan"
										type="button"
										class="if-action if-action--subtle"
										@click="addReflection"
									>
										Add Reflection
									</button>
								</div>
							</div>

							<div
								v-if="!unitForm.reflections.length"
								class="rounded-2xl border border-dashed border-line-soft p-4"
							>
								<p class="type-caption text-ink/70">
									No shared reflections captured yet for this unit.
								</p>
							</div>

							<div v-else class="space-y-4">
								<article
									v-for="reflection in unitForm.reflections"
									:key="reflection.local_id"
									class="rounded-2xl border border-line-soft bg-surface-soft p-4"
								>
									<div class="grid gap-4 lg:grid-cols-2">
										<label class="block space-y-2">
											<span class="type-caption text-ink/70">Academic Year</span>
											<input
												:value="reflection.academic_year || derivedReflectionAcademicYear"
												type="text"
												class="if-input w-full"
												disabled
											/>
										</label>
										<label class="block space-y-2">
											<span class="type-caption text-ink/70">School</span>
											<input
												:value="reflection.school || derivedReflectionSchool"
												type="text"
												class="if-input w-full"
												disabled
											/>
										</label>
										<p class="type-caption text-ink/60 lg:col-span-2">
											Academic Year and School stay derived from the parent course plan.
										</p>
										<label class="block space-y-2 lg:col-span-2">
											<span class="type-caption text-ink/70">Prior To The Unit</span>
											<PlanningRichTextField
												v-model="reflection.prior_to_the_unit"
												:editable="canManagePlan"
												min-height-class="min-h-[6rem]"
											/>
										</label>
										<label class="block space-y-2 lg:col-span-2">
											<span class="type-caption text-ink/70">During The Unit</span>
											<PlanningRichTextField
												v-model="reflection.during_the_unit"
												:editable="canManagePlan"
												min-height-class="min-h-[6rem]"
											/>
										</label>
										<label class="block space-y-2 lg:col-span-2">
											<span class="type-caption text-ink/70">What Worked Well</span>
											<PlanningRichTextField
												v-model="reflection.what_work_well"
												:editable="canManagePlan"
												min-height-class="min-h-[6rem]"
											/>
										</label>
										<label class="block space-y-2 lg:col-span-2">
											<span class="type-caption text-ink/70">What Didn't Work Well</span>
											<PlanningRichTextField
												v-model="reflection.what_didnt_work_well"
												:editable="canManagePlan"
												min-height-class="min-h-[6rem]"
											/>
										</label>
										<label class="block space-y-2 lg:col-span-2">
											<span class="type-caption text-ink/70">Change Suggestions</span>
											<PlanningRichTextField
												v-model="reflection.changes_suggestions"
												:editable="canManagePlan"
												min-height-class="min-h-[6rem]"
											/>
										</label>
									</div>
									<div v-if="canManagePlan" class="mt-4 flex justify-end">
										<button
											type="button"
											class="if-action if-action--subtle"
											@click="removeReflection(reflection.local_id)"
										>
											Remove Reflection
										</button>
									</div>
								</article>
							</div>
						</section>

						<section v-if="selectedUnit?.class_reflections?.length" class="space-y-3">
							<div class="flex items-center justify-between gap-3">
								<h3 class="type-h3 text-ink">Class Reflections Across This Unit</h3>
								<span class="chip">{{ selectedUnit.class_reflections.length }}</span>
							</div>
							<div class="grid gap-3 xl:grid-cols-2">
								<article
									v-for="reflection in selectedUnit.class_reflections"
									:key="`${selectedUnit.unit_plan}-${reflection.class_teaching_plan}`"
									class="rounded-2xl border border-line-soft bg-surface-soft p-4"
								>
									<div class="flex items-center justify-between gap-3">
										<p class="type-body-strong text-ink">{{ reflection.class_label }}</p>
										<span v-if="reflection.academic_year" class="chip">
											{{ reflection.academic_year }}
										</span>
									</div>
									<div
										v-if="hasRichTextContent(reflection.prior_to_the_unit)"
										class="mt-3 space-y-2"
									>
										<p class="type-overline text-ink/60">Prior To The Unit</p>
										<PlanningRichTextField
											:model-value="reflection.prior_to_the_unit"
											:editable="false"
											display-class="text-ink/80"
										/>
									</div>
									<div
										v-if="hasRichTextContent(reflection.during_the_unit)"
										class="mt-3 space-y-2"
									>
										<p class="type-overline text-ink/60">During The Unit</p>
										<PlanningRichTextField
											:model-value="reflection.during_the_unit"
											:editable="false"
											display-class="text-ink/80"
										/>
									</div>
									<div v-if="hasRichTextContent(reflection.what_work_well)" class="mt-3 space-y-2">
										<p class="type-overline text-ink/60">What Worked Well</p>
										<PlanningRichTextField
											:model-value="reflection.what_work_well"
											:editable="false"
											display-class="text-ink/70"
										/>
									</div>
									<div
										v-if="hasRichTextContent(reflection.what_didnt_work_well)"
										class="mt-3 space-y-2"
									>
										<p class="type-overline text-ink/60">Watch For</p>
										<PlanningRichTextField
											:model-value="reflection.what_didnt_work_well"
											:editable="false"
											display-class="text-ink/70"
										/>
									</div>
									<div
										v-if="hasRichTextContent(reflection.changes_suggestions)"
										class="mt-3 space-y-2"
									>
										<p class="type-overline text-ink/60">Next Change</p>
										<PlanningRichTextField
											:model-value="reflection.changes_suggestions"
											:editable="false"
											display-class="text-ink/70"
										/>
									</div>
								</article>
							</div>
						</section>

						<div v-if="canManagePlan" class="flex justify-end gap-3">
							<button
								v-if="creatingUnit"
								type="button"
								class="if-action if-action--subtle"
								@click="cancelNewUnit"
							>
								Cancel New Unit
							</button>
							<button
								type="button"
								class="if-action"
								:disabled="unitPending"
								@click="handleSaveUnitPlan"
							>
								{{
									unitPending ? 'Saving...' : creatingUnit ? 'Create Unit Plan' : 'Save Unit Plan'
								}}
							</button>
						</div>

						<div :id="SECTION_IDS.unitResources" class="scroll-mt-40">
							<PlanningResourcePanel
								anchor-doctype="Unit Plan"
								:anchor-name="selectedUnit?.unit_plan || null"
								:can-manage="canManagePlan"
								eyebrow="Unit Resources"
								title="Shared resources for this unit"
								description="Use this layer for governed materials every class should inherit while teaching the unit."
								empty-message="No governed unit resources yet."
								blocked-message="Save the unit plan before sharing unit resources."
								read-only-message="Only approved curriculum staff can edit shared unit resources."
								:resources="selectedUnit?.shared_resources || []"
								@changed="loadSurface"
							/>
						</div>
					</template>
				</section>

				<section v-else class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
					<p class="type-body text-ink/70">
						Select a governed unit to edit the shared backbone, or create a new unit plan.
					</p>
				</section>
			</section>

			<section
				:id="SECTION_IDS.quizBanks"
				class="scroll-mt-40 rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
			>
				<button
					type="button"
					class="flex w-full flex-col gap-4 text-left lg:flex-row lg:items-start lg:justify-between"
					:aria-expanded="!isSectionCollapsed(SECTION_IDS.quizBanks)"
					@click="toggleSection(SECTION_IDS.quizBanks)"
				>
					<div>
						<p class="type-overline text-ink/60">Course Quiz Banks</p>
						<h2 class="mt-2 type-h2 text-ink">Shared quiz authoring</h2>
						<p class="mt-2 type-body text-ink/80">
							{{
								isSectionCollapsed(SECTION_IDS.quizBanks)
									? 'Open the course-level question banks when you need to author, revise, or assign a reusable quiz.'
									: 'Build question banks once, then assign them through the class task flow without rewriting the quiz each time.'
							}}
						</p>
					</div>
					<div class="flex flex-wrap items-center gap-2 lg:justify-end">
						<span class="chip">{{ surface.assessment.quiz_question_banks.length }} banks</span>
						<span v-if="selectedQuizBankLabel" class="chip">{{ selectedQuizBankLabel }}</span>
						<span class="chip">{{
							isSectionCollapsed(SECTION_IDS.quizBanks) ? 'Show' : 'Hide'
						}}</span>
					</div>
				</button>

				<div
					v-if="!isSectionCollapsed(SECTION_IDS.quizBanks)"
					class="mt-6 grid gap-6 xl:grid-cols-[minmax(0,20rem),minmax(0,1fr)]"
				>
					<aside class="space-y-4 xl:self-start">
						<section class="rounded-[1.75rem] border border-line-soft bg-surface-soft/55 p-5">
							<div class="mb-4 flex items-center justify-between gap-3">
								<div>
									<p class="type-overline text-ink/60">Course Quiz Banks</p>
									<h2 class="mt-1 type-h3 text-ink">Shared quiz authoring</h2>
								</div>
								<span class="chip">{{ surface.assessment.quiz_question_banks.length }}</span>
							</div>

							<p class="mb-4 type-caption text-ink/70">
								Quiz banks are shared at the course level so teachers can assign them later from
								the class task flow.
							</p>

							<div class="space-y-3">
								<button
									v-for="bank in surface.assessment.quiz_question_banks"
									:key="bank.quiz_question_bank"
									type="button"
									class="w-full rounded-2xl border p-4 text-left transition"
									:class="
										selectedQuizQuestionBank?.quiz_question_bank === bank.quiz_question_bank &&
										!creatingQuizQuestionBank
											? 'border-jacaranda bg-jacaranda/10 shadow-soft'
											: 'border-line-soft bg-surface-soft hover:border-jacaranda/40'
									"
									@click="selectQuizQuestionBank(bank.quiz_question_bank)"
								>
									<div class="flex items-start justify-between gap-3">
										<div class="min-w-0">
											<p class="type-body-strong text-ink">{{ bank.bank_title }}</p>
											<p class="mt-1 type-caption text-ink/70">
												{{ bank.published_question_count || 0 }} published of
												{{ bank.question_count || 0 }} total
											</p>
										</div>
										<span class="chip">
											{{ bank.is_published ? 'Ready' : 'Draft' }}
										</span>
									</div>
								</button>

								<div
									v-if="!surface.assessment.quiz_question_banks.length"
									class="rounded-2xl border border-dashed border-line-soft p-4"
								>
									<p class="type-caption text-ink/70">No course quiz banks yet.</p>
								</div>
							</div>

							<div v-if="canManagePlan" class="mt-4">
								<button type="button" class="if-action w-full" @click="startNewQuizQuestionBank">
									{{ creatingQuizQuestionBank ? 'Editing New Quiz Bank' : 'New Quiz Bank' }}
								</button>
							</div>
						</section>
					</aside>

					<section class="rounded-[1.75rem] border border-line-soft bg-surface-soft/40 p-6">
						<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
							<div>
								<p class="type-overline text-ink/60">
									{{ creatingQuizQuestionBank ? 'New Quiz Bank' : 'Selected Quiz Bank' }}
								</p>
								<h2 class="mt-2 type-h2 text-ink">
									{{
										creatingQuizQuestionBank
											? 'Draft a reusable quiz bank'
											: quizBankForm.bank_title || 'Quiz Bank'
									}}
								</h2>
								<p class="mt-2 type-body text-ink/80">
									Build question banks once, then assign them through the class task flow without
									rewriting the quiz each time.
								</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<span class="chip"> {{ quizBankForm.questions.length }} questions </span>
								<span class="chip">
									{{ quizBankForm.is_published ? 'Published' : 'Draft only' }}
								</span>
								<button
									v-if="canManagePlan && !creatingQuizQuestionBank && selectedQuizQuestionBank"
									type="button"
									class="if-action if-action--subtle"
									:disabled="!selectedQuizQuestionBank.is_published"
									@click="openAssignFromQuizBank(selectedQuizQuestionBank)"
								>
									Assign This Quiz
								</button>
							</div>
						</div>
						<p
							v-if="
								canManagePlan &&
								!creatingQuizQuestionBank &&
								selectedQuizQuestionBank &&
								!selectedQuizQuestionBank.is_published
							"
							class="mt-3 type-caption text-ink/70"
						>
							Publish the quiz bank before assigning it to a class.
						</p>

						<div
							v-if="!showQuizBankEditor"
							class="mt-6 rounded-2xl border border-dashed border-line-soft p-5"
						>
							<p class="type-caption text-ink/70">
								Select a quiz bank, or create a new one for this course.
							</p>
						</div>

						<template v-else>
							<div v-if="canManagePlan" class="mt-6 grid gap-4 lg:grid-cols-2">
								<label class="block space-y-2">
									<span class="type-caption text-ink/70">Bank Title</span>
									<input
										v-model="quizBankForm.bank_title"
										data-quick-focus="quiz-bank-title"
										type="text"
										class="if-input w-full"
										placeholder="e.g. Cell Structure Check-in"
									/>
								</label>
								<label
									class="flex items-center gap-3 rounded-2xl border border-line-soft bg-surface-soft px-4 py-4"
								>
									<input v-model="quizBankForm.is_published" type="checkbox" class="h-4 w-4" />
									<div>
										<p class="type-body-strong text-ink">Ready for assignment</p>
										<p class="type-caption text-ink/70">
											Published banks appear in the quiz selection step when teachers assign work.
										</p>
									</div>
								</label>
								<label class="block space-y-2 lg:col-span-2">
									<span class="type-caption text-ink/70">Description</span>
									<textarea
										v-model="quizBankForm.description"
										rows="4"
										class="if-input min-h-[8rem] w-full resize-y"
										placeholder="Explain what this quiz bank checks and when teachers should use it."
									/>
								</label>
							</div>

							<section class="mt-6 space-y-4">
								<div class="flex items-center justify-between gap-3">
									<div>
										<p class="type-overline text-ink/60">Questions</p>
										<h3 class="mt-1 type-h3 text-ink">Reusable quiz items</h3>
									</div>
									<button
										v-if="canManagePlan"
										type="button"
										class="if-action if-action--subtle"
										@click="addQuizQuestion"
									>
										Add Question
									</button>
								</div>

								<div
									v-if="!quizBankForm.questions.length"
									class="rounded-2xl border border-dashed border-line-soft p-4"
								>
									<p class="type-caption text-ink/70">
										No questions yet. Add reusable questions teachers can pull into quiz-backed
										tasks.
									</p>
								</div>

								<div v-else class="space-y-4">
									<article
										v-for="question in quizBankForm.questions"
										:key="question.local_id"
										class="rounded-2xl border border-line-soft bg-surface-soft p-4"
									>
										<div class="grid gap-4 lg:grid-cols-2">
											<label class="block space-y-2">
												<span class="type-caption text-ink/70">Question Title</span>
												<input
													v-model="question.title"
													type="text"
													class="if-input w-full"
													placeholder="e.g. Identify the nucleus"
													:disabled="!canManagePlan"
												/>
											</label>
											<label class="block space-y-2">
												<span class="type-caption text-ink/70">Question Type</span>
												<select
													v-model="question.question_type"
													class="if-input w-full"
													:disabled="!canManagePlan"
													@change="handleQuizQuestionTypeChange(question)"
												>
													<option
														v-for="option in quizQuestionTypeOptions"
														:key="option"
														:value="option"
													>
														{{ option }}
													</option>
												</select>
											</label>
											<label
												class="flex items-center gap-3 rounded-2xl border border-line-soft bg-white px-4 py-4 lg:col-span-2"
											>
												<input
													v-model="question.is_published"
													type="checkbox"
													class="h-4 w-4"
													:disabled="!canManagePlan"
												/>
												<div>
													<p class="type-body-strong text-ink">Published in the bank</p>
													<p class="type-caption text-ink/70">
														Only published questions are available for quiz attempts.
													</p>
												</div>
											</label>
											<label class="block space-y-2 lg:col-span-2">
												<span class="type-caption text-ink/70">Prompt</span>
												<PlanningRichTextField
													v-model="question.prompt"
													:editable="canManagePlan"
													min-height-class="min-h-[8rem]"
												/>
											</label>
											<label
												v-if="question.question_type === 'Short Answer'"
												class="block space-y-2 lg:col-span-2"
											>
												<span class="type-caption text-ink/70">Accepted Answers</span>
												<textarea
													v-model="question.accepted_answers"
													rows="4"
													class="if-input min-h-[8rem] w-full resize-y"
													placeholder="One accepted answer per line"
													:disabled="!canManagePlan"
												/>
											</label>
										</div>

										<section
											v-if="isChoiceQuestion(question.question_type)"
											class="mt-4 space-y-3 rounded-2xl border border-line-soft bg-white p-4"
										>
											<div class="flex items-center justify-between gap-3">
												<div>
													<p class="type-overline text-ink/60">Answer Options</p>
													<h4 class="mt-1 type-body-strong text-ink">Choice payload</h4>
												</div>
												<button
													v-if="canManagePlan && question.question_type !== 'True / False'"
													type="button"
													class="if-action if-action--subtle"
													@click="addQuizOption(question)"
												>
													Add Option
												</button>
											</div>

											<div class="space-y-3">
												<div
													v-for="option in question.options"
													:key="option.local_id"
													class="grid gap-3 rounded-2xl border border-line-soft bg-surface-soft p-3 md:grid-cols-[minmax(0,1fr),auto,auto]"
												>
													<input
														v-model="option.option_text"
														type="text"
														class="if-input w-full"
														placeholder="Option text"
														:disabled="!canManagePlan"
													/>
													<label
														class="flex items-center gap-2 rounded-xl border border-line-soft bg-white px-3 py-2 type-caption text-ink/70"
													>
														<input
															v-model="option.is_correct"
															type="checkbox"
															class="h-4 w-4"
															:disabled="!canManagePlan"
														/>
														<span>Correct</span>
													</label>
													<button
														v-if="canManagePlan && question.question_type !== 'True / False'"
														type="button"
														class="if-action if-action--subtle"
														@click="removeQuizOption(question, option.local_id)"
													>
														Remove
													</button>
												</div>
											</div>
										</section>

										<label class="mt-4 block space-y-2">
											<span class="type-caption text-ink/70">Explanation</span>
											<PlanningRichTextField
												v-model="question.explanation"
												placeholder="Optional feedback or explanation shown when allowed."
												:editable="canManagePlan"
												min-height-class="min-h-[6rem]"
											/>
										</label>

										<div v-if="canManagePlan" class="mt-4 flex justify-end">
											<button
												type="button"
												class="if-action if-action--subtle"
												@click="removeQuizQuestion(question.local_id)"
											>
												Remove Question
											</button>
										</div>
									</article>
								</div>
							</section>

							<div v-if="canManagePlan" class="mt-6 flex flex-wrap justify-end gap-3">
								<button
									v-if="creatingQuizQuestionBank"
									type="button"
									class="if-action if-action--subtle"
									@click="cancelNewQuizQuestionBank"
								>
									Cancel New Quiz Bank
								</button>
								<button
									type="button"
									class="if-action"
									:disabled="quizBankPending"
									@click="handleSaveQuizQuestionBank"
								>
									{{
										quizBankPending
											? 'Saving...'
											: creatingQuizQuestionBank
												? 'Create Quiz Bank'
												: 'Save Quiz Bank'
									}}
								</button>
							</div>
						</template>
					</section>
				</div>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { toast } from 'frappe-ui';
import { useRoute, useRouter } from 'vue-router';

import CoursePlanTimelineCard from '@/components/planning/CoursePlanTimelineCard.vue';
import PlanningRichTextField from '@/components/planning/PlanningRichTextField.vue';
import PlanningResourcePanel from '@/components/planning/PlanningResourcePanel.vue';
import { useOverlayStack } from '@/composables/useOverlayStack';
import {
	getStaffCoursePlanSurface,
	saveCoursePlan,
	saveGovernedUnitPlan,
	saveQuizQuestionBank,
} from '@/lib/services/staff/staffTeachingService';
import type { StaffLearningStandardPickerRow } from '@/types/contracts/staff_teaching/get_learning_standard_picker';
import type {
	Response as StaffCoursePlanSurfaceResponse,
	StaffCoursePlanQuizQuestion,
	StaffCoursePlanQuizQuestionBank,
	StaffCoursePlanQuizQuestionOption,
	StaffCoursePlanTimelineUnit,
	StaffCoursePlanUnit,
} from '@/types/contracts/staff_teaching/get_staff_course_plan_surface';
import type {
	StaffPlanningReflection,
	StaffPlanningStandard,
} from '@/types/contracts/staff_teaching/get_staff_class_planning_surface';

type EditableStandard = StaffPlanningStandard & {
	local_id: number;
};

type EditableReflection = StaffPlanningReflection & {
	local_id: number;
};

type EditableQuizQuestionOption = Omit<StaffCoursePlanQuizQuestionOption, 'is_correct'> & {
	local_id: number;
	is_correct: boolean;
};

type EditableQuizQuestion = Omit<StaffCoursePlanQuizQuestion, 'options' | 'is_published'> & {
	local_id: number;
	is_published: boolean;
	options: EditableQuizQuestionOption[];
};

const props = defineProps<{
	coursePlan: string;
	unitPlan?: string;
	quizQuestionBank?: string;
	studentGroup?: string;
}>();

const route = useRoute();
const router = useRouter();
const overlay = useOverlayStack();

const SECTION_IDS = {
	overview: 'course-plan-overview',
	timeline: 'course-plan-timeline',
	courseResources: 'course-plan-resources',
	units: 'course-plan-units',
	unitEditor: 'course-plan-unit-editor',
	standards: 'course-plan-standards',
	reflections: 'course-plan-reflections',
	unitResources: 'course-plan-unit-resources',
	quizBanks: 'course-plan-quiz-banks',
} as const;

type WorkspaceSectionId = (typeof SECTION_IDS)[keyof typeof SECTION_IDS];

const collapsedSectionDefaults: Record<WorkspaceSectionId, boolean> = {
	[SECTION_IDS.overview]: true,
	[SECTION_IDS.timeline]: false,
	[SECTION_IDS.courseResources]: false,
	[SECTION_IDS.units]: false,
	[SECTION_IDS.unitEditor]: false,
	[SECTION_IDS.standards]: true,
	[SECTION_IDS.reflections]: true,
	[SECTION_IDS.unitResources]: true,
	[SECTION_IDS.quizBanks]: true,
};

const surface = ref<StaffCoursePlanSurfaceResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');
const coursePlanPending = ref(false);
const unitPending = ref(false);
const quizBankPending = ref(false);
const selectedUnitPlan = ref('');
const selectedQuizQuestionBankName = ref(String(props.quizQuestionBank || '').trim());
const creatingUnit = ref(false);
const creatingQuizQuestionBank = ref(false);
const loadToken = ref(0);
const nextLocalId = ref(1);
const activeSectionId = ref<WorkspaceSectionId>(SECTION_IDS.overview);
let scrollFrame = 0;

const coursePlanForm = reactive({
	record_modified: '',
	title: '',
	academic_year: '',
	cycle_label: '',
	plan_status: 'Draft',
	summary: '',
});

const unitForm = reactive({
	unit_plan: '',
	record_modified: '',
	title: '',
	program: '',
	unit_code: '',
	unit_order: null as number | null,
	unit_status: 'Active',
	version: '',
	duration: '',
	estimated_duration: '',
	is_published: false,
	overview: '',
	essential_understanding: '',
	misconceptions: '',
	content: '',
	skills: '',
	concepts: '',
	standards: [] as EditableStandard[],
	reflections: [] as EditableReflection[],
});

const quizBankForm = reactive({
	quiz_question_bank: '',
	record_modified: '',
	bank_title: '',
	description: '',
	is_published: true,
	questions: [] as EditableQuizQuestion[],
});

const coursePlanStatusOptions = ['Draft', 'Active', 'Archived'];
const unitStatusOptions = ['Draft', 'Active', 'Archived'];
const coverageLevelOptions = ['Introduced', 'Reinforced', 'Mastered'];
const alignmentStrengthOptions = ['Exact', 'Partial', 'Broad'];
const quizQuestionTypeOptions = [
	'Single Choice',
	'Multiple Answer',
	'True / False',
	'Short Answer',
	'Essay',
];
const timelineShortDateFormatter = new Intl.DateTimeFormat(undefined, {
	month: 'short',
	day: 'numeric',
});

const selectedUnit = computed<StaffCoursePlanUnit | null>(() => {
	return (
		surface.value?.curriculum.units.find(unit => unit.unit_plan === selectedUnitPlan.value) || null
	);
});

const selectedQuizQuestionBank = computed<StaffCoursePlanQuizQuestionBank | null>(() => {
	const detail = surface.value?.assessment.selected_quiz_question_bank || null;
	if (!detail) return null;
	if (
		selectedQuizQuestionBankName.value &&
		detail.quiz_question_bank !== selectedQuizQuestionBankName.value
	) {
		return null;
	}
	return detail;
});
const collapsedSections = reactive<Record<WorkspaceSectionId, boolean>>({
	...collapsedSectionDefaults,
});

const canManagePlan = computed(() => Boolean(surface.value?.course_plan.can_manage_resources));
const coursePlanAcademicYearOptions = computed(
	() => surface.value?.field_options.academic_years || []
);
const courseProgramOptions = computed(() => surface.value?.field_options.programs || []);
const derivedReflectionAcademicYear = computed(
	() => surface.value?.course_plan.academic_year || ''
);
const derivedReflectionSchool = computed(() => surface.value?.course_plan.school || '');
const showUnitEditor = computed(() => Boolean(selectedUnit.value || creatingUnit.value));
const legacyStandardsCount = computed(
	() =>
		unitForm.standards.filter(
			standard =>
				!String(standard.learning_standard || '').trim() &&
				Boolean(
					String(standard.standard_code || '').trim() ||
					String(standard.standard_description || '').trim() ||
					String(standard.framework_name || '').trim()
				)
		).length
);
const showQuizBankEditor = computed(() =>
	Boolean(selectedQuizQuestionBank.value || creatingQuizQuestionBank.value)
);
const selectedUnitTimelineState = computed<StaffCoursePlanTimelineUnit | null>(() => {
	const timelineUnits = surface.value?.curriculum.timeline.units || [];
	return timelineUnits.find(unit => unit.unit_plan === selectedUnitPlan.value) || null;
});
const selectedQuizBankLabel = computed(() => {
	return (
		selectedQuizQuestionBank.value?.bank_title ||
		surface.value?.assessment.quiz_question_banks.find(
			bank => bank.quiz_question_bank === selectedQuizQuestionBankName.value
		)?.bank_title ||
		''
	);
});
const coursePlanResourceCount = computed(
	() => surface.value?.resources.course_plan_resources.length || 0
);
const timelineSummary = computed(() => surface.value?.curriculum.timeline || null);
const timelineScopeLabel = computed(() => {
	const timeline = timelineSummary.value;
	if (!timeline || timeline.status !== 'ready') return '';
	const scope = timeline.scope || {};
	if (scope.mode === 'student_group_term') {
		return scope.student_group_label
			? `${scope.student_group_label} · ${scope.term_label || scope.term || 'Term'}`
			: scope.term_label || scope.term || 'Term';
	}
	return scope.academic_year || '';
});
const timelineDateLabel = computed(() => {
	const timeline = timelineSummary.value;
	if (!timeline || timeline.status !== 'ready') return '';
	const start = parseIsoDate(timeline.scope.window_start);
	const end = parseIsoDate(timeline.scope.window_end);
	if (!start || !end) return '';
	return `${timelineShortDateFormatter.format(start)} to ${timelineShortDateFormatter.format(end)}`;
});
const navigationSections = computed<
	{ id: WorkspaceSectionId; label: string; count?: number | null }[]
>(() => {
	const sections: { id: WorkspaceSectionId; label: string; count?: number | null }[] = [
		{ id: SECTION_IDS.overview, label: 'Overview' },
		{ id: SECTION_IDS.timeline, label: 'Timeline' },
		{
			id: SECTION_IDS.courseResources,
			label: 'Plan Resources',
			count: surface.value?.resources.course_plan_resources.length || 0,
		},
		{
			id: SECTION_IDS.units,
			label: 'Units',
			count: surface.value?.curriculum.unit_count || 0,
		},
	];

	if (showUnitEditor.value) {
		sections.push({ id: SECTION_IDS.unitEditor, label: 'Unit Content' });
		sections.push({
			id: SECTION_IDS.standards,
			label: 'Standards',
			count: unitForm.standards.length,
		});
		sections.push({
			id: SECTION_IDS.reflections,
			label: 'Reflections',
			count: unitForm.reflections.length,
		});
	}

	if (showUnitEditor.value) {
		sections.push({
			id: SECTION_IDS.unitResources,
			label: 'Unit Resources',
			count: selectedUnit.value?.shared_resources.length || 0,
		});
	}

	sections.push({
		id: SECTION_IDS.quizBanks,
		label: 'Quiz Banks',
		count: surface.value?.assessment.quiz_question_banks.length || 0,
	});

	return sections;
});

function nextId() {
	return nextLocalId.value++;
}

function parseIsoDate(value?: string | null) {
	if (!value) return null;
	const parsed = new Date(`${value}T00:00:00`);
	return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function coursePlanSectionStorageKey() {
	return `ifitwala.course-plan.sections.${props.coursePlan}`;
}

function loadCollapsedSections() {
	Object.assign(collapsedSections, collapsedSectionDefaults);
	if (typeof window === 'undefined' || !props.coursePlan) return;
	try {
		const raw = window.localStorage.getItem(coursePlanSectionStorageKey());
		if (!raw) return;
		const parsed = JSON.parse(raw) as Partial<Record<WorkspaceSectionId, boolean>>;
		for (const sectionId of Object.values(SECTION_IDS)) {
			if (typeof parsed?.[sectionId] === 'boolean') {
				collapsedSections[sectionId] = parsed[sectionId] as boolean;
			}
		}
	} catch {
		Object.assign(collapsedSections, collapsedSectionDefaults);
	}
}

function persistCollapsedSections() {
	if (typeof window === 'undefined' || !props.coursePlan) return;
	window.localStorage.setItem(coursePlanSectionStorageKey(), JSON.stringify(collapsedSections));
}

function isSectionCollapsed(sectionId: WorkspaceSectionId) {
	return Boolean(collapsedSections[sectionId]);
}

function setSectionCollapsed(sectionId: WorkspaceSectionId, collapsed: boolean) {
	collapsedSections[sectionId] = collapsed;
	persistCollapsedSections();
}

function setSectionExpanded(sectionId: WorkspaceSectionId, expanded: boolean) {
	setSectionCollapsed(sectionId, !expanded);
}

function toggleSection(sectionId: WorkspaceSectionId) {
	setSectionCollapsed(sectionId, !isSectionCollapsed(sectionId));
}

function expandSectionChain(sectionId: WorkspaceSectionId) {
	if (
		sectionId === SECTION_IDS.standards ||
		sectionId === SECTION_IDS.reflections ||
		sectionId === SECTION_IDS.unitResources
	) {
		setSectionExpanded(SECTION_IDS.unitEditor, true);
	}
}

function isChoiceQuestion(questionType?: string | null) {
	return ['Single Choice', 'Multiple Answer', 'True / False'].includes(questionType || '');
}

function hasRichTextContent(value?: string | null) {
	return Boolean(
		String(value || '')
			.replace(/<style[\s\S]*?<\/style>/gi, ' ')
			.replace(/<script[\s\S]*?<\/script>/gi, ' ')
			.replace(/<[^>]*>/g, ' ')
			.replace(/&nbsp;|&#160;/gi, ' ')
			.trim()
	);
}

function buildEditableStandard(standard?: StaffPlanningStandard): EditableStandard {
	return {
		local_id: nextId(),
		learning_standard: standard?.learning_standard || '',
		framework_name: standard?.framework_name || '',
		framework_version: standard?.framework_version || '',
		subject_area: standard?.subject_area || '',
		program: standard?.program || unitForm.program || '',
		strand: standard?.strand || '',
		substrand: standard?.substrand || '',
		standard_code: standard?.standard_code || '',
		standard_description: standard?.standard_description || '',
		coverage_level: standard?.coverage_level || '',
		alignment_strength: standard?.alignment_strength || '',
		alignment_type: standard?.alignment_type || '',
		notes: standard?.notes || '',
	};
}

function buildEditableReflection(reflection?: StaffPlanningReflection): EditableReflection {
	return {
		local_id: nextId(),
		academic_year: reflection?.academic_year || derivedReflectionAcademicYear.value || '',
		school: reflection?.school || derivedReflectionSchool.value || '',
		prior_to_the_unit: reflection?.prior_to_the_unit || '',
		during_the_unit: reflection?.during_the_unit || '',
		what_work_well: reflection?.what_work_well || '',
		what_didnt_work_well: reflection?.what_didnt_work_well || '',
		changes_suggestions: reflection?.changes_suggestions || '',
	};
}

function buildEditableQuizOption(
	option?: StaffCoursePlanQuizQuestionOption
): EditableQuizQuestionOption {
	return {
		local_id: nextId(),
		option_text: option?.option_text || '',
		is_correct: Boolean(option?.is_correct),
	};
}

function buildEditableQuizQuestion(question?: StaffCoursePlanQuizQuestion): EditableQuizQuestion {
	return {
		local_id: nextId(),
		quiz_question: question?.quiz_question || '',
		title: question?.title || '',
		question_type: question?.question_type || 'Single Choice',
		is_published: question?.is_published !== 0,
		prompt: question?.prompt || '',
		accepted_answers: question?.accepted_answers || '',
		explanation: question?.explanation || '',
		options: (question?.options || []).map(option => buildEditableQuizOption(option)),
	};
}

function buildBlankQuizQuestion(questionType = 'Single Choice'): EditableQuizQuestion {
	const question = buildEditableQuizQuestion({
		title: '',
		question_type: questionType,
		is_published: 1,
		prompt: '',
		accepted_answers: '',
		explanation: '',
		options: [],
	});
	handleQuizQuestionTypeChange(question);
	return question;
}

function getSectionElement(sectionId: WorkspaceSectionId) {
	if (typeof document === 'undefined') return null;
	return document.getElementById(sectionId);
}

function focusWithinSection(sectionId: WorkspaceSectionId, selector: string) {
	window.setTimeout(() => {
		const target = getSectionElement(sectionId)?.querySelector<HTMLElement>(selector);
		target?.focus();
	}, 220);
}

async function setSectionHash(sectionId: WorkspaceSectionId) {
	const nextHash = `#${sectionId}`;
	if (route.hash === nextHash) return;
	await router.replace({
		name: 'staff-course-plan',
		params: { coursePlan: props.coursePlan },
		query: { ...route.query },
		hash: nextHash,
	});
}

async function replaceQuizQuestionBankRoute(quizQuestionBank?: string | null) {
	await router.replace({
		name: 'staff-course-plan',
		params: { coursePlan: props.coursePlan },
		query: {
			...route.query,
			quiz_question_bank: quizQuestionBank || undefined,
		},
		hash: route.hash,
	});
}

function syncActiveSectionFromViewport() {
	if (!navigationSections.value.length || typeof window === 'undefined') return;
	let currentSection = navigationSections.value[0]?.id || SECTION_IDS.overview;

	for (const section of navigationSections.value) {
		const element = getSectionElement(section.id);
		if (!element) continue;
		if (element.getBoundingClientRect().top <= 180) {
			currentSection = section.id;
			continue;
		}
		break;
	}

	activeSectionId.value = currentSection;
}

function requestActiveSectionSync() {
	if (typeof window === 'undefined') return;
	if (scrollFrame) {
		window.cancelAnimationFrame(scrollFrame);
	}
	scrollFrame = window.requestAnimationFrame(() => {
		scrollFrame = 0;
		syncActiveSectionFromViewport();
	});
}

function syncRouteHashSection(behavior: ScrollBehavior = 'auto') {
	const sectionId = String(route.hash || '').replace(/^#/, '') as WorkspaceSectionId;
	if (!sectionId) return;
	expandSectionChain(sectionId);
	setSectionExpanded(sectionId, true);
	const element = getSectionElement(sectionId);
	if (!element) return;
	activeSectionId.value = sectionId;
	element.scrollIntoView({ behavior, block: 'start' });
}

async function jumpToSection(sectionId: WorkspaceSectionId, focusSelector?: string) {
	expandSectionChain(sectionId);
	setSectionExpanded(sectionId, true);
	await setSectionHash(sectionId);
	await nextTick();
	const element = getSectionElement(sectionId);
	if (!element) return;
	activeSectionId.value = sectionId;
	element.scrollIntoView({ behavior: 'smooth', block: 'start' });
	if (focusSelector) {
		focusWithinSection(sectionId, focusSelector);
	}
}

function setResourceComposerMode(sectionId: WorkspaceSectionId, mode: 'link' | 'file') {
	getSectionElement(sectionId)
		?.querySelector<HTMLElement>(`[data-resource-mode="${mode}"]`)
		?.click();
}

function ensureSelectedUnitForQuickAction(message: string) {
	if (selectedUnit.value) return true;
	toast.error(message);
	void jumpToSection(SECTION_IDS.units);
	return false;
}

async function quickEditUnit() {
	if (
		!ensureSelectedUnitForQuickAction('Select a governed unit before editing shared unit content.')
	) {
		return;
	}
	setSectionExpanded(SECTION_IDS.unitEditor, true);
	await jumpToSection(SECTION_IDS.unitEditor, '[data-quick-focus="unit-title"]');
}

async function quickUploadUnitFile() {
	if (
		!ensureSelectedUnitForQuickAction(
			'Select a governed unit before adding shared unit resources.'
		)
	) {
		return;
	}
	setSectionExpanded(SECTION_IDS.unitResources, true);
	setResourceComposerMode(SECTION_IDS.unitResources, 'file');
	await jumpToSection(SECTION_IDS.unitResources, '[data-resource-choose-file="true"]');
}

async function quickAddReflection() {
	if (
		!ensureSelectedUnitForQuickAction('Select a governed unit before adding shared reflections.')
	) {
		return;
	}
	addReflection();
	setSectionExpanded(SECTION_IDS.reflections, true);
	await jumpToSection(SECTION_IDS.reflections);
}

async function quickStartQuizBank() {
	await startNewQuizQuestionBank();
	setSectionExpanded(SECTION_IDS.quizBanks, true);
	await jumpToSection(SECTION_IDS.quizBanks, '[data-quick-focus="quiz-bank-title"]');
}

function syncCoursePlanForm(payload: StaffCoursePlanSurfaceResponse | null) {
	coursePlanForm.record_modified = payload?.course_plan.record_modified || '';
	coursePlanForm.title = payload?.course_plan.title || '';
	coursePlanForm.academic_year = payload?.course_plan.academic_year || '';
	coursePlanForm.cycle_label = payload?.course_plan.cycle_label || '';
	coursePlanForm.plan_status = payload?.course_plan.plan_status || 'Draft';
	coursePlanForm.summary = payload?.course_plan.summary || '';
}

function syncUnitForm(unit: StaffCoursePlanUnit | null) {
	unitForm.unit_plan = unit?.unit_plan || '';
	unitForm.record_modified = unit?.record_modified || '';
	unitForm.title = unit?.title || '';
	unitForm.program = unit?.program || '';
	unitForm.unit_code = unit?.unit_code || '';
	unitForm.unit_order = unit?.unit_order ?? null;
	unitForm.unit_status = unit?.unit_status || 'Active';
	unitForm.version = unit?.version || '';
	unitForm.duration = unit?.duration || '';
	unitForm.estimated_duration = unit?.estimated_duration || '';
	unitForm.is_published = Boolean(unit?.is_published);
	unitForm.overview = unit?.overview || '';
	unitForm.essential_understanding = unit?.essential_understanding || '';
	unitForm.misconceptions = unit?.misconceptions || '';
	unitForm.content = unit?.content || '';
	unitForm.skills = unit?.skills || '';
	unitForm.concepts = unit?.concepts || '';
	unitForm.standards = (unit?.standards || []).map(standard => buildEditableStandard(standard));
	unitForm.reflections = (unit?.shared_reflections || []).map(reflection =>
		buildEditableReflection(reflection)
	);
}

function syncQuizBankForm(bank: StaffCoursePlanQuizQuestionBank | null) {
	quizBankForm.quiz_question_bank = bank?.quiz_question_bank || '';
	quizBankForm.record_modified = bank?.record_modified || '';
	quizBankForm.bank_title = bank?.bank_title || '';
	quizBankForm.description = bank?.description || '';
	quizBankForm.is_published = bank?.is_published !== 0;
	quizBankForm.questions = (bank?.questions || []).map(question =>
		buildEditableQuizQuestion(question)
	);
}

function applyQuizBankSelection(payload: StaffCoursePlanSurfaceResponse) {
	if (creatingQuizQuestionBank.value) return;
	const requestedBank = String(
		selectedQuizQuestionBankName.value || props.quizQuestionBank || ''
	).trim();
	const resolvedBank =
		payload.resolved.quiz_question_bank ||
		payload.assessment.quiz_question_banks[0]?.quiz_question_bank ||
		'';
	const nextBank = payload.assessment.quiz_question_banks.some(
		bank => bank.quiz_question_bank === requestedBank
	)
		? requestedBank
		: resolvedBank;
	selectedQuizQuestionBankName.value = nextBank;
	const detail = payload.assessment.selected_quiz_question_bank || null;
	syncQuizBankForm(detail && detail.quiz_question_bank === nextBank ? detail : null);
}

function applySurfaceSelection(payload: StaffCoursePlanSurfaceResponse) {
	syncCoursePlanForm(payload);

	if (!creatingUnit.value) {
		const requestedUnit = String(props.unitPlan || '').trim();
		const resolvedUnit =
			payload.resolved.unit_plan || payload.curriculum.units[0]?.unit_plan || '';
		const nextSelectedUnit = payload.curriculum.units.some(
			unit => unit.unit_plan === requestedUnit
		)
			? requestedUnit
			: resolvedUnit;
		selectedUnitPlan.value = nextSelectedUnit;
		syncUnitForm(
			payload.curriculum.units.find(unit => unit.unit_plan === nextSelectedUnit) || null
		);
	}

	applyQuizBankSelection(payload);
}

async function loadSurface() {
	const ticket = loadToken.value + 1;
	loadToken.value = ticket;
	loading.value = true;
	errorMessage.value = '';

	try {
		const payload = await getStaffCoursePlanSurface({
			course_plan: props.coursePlan,
			unit_plan: props.unitPlan || undefined,
			quiz_question_bank:
				props.quizQuestionBank || selectedQuizQuestionBankName.value || undefined,
			student_group: props.studentGroup || undefined,
		});
		if (ticket !== loadToken.value) return;
		surface.value = payload;
		applySurfaceSelection(payload);
		await nextTick();
		if (route.hash) {
			syncRouteHashSection('auto');
		} else {
			requestActiveSectionSync();
		}
	} catch (error) {
		if (ticket !== loadToken.value) return;
		surface.value = null;
		errorMessage.value = error instanceof Error ? error.message : 'Unknown error';
	} finally {
		if (ticket === loadToken.value) {
			loading.value = false;
		}
	}
}

async function selectUnit(unitPlan: string) {
	creatingUnit.value = false;
	selectedUnitPlan.value = unitPlan;
	syncUnitForm(surface.value?.curriculum.units.find(unit => unit.unit_plan === unitPlan) || null);
	setSectionExpanded(SECTION_IDS.unitEditor, true);
	await router.replace({
		name: 'staff-course-plan',
		params: { coursePlan: props.coursePlan },
		query: {
			...route.query,
			unit_plan: unitPlan || undefined,
		},
		hash: route.hash,
	});
}

async function startNewUnit() {
	creatingUnit.value = true;
	selectedUnitPlan.value = '';
	syncUnitForm(null);
	setSectionExpanded(SECTION_IDS.unitEditor, true);
	await router.replace({
		name: 'staff-course-plan',
		params: { coursePlan: props.coursePlan },
		query: {
			...route.query,
			unit_plan: undefined,
		},
		hash: route.hash,
	});
}

function cancelNewUnit() {
	creatingUnit.value = false;
	const fallbackUnit = surface.value?.curriculum.units[0]?.unit_plan || '';
	if (fallbackUnit) {
		void selectUnit(fallbackUnit);
		return;
	}
	syncUnitForm(null);
}

function applySelectedLearningStandards(rows: StaffLearningStandardPickerRow[]) {
	const existingStandards = new Set(
		unitForm.standards
			.map(standard => String(standard.learning_standard || '').trim())
			.filter(value => Boolean(value))
	);
	let added = 0;

	rows.forEach(standard => {
		const learningStandard = String(standard.learning_standard || '').trim();
		if (!learningStandard || existingStandards.has(learningStandard)) {
			return;
		}
		unitForm.standards.push(
			buildEditableStandard({
				learning_standard: learningStandard,
				framework_name: standard.framework_name || '',
				framework_version: standard.framework_version || '',
				subject_area: standard.subject_area || '',
				program: standard.program || unitForm.program || '',
				strand: standard.strand || '',
				substrand: standard.substrand || '',
				standard_code: standard.standard_code || '',
				standard_description: standard.standard_description || '',
				alignment_type: standard.alignment_type || '',
			})
		);
		existingStandards.add(learningStandard);
		added += 1;
	});

	if (added) {
		toast.success(`${added} learning standard${added === 1 ? '' : 's'} added.`);
		return;
	}
	toast.error('All selected standards are already on this unit.');
}

function openStandardsOverlay() {
	if (!canManagePlan.value) return;
	const preferredProgram =
		unitForm.program ||
		selectedUnit.value?.program ||
		(courseProgramOptions.value.length === 1 ? courseProgramOptions.value[0]?.value || '' : '');
	overlay.open('learning-standards-picker', {
		unitPlan: unitForm.unit_plan || selectedUnit.value?.unit_plan || null,
		unitTitle: unitForm.title || selectedUnit.value?.title || 'Selected Unit',
		unitProgram: preferredProgram || null,
		programLocked: Boolean(preferredProgram),
		existingStandards: unitForm.standards
			.map(standard => String(standard.learning_standard || '').trim())
			.filter(value => Boolean(value)),
		onApply: applySelectedLearningStandards,
	});
}

function removeStandard(localId: number) {
	unitForm.standards = unitForm.standards.filter(standard => standard.local_id !== localId);
}

function addReflection() {
	unitForm.reflections.push(buildEditableReflection());
}

function removeReflection(localId: number) {
	unitForm.reflections = unitForm.reflections.filter(
		reflection => reflection.local_id !== localId
	);
}

function serializeStandards(): StaffPlanningStandard[] {
	return unitForm.standards.map(({ local_id, ...row }) => row);
}

function serializeReflections(): StaffPlanningReflection[] {
	return unitForm.reflections.map(({ local_id, academic_year, school, ...row }) => ({
		...row,
		academic_year: derivedReflectionAcademicYear.value || academic_year || null,
		school: derivedReflectionSchool.value || school || null,
	}));
}

async function startNewQuizQuestionBank() {
	creatingQuizQuestionBank.value = true;
	selectedQuizQuestionBankName.value = '';
	syncQuizBankForm(null);
	await replaceQuizQuestionBankRoute(null);
}

function openAssignFromQuizBank(bank: StaffCoursePlanQuizQuestionBank) {
	if (!surface.value) return;
	if (!bank.is_published) {
		toast.error('Publish the quiz bank before assigning it.');
		return;
	}
	overlay.open('create-task', {
		prefillCourse: surface.value.course_plan.course,
		prefillUnitPlan: selectedUnit.value?.unit_plan || null,
		prefillQuizQuestionBank: bank.quiz_question_bank,
		prefillQuizQuestionBankLabel: bank.bank_title,
		prefillTitle: bank.bank_title,
		prefillTaskType: 'Quiz',
	});
}

async function selectQuizQuestionBank(questionBank: string) {
	creatingQuizQuestionBank.value = false;
	selectedQuizQuestionBankName.value = questionBank;
	await replaceQuizQuestionBankRoute(questionBank);
}

async function cancelNewQuizQuestionBank() {
	creatingQuizQuestionBank.value = false;
	const fallbackBank = surface.value?.assessment.quiz_question_banks[0]?.quiz_question_bank || '';
	selectedQuizQuestionBankName.value = fallbackBank;
	if (fallbackBank) {
		await replaceQuizQuestionBankRoute(fallbackBank);
		return;
	}
	syncQuizBankForm(null);
	await replaceQuizQuestionBankRoute(null);
}

function addQuizQuestion() {
	quizBankForm.questions.push(buildBlankQuizQuestion());
}

function removeQuizQuestion(localId: number) {
	quizBankForm.questions = quizBankForm.questions.filter(
		question => question.local_id !== localId
	);
}

function addQuizOption(question: EditableQuizQuestion) {
	question.options.push(buildEditableQuizOption());
}

function removeQuizOption(question: EditableQuizQuestion, localId: number) {
	question.options = question.options.filter(option => option.local_id !== localId);
}

function handleQuizQuestionTypeChange(question: EditableQuizQuestion) {
	if (question.question_type === 'True / False') {
		question.options = [
			buildEditableQuizOption({ option_text: 'True', is_correct: 1 }),
			buildEditableQuizOption({ option_text: 'False', is_correct: 0 }),
		];
		question.accepted_answers = '';
		return;
	}

	if (isChoiceQuestion(question.question_type)) {
		if (question.options.length < 2) {
			question.options = [buildEditableQuizOption(), buildEditableQuizOption()];
		}
		question.accepted_answers = '';
		return;
	}

	question.options = [];
	if (question.question_type !== 'Short Answer') {
		question.accepted_answers = '';
	}
}

function serializeQuizQuestions(): StaffCoursePlanQuizQuestion[] {
	return quizBankForm.questions.map(({ local_id, is_published, options, ...question }) => ({
		...question,
		is_published: is_published ? 1 : 0,
		options: options.map(({ local_id: optionLocalId, is_correct, ...option }) => ({
			...option,
			is_correct: is_correct ? 1 : 0,
		})),
	}));
}

async function handleSaveCoursePlan() {
	if (!surface.value?.course_plan.course_plan) return;
	coursePlanPending.value = true;
	try {
		await saveCoursePlan({
			course_plan: surface.value.course_plan.course_plan,
			expected_modified: coursePlanForm.record_modified || null,
			title: coursePlanForm.title.trim(),
			academic_year: coursePlanForm.academic_year || null,
			cycle_label: coursePlanForm.cycle_label.trim() || null,
			plan_status: coursePlanForm.plan_status,
			summary: coursePlanForm.summary || null,
		});
		await loadSurface();
		toast.success('Shared course plan updated.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save the shared course plan.');
	} finally {
		coursePlanPending.value = false;
	}
}

async function handleSaveUnitPlan() {
	unitPending.value = true;
	try {
		const wasCreating = creatingUnit.value;
		const result = await saveGovernedUnitPlan({
			course_plan: props.coursePlan,
			unit_plan: wasCreating ? undefined : unitForm.unit_plan || undefined,
			expected_modified: wasCreating ? null : unitForm.record_modified || null,
			title: unitForm.title.trim(),
			program: unitForm.program || null,
			unit_code: unitForm.unit_code.trim() || null,
			unit_order: unitForm.unit_order,
			unit_status: unitForm.unit_status,
			version: unitForm.version.trim() || null,
			duration: unitForm.duration.trim() || null,
			estimated_duration: unitForm.estimated_duration.trim() || null,
			is_published: unitForm.is_published ? 1 : 0,
			overview: unitForm.overview || null,
			essential_understanding: unitForm.essential_understanding || null,
			misconceptions: unitForm.misconceptions || null,
			content: unitForm.content || null,
			skills: unitForm.skills || null,
			concepts: unitForm.concepts || null,
			standards: serializeStandards(),
			reflections: serializeReflections(),
		});
		creatingUnit.value = false;
		await router.replace({
			name: 'staff-course-plan',
			params: { coursePlan: props.coursePlan },
			query: {
				...route.query,
				unit_plan: result.unit_plan,
			},
			hash: route.hash,
		});
		await loadSurface();
		toast.success(wasCreating ? 'Unit plan created.' : 'Unit plan updated.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save the unit plan.');
	} finally {
		unitPending.value = false;
	}
}

async function handleSaveQuizQuestionBank() {
	quizBankPending.value = true;
	try {
		const wasCreating = creatingQuizQuestionBank.value;
		const result = await saveQuizQuestionBank({
			course_plan: props.coursePlan,
			quiz_question_bank: wasCreating ? undefined : quizBankForm.quiz_question_bank || undefined,
			expected_modified: wasCreating ? null : quizBankForm.record_modified || null,
			bank_title: quizBankForm.bank_title.trim(),
			description: quizBankForm.description || null,
			is_published: quizBankForm.is_published ? 1 : 0,
			questions: serializeQuizQuestions(),
		});
		creatingQuizQuestionBank.value = false;
		selectedQuizQuestionBankName.value = result.quiz_question_bank;
		const routeWillChange =
			String(props.quizQuestionBank || '').trim() !== result.quiz_question_bank;
		await replaceQuizQuestionBankRoute(result.quiz_question_bank);
		if (!routeWillChange) {
			await loadSurface();
		}
		toast.success(wasCreating ? 'Quiz bank created.' : 'Quiz bank updated.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save the quiz bank.');
	} finally {
		quizBankPending.value = false;
	}
}

watch(
	() => [props.coursePlan, props.unitPlan, props.quizQuestionBank, props.studentGroup],
	() => {
		loadSurface();
	},
	{ immediate: true }
);

watch(
	() => props.coursePlan,
	() => {
		loadCollapsedSections();
	},
	{ immediate: true }
);

watch(
	() => route.hash,
	hash => {
		const sectionId = String(hash || '').replace(/^#/, '') as WorkspaceSectionId;
		if (!sectionId) return;
		expandSectionChain(sectionId);
		setSectionExpanded(sectionId, true);
		activeSectionId.value = sectionId;
	}
);

watch(navigationSections, () => {
	if (route.hash) return;
	void nextTick(() => {
		requestActiveSectionSync();
	});
});

onMounted(() => {
	window.addEventListener('scroll', requestActiveSectionSync, { passive: true });
	loadCollapsedSections();
	requestActiveSectionSync();
});

onBeforeUnmount(() => {
	window.removeEventListener('scroll', requestActiveSectionSync);
	if (scrollFrame) {
		window.cancelAnimationFrame(scrollFrame);
		scrollFrame = 0;
	}
});
</script>
