<template>
	<section
		v-if="show"
		:id="SECTION_IDS.unitEditor"
		class="scroll-mt-40 space-y-6 rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
	>
		<div class="course-plan-unit-editor-header">
			<div>
				<p class="type-overline text-ink/60">
					{{ creatingUnit ? 'New Unit Plan' : 'Selected Unit' }}
				</p>
				<h2 class="mt-2 type-h2 text-ink">
					{{ unitEditorHeading }}
				</h2>
			</div>
			<div class="course-plan-unit-editor-summary">
				<span v-if="!creatingUnit" class="course-plan-unit-summary-pill">
					<span class="course-plan-unit-summary-pill__label">Unit</span>
					<span class="course-plan-unit-summary-pill__value">
						{{ unitForm.unit_order || '—' }}
					</span>
				</span>
				<span v-if="unitForm.unit_status" class="course-plan-unit-summary-pill">
					<span class="course-plan-unit-summary-pill__label">Status</span>
					<span class="course-plan-unit-summary-pill__value">
						{{ unitForm.unit_status }}
					</span>
				</span>
				<span
					v-if="selectedUnitTimelineState?.start_date && selectedUnitTimelineState?.end_date"
					class="course-plan-unit-summary-pill"
				>
					<span class="course-plan-unit-summary-pill__label">Timeline</span>
					<span class="course-plan-unit-summary-pill__value">
						{{ selectedUnitTimelineState.start_date }} →
						{{ selectedUnitTimelineState.end_date }}
					</span>
				</span>
				<button
					type="button"
					class="course-plan-unit-summary-pill course-plan-unit-summary-pill--toggle"
					:aria-expanded="!isSectionCollapsed(SECTION_IDS.unitEditor)"
					@click="emit('toggle-section', SECTION_IDS.unitEditor)"
				>
					<span class="course-plan-unit-summary-pill__label">Section</span>
					<span class="course-plan-unit-summary-pill__value">
						{{ isSectionCollapsed(SECTION_IDS.unitEditor) ? 'Show' : 'Hide' }}
					</span>
					<span class="course-plan-unit-summary-pill__icon">
						{{ isSectionCollapsed(SECTION_IDS.unitEditor) ? '+' : '-' }}
					</span>
				</button>
				<span
					v-if="canManagePlan"
					class="course-plan-unit-summary-pill"
					:class="
						unitPending
							? 'border-jacaranda/35 bg-jacaranda/16 text-jacaranda'
							: unitFormDirty
								? 'border-flame/25 bg-flame/10 text-flame'
								: 'border-line-soft bg-white/95 text-ink/72'
					"
				>
					<span class="course-plan-unit-summary-pill__label">Save State</span>
					<span class="course-plan-unit-summary-pill__value">
						{{ unitSaveStatusLabel }}
					</span>
				</span>
				<span
					v-if="creatingUnit"
					class="course-plan-unit-summary-pill border-jacaranda/20 bg-white/92 text-ink/72"
				>
					<span class="course-plan-unit-summary-pill__label">Mode</span>
					<span class="course-plan-unit-summary-pill__value">New unit</span>
				</span>
				<button
					v-if="creatingUnit"
					type="button"
					class="if-action course-plan-unit-inline-action"
					@click="emit('cancel-new-unit')"
				>
					Cancel New Unit
				</button>
				<button
					v-if="canManagePlan"
					type="button"
					class="if-action course-plan-unit-save-button course-plan-unit-inline-action"
					data-testid="unit-save-header-button"
					:disabled="!canSaveUnitAction"
					@click="emit('save-unit')"
				>
					{{ unitSaveActionLabel }}
				</button>
			</div>
			<div v-if="!isSectionCollapsed(SECTION_IDS.unitEditor)" class="course-plan-unit-editor-nav">
				<button
					type="button"
					class="course-plan-unit-nav-pill"
					@click="emit('scroll-to-unit-panel', UNIT_PANEL_IDS.setup)"
				>
					Basics
				</button>
				<button
					type="button"
					class="course-plan-unit-nav-pill"
					@click="emit('scroll-to-unit-panel', UNIT_PANEL_IDS.narrative)"
				>
					Core Narrative
				</button>
				<button
					type="button"
					class="course-plan-unit-nav-pill"
					@click="emit('scroll-to-unit-panel', UNIT_PANEL_IDS.learningFocus)"
				>
					Learning Focus
				</button>
				<button
					type="button"
					class="course-plan-unit-nav-pill"
					@click="emit('jump-to-section', SECTION_IDS.standards)"
				>
					Standards
				</button>
				<button
					type="button"
					class="course-plan-unit-nav-pill"
					@click="emit('jump-to-section', SECTION_IDS.reflections)"
				>
					Reflections
				</button>
				<button
					type="button"
					class="course-plan-unit-nav-pill"
					@click="emit('jump-to-section', SECTION_IDS.unitResources)"
				>
					Resources
				</button>
			</div>
		</div>

		<template v-if="!isSectionCollapsed(SECTION_IDS.unitEditor)">
			<template v-if="canManagePlan">
				<div
					v-if="showUnitSaveRail"
					data-testid="unit-save-rail"
					class="course-plan-unit-save-rail sticky bottom-4 z-20"
				>
					<div class="course-plan-unit-save-rail__inner">
						<div class="min-w-0">
							<p class="type-caption text-ink/60">Selected Unit</p>
							<p class="mt-1 type-body-strong text-ink">{{ unitSaveStatusLabel }}</p>
							<p class="mt-1 type-caption text-ink/70">
								{{ unitSaveSupportText }}
							</p>
						</div>
						<div class="flex flex-wrap gap-2">
							<button
								v-if="creatingUnit"
								type="button"
								class="if-action"
								@click="emit('cancel-new-unit')"
							>
								Cancel New Unit
							</button>
							<button
								type="button"
								class="if-action course-plan-unit-save-button"
								:disabled="!canSaveUnitAction"
								@click="emit('save-unit')"
							>
								{{ unitSaveActionLabel }}
							</button>
						</div>
					</div>
				</div>

				<section :id="UNIT_PANEL_IDS.setup" class="course-plan-unit-panel scroll-mt-40 space-y-4">
					<div class="course-plan-unit-panel__header">
						<div class="space-y-3">
							<div>
								<p class="type-overline text-ink/60">Unit Setup</p>
								<h3 class="mt-1 type-h3 text-ink">Core metadata and publishing state</h3>
							</div>
							<p class="max-w-xl type-caption text-ink/65">
								Keep the shared unit identity, order, and readiness clear before staff work deeper
								into the narrative and standards layers.
							</p>
						</div>
						<button
							type="button"
							class="course-plan-unit-panel__toggle"
							data-testid="unit-panel-toggle-setup"
							:aria-controls="`${UNIT_PANEL_IDS.setup}-content`"
							:aria-expanded="!isUnitPanelCollapsed(UNIT_PANEL_IDS.setup)"
							@click="emit('toggle-unit-panel', UNIT_PANEL_IDS.setup)"
						>
							<span class="type-caption text-ink/70">
								{{ isUnitPanelCollapsed(UNIT_PANEL_IDS.setup) ? 'Show section' : 'Hide section' }}
							</span>
							<span class="course-plan-unit-panel__toggle-icon">
								{{ isUnitPanelCollapsed(UNIT_PANEL_IDS.setup) ? '+' : '-' }}
							</span>
						</button>
					</div>
					<div
						v-if="!isUnitPanelCollapsed(UNIT_PANEL_IDS.setup)"
						:id="`${UNIT_PANEL_IDS.setup}-content`"
						class="grid gap-4 lg:grid-cols-2"
					>
						<label class="course-plan-unit-subcard block space-y-2">
							<span class="type-caption text-ink/70">Unit Title</span>
							<input
								v-model="unitForm.title"
								data-quick-focus="unit-title"
								type="text"
								class="if-input w-full"
								placeholder="e.g. Cells and Systems"
							/>
						</label>
						<label class="course-plan-unit-subcard block space-y-2">
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
						<label class="course-plan-unit-subcard block space-y-2">
							<span class="type-caption text-ink/70">Unit Code</span>
							<input
								v-model="unitForm.unit_code"
								type="text"
								class="if-input w-full"
								placeholder="Optional unit code"
							/>
						</label>
						<label class="course-plan-unit-subcard block space-y-2">
							<span class="type-caption text-ink/70">Unit Order</span>
							<input
								v-model.number="unitForm.unit_order"
								type="number"
								min="1"
								step="1"
								class="if-input w-full"
							/>
						</label>
						<label class="course-plan-unit-subcard block space-y-2">
							<span class="type-caption text-ink/70">Unit Status</span>
							<select v-model="unitForm.unit_status" class="if-input w-full">
								<option v-for="option in unitStatusOptions" :key="option" :value="option">
									{{ option }}
								</option>
							</select>
						</label>
						<label class="course-plan-unit-subcard block space-y-2">
							<span class="type-caption text-ink/70">Version</span>
							<input
								v-model="unitForm.version"
								type="text"
								class="if-input w-full"
								placeholder="Optional version"
							/>
						</label>
						<label class="course-plan-unit-subcard block space-y-2">
							<span class="type-caption text-ink/70">Duration</span>
							<input
								v-model="unitForm.duration"
								type="text"
								class="if-input w-full"
								placeholder="e.g. 6 weeks"
							/>
						</label>
						<label class="course-plan-unit-subcard block space-y-2">
							<span class="type-caption text-ink/70">Estimated Duration</span>
							<input
								v-model="unitForm.estimated_duration"
								type="text"
								class="if-input w-full"
								placeholder="e.g. 24 GLH"
							/>
						</label>
						<label
							class="course-plan-unit-subcard flex items-center gap-3 px-4 py-4 lg:col-span-2"
						>
							<input v-model="unitForm.is_published" type="checkbox" class="h-4 w-4" />
							<div>
								<p class="type-body-strong text-ink">Published for class inheritance</p>
								<p class="type-caption text-ink/70">
									Use this when the governed unit is ready for linked classes to inherit.
								</p>
							</div>
						</label>
					</div>
				</section>

				<section
					:id="UNIT_PANEL_IDS.narrative"
					class="course-plan-unit-panel scroll-mt-40 space-y-4"
				>
					<div class="course-plan-unit-panel__header">
						<div class="space-y-3">
							<div>
								<p class="type-overline text-ink/60">Core Narrative</p>
								<h3 class="mt-1 type-h3 text-ink">Purpose, understanding, and watch-fors</h3>
							</div>
							<p class="max-w-xl type-caption text-ink/65">
								Keep the unit rationale, enduring understanding, and common watch-fors on separate
								rows so longer rich text stays readable.
							</p>
						</div>
						<button
							type="button"
							class="course-plan-unit-panel__toggle"
							data-testid="unit-panel-toggle-narrative"
							:aria-controls="`${UNIT_PANEL_IDS.narrative}-content`"
							:aria-expanded="!isUnitPanelCollapsed(UNIT_PANEL_IDS.narrative)"
							@click="emit('toggle-unit-panel', UNIT_PANEL_IDS.narrative)"
						>
							<span class="type-caption text-ink/70">
								{{
									isUnitPanelCollapsed(UNIT_PANEL_IDS.narrative) ? 'Show section' : 'Hide section'
								}}
							</span>
							<span class="course-plan-unit-panel__toggle-icon">
								{{ isUnitPanelCollapsed(UNIT_PANEL_IDS.narrative) ? '+' : '-' }}
							</span>
						</button>
					</div>
					<div
						v-if="!isUnitPanelCollapsed(UNIT_PANEL_IDS.narrative)"
						:id="`${UNIT_PANEL_IDS.narrative}-content`"
						class="space-y-4"
					>
						<label class="course-plan-unit-subcard block space-y-2">
							<span class="type-caption text-ink/70">Overview & Rationale</span>
							<PlanningRichTextField
								v-model="unitForm.overview"
								placeholder="State the unit arc, rationale, and what makes this backbone important."
								min-height-class="min-h-[8rem]"
							/>
						</label>
						<label class="course-plan-unit-subcard block space-y-2">
							<span class="type-caption text-ink/70">Essential Understanding</span>
							<PlanningRichTextField
								v-model="unitForm.essential_understanding"
								placeholder="Capture the shared understanding every class should build."
								min-height-class="min-h-[8rem]"
							/>
						</label>
						<label class="course-plan-unit-subcard block space-y-2">
							<span class="type-caption text-ink/70">Likely Misconceptions</span>
							<PlanningRichTextField
								v-model="unitForm.misconceptions"
								placeholder="List likely misunderstandings students may bring into the unit."
								min-height-class="min-h-[8rem]"
							/>
						</label>
					</div>
				</section>

				<section
					:id="UNIT_PANEL_IDS.learningFocus"
					class="course-plan-unit-panel scroll-mt-40 space-y-4"
				>
					<div class="course-plan-unit-panel__header">
						<div class="space-y-3">
							<div>
								<p class="type-overline text-ink/60">Learning Focus</p>
								<h3 class="mt-1 type-h3 text-ink">Content, skills, and concepts in one view</h3>
							</div>
							<p class="max-w-xl type-caption text-ink/65">
								Give each learning pillar its own row so longer entries can breathe without
								blurring together.
							</p>
						</div>
						<button
							type="button"
							class="course-plan-unit-panel__toggle"
							data-testid="unit-panel-toggle-learning-focus"
							:aria-controls="`${UNIT_PANEL_IDS.learningFocus}-content`"
							:aria-expanded="!isUnitPanelCollapsed(UNIT_PANEL_IDS.learningFocus)"
							@click="emit('toggle-unit-panel', UNIT_PANEL_IDS.learningFocus)"
						>
							<span class="type-caption text-ink/70">
								{{
									isUnitPanelCollapsed(UNIT_PANEL_IDS.learningFocus)
										? 'Show section'
										: 'Hide section'
								}}
							</span>
							<span class="course-plan-unit-panel__toggle-icon">
								{{ isUnitPanelCollapsed(UNIT_PANEL_IDS.learningFocus) ? '+' : '-' }}
							</span>
						</button>
					</div>
					<div
						v-if="!isUnitPanelCollapsed(UNIT_PANEL_IDS.learningFocus)"
						:id="`${UNIT_PANEL_IDS.learningFocus}-content`"
						class="space-y-4"
					>
						<label class="course-plan-unit-subcard block space-y-2">
							<span class="type-caption text-ink/70">Content</span>
							<PlanningRichTextField
								v-model="unitForm.content"
								placeholder="What should students know?"
								min-height-class="min-h-[8rem]"
							/>
						</label>
						<label class="course-plan-unit-subcard block space-y-2">
							<span class="type-caption text-ink/70">Skills</span>
							<PlanningRichTextField
								v-model="unitForm.skills"
								placeholder="What should students be able to do?"
								min-height-class="min-h-[8rem]"
							/>
						</label>
						<label class="course-plan-unit-subcard block space-y-2">
							<span class="type-caption text-ink/70">Concepts</span>
							<PlanningRichTextField
								v-model="unitForm.concepts"
								placeholder="Which big ideas or concepts should anchor the unit?"
								min-height-class="min-h-[8rem]"
							/>
						</label>
					</div>
				</section>
			</template>

			<template v-else>
				<section class="course-plan-unit-panel space-y-4">
					<div class="course-plan-unit-panel__header">
						<div class="space-y-3">
							<div>
								<p class="type-overline text-ink/60">Core Narrative</p>
								<h3 class="mt-1 type-h3 text-ink">Shared unit backbone</h3>
							</div>
							<p class="max-w-xl type-caption text-ink/65">
								The selected unit keeps overview, understanding, and watch-fors on separate rows so
								the narrative stays readable before the learning-focus fields below.
							</p>
						</div>
						<button
							type="button"
							class="course-plan-unit-panel__toggle"
							data-testid="unit-panel-toggle-narrative"
							:aria-controls="`${UNIT_PANEL_IDS.narrative}-content`"
							:aria-expanded="!isUnitPanelCollapsed(UNIT_PANEL_IDS.narrative)"
							@click="emit('toggle-unit-panel', UNIT_PANEL_IDS.narrative)"
						>
							<span class="type-caption text-ink/70">
								{{
									isUnitPanelCollapsed(UNIT_PANEL_IDS.narrative) ? 'Show section' : 'Hide section'
								}}
							</span>
							<span class="course-plan-unit-panel__toggle-icon">
								{{ isUnitPanelCollapsed(UNIT_PANEL_IDS.narrative) ? '+' : '-' }}
							</span>
						</button>
					</div>
					<div
						v-if="!isUnitPanelCollapsed(UNIT_PANEL_IDS.narrative)"
						:id="`${UNIT_PANEL_IDS.narrative}-content`"
						class="space-y-4"
					>
						<div
							v-if="hasRichTextContent(selectedUnit?.overview)"
							class="course-plan-unit-subcard space-y-2"
						>
							<p class="type-overline text-ink/60">Overview</p>
							<PlanningRichTextField
								:model-value="selectedUnit?.overview"
								:editable="false"
								display-class="text-ink/80"
							/>
						</div>
						<div
							v-if="hasRichTextContent(selectedUnit?.essential_understanding)"
							class="course-plan-unit-subcard space-y-2"
						>
							<p class="type-overline text-ink/60">Essential Understanding</p>
							<PlanningRichTextField
								:model-value="selectedUnit?.essential_understanding"
								:editable="false"
								display-class="text-ink/80"
							/>
						</div>
						<div
							v-if="hasRichTextContent(selectedUnit?.misconceptions)"
							class="course-plan-unit-subcard space-y-2"
						>
							<p class="type-overline text-ink/60">Likely Misconceptions</p>
							<PlanningRichTextField
								:model-value="selectedUnit?.misconceptions"
								:editable="false"
								display-class="text-ink/80"
							/>
						</div>
					</div>
				</section>

				<section class="course-plan-unit-panel space-y-4">
					<div class="course-plan-unit-panel__header">
						<div class="space-y-3">
							<div>
								<p class="type-overline text-ink/60">Learning Focus</p>
								<h3 class="mt-1 type-h3 text-ink">Content, skills, and concepts</h3>
							</div>
							<p class="max-w-xl type-caption text-ink/65">
								The selected unit keeps the three learning anchors on separate rows so long entries
								remain easy to scan.
							</p>
						</div>
						<button
							type="button"
							class="course-plan-unit-panel__toggle"
							data-testid="unit-panel-toggle-learning-focus"
							:aria-controls="`${UNIT_PANEL_IDS.learningFocus}-content`"
							:aria-expanded="!isUnitPanelCollapsed(UNIT_PANEL_IDS.learningFocus)"
							@click="emit('toggle-unit-panel', UNIT_PANEL_IDS.learningFocus)"
						>
							<span class="type-caption text-ink/70">
								{{
									isUnitPanelCollapsed(UNIT_PANEL_IDS.learningFocus)
										? 'Show section'
										: 'Hide section'
								}}
							</span>
							<span class="course-plan-unit-panel__toggle-icon">
								{{ isUnitPanelCollapsed(UNIT_PANEL_IDS.learningFocus) ? '+' : '-' }}
							</span>
						</button>
					</div>
					<div
						v-if="!isUnitPanelCollapsed(UNIT_PANEL_IDS.learningFocus)"
						:id="`${UNIT_PANEL_IDS.learningFocus}-content`"
						class="space-y-4"
					>
						<div
							v-if="hasRichTextContent(selectedUnit?.content)"
							class="course-plan-unit-subcard space-y-2"
						>
							<p class="type-overline text-ink/60">Content</p>
							<PlanningRichTextField
								:model-value="selectedUnit?.content"
								:editable="false"
								display-class="text-ink/80"
							/>
						</div>
						<div
							v-if="hasRichTextContent(selectedUnit?.skills)"
							class="course-plan-unit-subcard space-y-2"
						>
							<p class="type-overline text-ink/60">Skills</p>
							<PlanningRichTextField
								:model-value="selectedUnit?.skills"
								:editable="false"
								display-class="text-ink/80"
							/>
						</div>
						<div
							v-if="hasRichTextContent(selectedUnit?.concepts)"
							class="course-plan-unit-subcard space-y-2"
						>
							<p class="type-overline text-ink/60">Concepts</p>
							<PlanningRichTextField
								:model-value="selectedUnit?.concepts"
								:editable="false"
								display-class="text-ink/80"
							/>
						</div>
					</div>
				</section>
			</template>

			<section :id="SECTION_IDS.standards" class="course-plan-unit-panel scroll-mt-40 space-y-3">
				<div class="course-plan-unit-panel__header">
					<div class="space-y-3">
						<div>
							<p class="type-overline text-ink/60">Standards Alignment</p>
							<h3 class="mt-1 type-h3 text-ink">Shared alignment rows</h3>
						</div>
						<p class="max-w-xl type-caption text-ink/65">
							Keep the approved shared standards available without forcing the full row list open
							all the time.
						</p>
					</div>
					<div class="flex flex-wrap items-center gap-2">
						<span class="chip">{{ unitForm.standards.length }}</span>
						<button
							v-if="canManagePlan"
							type="button"
							class="if-action"
							@click="emit('open-standards-overlay')"
						>
							Select Standards
						</button>
						<button
							type="button"
							class="course-plan-unit-panel__toggle"
							data-testid="unit-panel-toggle-standards"
							:aria-controls="`${SECTION_IDS.standards}-content`"
							:aria-expanded="!isSectionCollapsed(SECTION_IDS.standards)"
							@click="emit('toggle-section', SECTION_IDS.standards)"
						>
							<span class="type-caption text-ink/70">
								{{ isSectionCollapsed(SECTION_IDS.standards) ? 'Show section' : 'Hide section' }}
							</span>
							<span class="course-plan-unit-panel__toggle-icon">
								{{ isSectionCollapsed(SECTION_IDS.standards) ? '+' : '-' }}
							</span>
						</button>
					</div>
				</div>

				<div
					v-if="!isSectionCollapsed(SECTION_IDS.standards)"
					:id="`${SECTION_IDS.standards}-content`"
					class="space-y-3"
				>
					<div
						v-if="!unitForm.standards.length"
						class="rounded-2xl border border-dashed border-line-soft p-4"
					>
						<p class="type-caption text-ink/70">
							No standards have been captured for this unit yet.
						</p>
					</div>

					<div v-else class="space-y-3">
						<article
							v-for="standard in unitForm.standards"
							:key="standard.local_id"
							class="overflow-hidden rounded-[1.5rem] border transition"
							:class="
								isStandardExpanded(standard.local_id)
									? 'border-jacaranda/35 bg-white shadow-soft'
									: 'border-line-soft bg-surface-soft hover:border-jacaranda/35 hover:bg-white/95'
							"
						>
							<button
								type="button"
								class="group flex w-full items-start justify-between gap-4 px-4 py-4 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-jacaranda/30 sm:px-5"
								:aria-controls="`course-plan-standard-${standard.local_id}`"
								:aria-expanded="isStandardExpanded(standard.local_id)"
								@click="emit('toggle-standard', standard.local_id)"
							>
								<div class="min-w-0 flex-1">
									<div class="flex min-w-0 items-center gap-3">
										<span
											class="inline-flex shrink-0 items-center rounded-full border border-jacaranda/20 bg-jacaranda/10 px-3 py-1 text-xs font-semibold tracking-[0.08em] text-jacaranda"
										>
											{{ trimmedValue(standard.standard_code) || 'Code pending' }}
										</span>
										<div
											class="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto whitespace-nowrap no-scrollbar"
										>
											<span
												v-for="token in standardSummaryTokens(standard)"
												:key="token.key"
												class="chip shrink-0"
												:class="token.pending ? 'border-dashed text-ink/55' : ''"
											>
												{{ token.label }}
											</span>
										</div>
									</div>
									<p class="mt-3 type-body text-ink/85">
										{{ standardSummaryDescription(standard) }}
									</p>
								</div>
								<div class="flex shrink-0 items-center gap-2 pl-1">
									<span class="chip">{{
										isStandardExpanded(standard.local_id) ? 'Hide details' : 'Details'
									}}</span>
									<span
										class="inline-flex h-9 w-9 items-center justify-center rounded-full border border-line-soft bg-white text-base font-semibold text-ink/60 transition group-hover:border-jacaranda/35 group-hover:text-jacaranda"
									>
										{{ isStandardExpanded(standard.local_id) ? '-' : '+' }}
									</span>
								</div>
							</button>

							<div
								v-if="isStandardExpanded(standard.local_id)"
								:id="`course-plan-standard-${standard.local_id}`"
								class="border-t border-line-soft px-4 pb-4 pt-4 sm:px-5 sm:pb-5"
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
											<option v-for="option in coverageLevelOptions" :key="option" :value="option">
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
										class="if-action"
										@click="emit('remove-standard', standard.local_id)"
									>
										Remove Standard
									</button>
								</div>
							</div>
						</article>
					</div>
				</div>
			</section>

			<section :id="SECTION_IDS.reflections" class="course-plan-unit-panel scroll-mt-40 space-y-3">
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
							class="if-action"
							@click="emit('add-reflection')"
						>
							Add Reflection
						</button>
					</div>
				</div>

				<div
					v-if="!unitForm.reflections.length"
					class="rounded-2xl border border-dashed border-line-soft p-4"
				>
					<p class="type-caption text-ink/70">No shared reflections captured yet for this unit.</p>
				</div>

				<div v-else class="space-y-4">
					<article
						v-for="reflection in unitForm.reflections"
						:key="reflection.local_id"
						class="course-plan-unit-subcard"
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
								class="if-action"
								@click="emit('remove-reflection', reflection.local_id)"
							>
								Remove Reflection
							</button>
						</div>
					</article>
				</div>
			</section>

			<section
				v-if="selectedUnit?.class_reflections?.length"
				class="course-plan-unit-panel space-y-3"
			>
				<div class="flex items-center justify-between gap-3">
					<h3 class="type-h3 text-ink">Class Reflections Across This Unit</h3>
					<span class="chip">{{ selectedUnit.class_reflections.length }}</span>
				</div>
				<div class="grid gap-3 xl:grid-cols-2">
					<article
						v-for="reflection in selectedUnit.class_reflections"
						:key="`${selectedUnit.unit_plan}-${reflection.class_teaching_plan}`"
						class="course-plan-unit-subcard"
					>
						<div class="flex items-center justify-between gap-3">
							<p class="type-body-strong text-ink">{{ reflection.class_label }}</p>
							<span v-if="reflection.academic_year" class="chip">
								{{ reflection.academic_year }}
							</span>
						</div>
						<div v-if="hasRichTextContent(reflection.prior_to_the_unit)" class="mt-3 space-y-2">
							<p class="type-overline text-ink/60">Prior To The Unit</p>
							<PlanningRichTextField
								:model-value="reflection.prior_to_the_unit"
								:editable="false"
								display-class="text-ink/80"
							/>
						</div>
						<div v-if="hasRichTextContent(reflection.during_the_unit)" class="mt-3 space-y-2">
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
						<div v-if="hasRichTextContent(reflection.what_didnt_work_well)" class="mt-3 space-y-2">
							<p class="type-overline text-ink/60">Watch For</p>
							<PlanningRichTextField
								:model-value="reflection.what_didnt_work_well"
								:editable="false"
								display-class="text-ink/70"
							/>
						</div>
						<div v-if="hasRichTextContent(reflection.changes_suggestions)" class="mt-3 space-y-2">
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

			<section
				v-if="canManagePlan"
				class="course-plan-unit-panel course-plan-unit-panel--footer flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
			>
				<div>
					<p class="type-overline text-ink/60">Final Checkpoint</p>
					<p class="mt-1 type-caption text-ink/70">
						Save from here or from the sticky rail while you scroll through the unit.
					</p>
				</div>
				<div class="flex flex-wrap gap-2">
					<button
						v-if="creatingUnit"
						type="button"
						class="if-action"
						@click="emit('cancel-new-unit')"
					>
						Cancel New Unit
					</button>
					<button
						type="button"
						class="if-action course-plan-unit-save-button"
						:disabled="!canSaveUnitAction"
						@click="emit('save-unit')"
					>
						{{ unitSaveActionLabel }}
					</button>
				</div>
			</section>

			<section
				:id="SECTION_IDS.unitResources"
				class="course-plan-unit-panel scroll-mt-40 space-y-4"
			>
				<div class="course-plan-unit-panel__header">
					<div>
						<p class="type-overline text-ink/60">Unit Resources</p>
						<h3 class="mt-1 type-h3 text-ink">Shared resources for this unit</h3>
					</div>
					<p class="max-w-xl type-caption text-ink/65">
						Use this layer for governed materials every class should inherit while teaching the
						unit.
					</p>
				</div>
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
					enable-attachment-preview
					hide-header
					embedded
					@changed="emit('resource-changed')"
				/>
			</section>
		</template>
	</section>

	<section v-else class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
		<p class="type-body text-ink/70">
			Select a governed unit to edit the shared backbone, or create a new unit plan.
		</p>
	</section>
</template>

<script setup lang="ts">
import PlanningResourcePanel from '@/components/planning/PlanningResourcePanel.vue';
import PlanningRichTextField from '@/components/planning/PlanningRichTextField.vue';
import {
	SECTION_IDS,
	UNIT_PANEL_IDS,
	alignmentStrengthOptions,
	coverageLevelOptions,
	hasRichTextContent,
	standardSummaryDescription,
	standardSummaryTokens,
	trimmedValue,
	type UnitFormState,
	type UnitPanelId,
	type WorkspaceSectionId,
} from '@/lib/planning/coursePlanWorkspace';
import type {
	StaffCoursePlanTimelineUnit,
	StaffCoursePlanUnit,
} from '@/types/contracts/staff_teaching/get_staff_course_plan_surface';

const props = defineProps<{
	show: boolean;
	canManagePlan: boolean;
	creatingUnit: boolean;
	unitPending: boolean;
	unitFormDirty: boolean;
	unitForm: UnitFormState;
	selectedUnit: StaffCoursePlanUnit | null;
	selectedUnitTimelineState: StaffCoursePlanTimelineUnit | null;
	courseProgramOptions: Array<{ label: string; value: string }>;
	unitStatusOptions: readonly string[];
	derivedReflectionAcademicYear: string;
	derivedReflectionSchool: string;
	showUnitSaveRail: boolean;
	unitEditorHeading: string;
	unitSaveStatusLabel: string;
	unitSaveSupportText: string;
	unitSaveActionLabel: string;
	canSaveUnitAction: boolean;
	collapsedSections: Record<WorkspaceSectionId, boolean>;
	collapsedUnitPanels: Record<UnitPanelId, boolean>;
	isStandardExpanded: (localId: number) => boolean;
}>();

const emit = defineEmits<{
	(e: 'toggle-section', sectionId: WorkspaceSectionId): void;
	(e: 'jump-to-section', sectionId: WorkspaceSectionId): void;
	(e: 'toggle-unit-panel', panelId: UnitPanelId): void;
	(e: 'scroll-to-unit-panel', panelId: UnitPanelId): void;
	(e: 'open-standards-overlay'): void;
	(e: 'toggle-standard', localId: number): void;
	(e: 'remove-standard', localId: number): void;
	(e: 'add-reflection'): void;
	(e: 'remove-reflection', localId: number): void;
	(e: 'save-unit'): void;
	(e: 'cancel-new-unit'): void;
	(e: 'resource-changed'): void;
}>();

function isSectionCollapsed(sectionId: WorkspaceSectionId) {
	return Boolean(props.collapsedSections[sectionId]);
}

function isUnitPanelCollapsed(panelId: UnitPanelId) {
	return Boolean(props.collapsedUnitPanels[panelId]);
}
</script>
