<template>
	<div class="staff-shell space-y-6 course-plan-workspace">
		<CoursePlanWorkspaceHeader
			:course-plan="props.coursePlan"
			:surface="surface"
			:can-manage-plan="canManagePlan"
			:navigation-sections="navigationSections"
			:active-section-id="activeSectionId"
			:selected-unit="selectedUnit"
			@jump-to-section="jumpToSection"
			@quick-edit-unit="quickEditUnit"
			@quick-upload-unit-file="quickUploadUnitFile"
			@quick-add-reflection="quickAddReflection"
			@quick-start-quiz-bank="quickStartQuizBank"
		/>

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
			<CoursePlanOverviewSection
				:course-plan-surface="surface.course_plan"
				:course-plan-form="coursePlanForm"
				:academic-year-options="coursePlanAcademicYearOptions"
				:can-manage-plan="canManagePlan"
				:collapsed="isSectionCollapsed(SECTION_IDS.overview)"
				:pending="coursePlanPending"
				@toggle="toggleSection(SECTION_IDS.overview)"
				@save="handleSaveCoursePlan"
			/>

			<CoursePlanTimelineSection
				:timeline="surface.curriculum.timeline"
				:timeline-scope-label="timelineScopeLabel"
				:timeline-date-label="timelineDateLabel"
				:collapsed="isSectionCollapsed(SECTION_IDS.timeline)"
				@toggle="toggleSection(SECTION_IDS.timeline)"
			/>

			<section class="grid gap-6 xl:grid-cols-[minmax(0,20rem),minmax(0,1fr)]">
				<CoursePlanUnitSidebar
					:course-plan-name="surface.course_plan.course_plan"
					:course-plan-resources="surface.resources.course_plan_resources"
					:can-manage-plan="canManagePlan"
					:course-plan-resource-count="coursePlanResourceCount"
					:course-resources-collapsed="isSectionCollapsed(SECTION_IDS.courseResources)"
					:units="surface.curriculum.units"
					:unit-count="surface.curriculum.unit_count"
					:selected-unit-plan="selectedUnitPlan"
					:creating-unit="creatingUnit"
					@toggle-course-resources="toggleSection(SECTION_IDS.courseResources)"
					@resource-changed="loadSurface"
					@select-unit="selectUnit"
					@start-new-unit="startNewUnit"
				/>

				<CoursePlanUnitEditor
					:show="showUnitEditor"
					:can-manage-plan="canManagePlan"
					:creating-unit="creatingUnit"
					:unit-pending="unitPending"
					:unit-form-dirty="unitFormDirty"
					:unit-form="unitForm"
					:selected-unit="selectedUnit"
					:selected-unit-timeline-state="selectedUnitTimelineState"
					:course-program-options="courseProgramOptions"
					:unit-status-options="unitStatusOptions"
					:derived-reflection-academic-year="derivedReflectionAcademicYear"
					:derived-reflection-school="derivedReflectionSchool"
					:show-unit-save-rail="showUnitSaveRail"
					:unit-editor-heading="unitEditorHeading"
					:unit-save-status-label="unitSaveStatusLabel"
					:unit-save-support-text="unitSaveSupportText"
					:unit-save-action-label="unitSaveActionLabel"
					:can-save-unit-action="canSaveUnitAction"
					:collapsed-sections="collapsedSections"
					:collapsed-unit-panels="collapsedUnitPanels"
					:is-standard-expanded="isStandardExpanded"
					@toggle-section="toggleSection"
					@jump-to-section="jumpToSection"
					@toggle-unit-panel="toggleUnitPanel"
					@scroll-to-unit-panel="scrollToUnitPanel"
					@open-standards-overlay="openStandardsOverlay"
					@toggle-standard="toggleStandardExpansion"
					@remove-standard="removeStandard"
					@add-reflection="addReflection"
					@remove-reflection="removeReflection"
					@save-unit="handleSaveUnitPlan"
					@cancel-new-unit="cancelNewUnit"
					@resource-changed="loadSurface"
				/>
			</section>

			<CoursePlanQuizBanksSection
				:collapsed="isSectionCollapsed(SECTION_IDS.quizBanks)"
				:can-manage-plan="canManagePlan"
				:creating-quiz-question-bank="creatingQuizQuestionBank"
				:show-quiz-bank-editor="showQuizBankEditor"
				:quiz-question-banks="surface.assessment.quiz_question_banks"
				:selected-quiz-question-bank="selectedQuizQuestionBank"
				:selected-quiz-bank-label="selectedQuizBankLabel"
				:quiz-bank-form="quizBankForm"
				:quiz-bank-pending="quizBankPending"
				@toggle="toggleSection(SECTION_IDS.quizBanks)"
				@select-bank="selectQuizQuestionBank"
				@start-new-bank="startNewQuizQuestionBank"
				@assign-quiz="openAssignFromQuizBank"
				@add-question="addQuizQuestion"
				@remove-question="removeQuizQuestion"
				@add-option="addQuizOption"
				@remove-option="removeQuizOption"
				@question-type-change="handleQuizQuestionTypeChange"
				@cancel-new-bank="cancelNewQuizQuestionBank"
				@save-bank="handleSaveQuizQuestionBank"
			/>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { toast } from 'frappe-ui';
import { useRoute, useRouter } from 'vue-router';

import CoursePlanOverviewSection from '@/components/planning/course-plan-workspace/CoursePlanOverviewSection.vue';
import CoursePlanQuizBanksSection from '@/components/planning/course-plan-workspace/CoursePlanQuizBanksSection.vue';
import CoursePlanTimelineSection from '@/components/planning/course-plan-workspace/CoursePlanTimelineSection.vue';
import CoursePlanUnitEditor from '@/components/planning/course-plan-workspace/CoursePlanUnitEditor.vue';
import CoursePlanUnitSidebar from '@/components/planning/course-plan-workspace/CoursePlanUnitSidebar.vue';
import CoursePlanWorkspaceHeader from '@/components/planning/course-plan-workspace/CoursePlanWorkspaceHeader.vue';
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
	StaffCoursePlanQuizQuestionBank,
	StaffCoursePlanTimelineUnit,
	StaffCoursePlanUnit,
} from '@/types/contracts/staff_teaching/get_staff_course_plan_surface';
import {
	SECTION_IDS,
	UNIT_PANEL_IDS,
	buildBlankQuizQuestion,
	buildEditableQuizOption,
	buildEditableQuizQuestion,
	buildEditableReflection,
	buildEditableStandard,
	buildUnitDraftSignature,
	handleQuizQuestionTypeChange as syncQuizQuestionType,
	parseIsoDate,
	serializeQuizQuestions,
	serializeReflections,
	serializeStandards,
	unitStatusOptions,
	type CoursePlanFormState,
	type EditableQuizQuestion,
	type QuizBankFormState,
	type UnitFormState,
	type UnitPanelId,
	type WorkspaceNavigationSection,
	type WorkspaceSectionId,
} from '@/lib/planning/coursePlanWorkspace';

const props = defineProps<{
	coursePlan: string;
	unitPlan?: string;
	quizQuestionBank?: string;
	studentGroup?: string;
}>();

const route = useRoute();
const router = useRouter();
const overlay = useOverlayStack();

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

const collapsedUnitPanelDefaults: Record<UnitPanelId, boolean> = {
	[UNIT_PANEL_IDS.setup]: false,
	[UNIT_PANEL_IDS.narrative]: true,
	[UNIT_PANEL_IDS.learningFocus]: true,
};

const surface = ref<StaffCoursePlanSurfaceResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');
const coursePlanPending = ref(false);
const unitPending = ref(false);
const quizBankPending = ref(false);
const unitDraftSnapshot = ref('');
const selectedUnitPlan = ref('');
const selectedQuizQuestionBankName = ref(String(props.quizQuestionBank || '').trim());
const creatingUnit = ref(false);
const creatingQuizQuestionBank = ref(false);
const loadToken = ref(0);
const nextLocalId = ref(1);
const activeSectionId = ref<WorkspaceSectionId>(SECTION_IDS.overview);
const expandedStandardIds = ref<number[]>([]);
let scrollFrame = 0;

const coursePlanForm = reactive<CoursePlanFormState>({
	record_modified: '',
	title: '',
	academic_year: '',
	cycle_label: '',
	plan_status: 'Draft',
	summary: '',
});

const unitForm = reactive<UnitFormState>({
	unit_plan: '',
	record_modified: '',
	title: '',
	program: '',
	unit_code: '',
	unit_order: null,
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
	standards: [],
	reflections: [],
});

const quizBankForm = reactive<QuizBankFormState>({
	quiz_question_bank: '',
	record_modified: '',
	bank_title: '',
	description: '',
	is_published: true,
	questions: [],
});

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
const collapsedUnitPanels = reactive<Record<UnitPanelId, boolean>>({
	...collapsedUnitPanelDefaults,
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
const unitFormSignature = computed(() =>
	buildUnitDraftSignature(
		unitForm,
		serializeStandards(unitForm.standards),
		serializeReflections(
			unitForm.reflections,
			derivedReflectionAcademicYear.value,
			derivedReflectionSchool.value
		)
	)
);
const unitFormDirty = computed(() => unitFormSignature.value !== unitDraftSnapshot.value);
const canSaveUnitAction = computed(() =>
	Boolean(canManagePlan.value && !unitPending.value && (creatingUnit.value || unitFormDirty.value))
);
const showUnitSaveRail = computed(() =>
	Boolean(
		canManagePlan.value &&
		showUnitEditor.value &&
		!isSectionCollapsed(SECTION_IDS.unitEditor) &&
		(creatingUnit.value || unitPending.value || unitFormDirty.value)
	)
);
const unitEditorHeading = computed(() => {
	if (creatingUnit.value) return 'Draft a governed unit';
	const rawTitle = String(selectedUnit.value?.title || unitForm.title || 'Unit Plan').trim();
	const order = unitForm.unit_order;
	const title =
		order && rawTitle.startsWith(`Unit ${order}:`)
			? rawTitle.slice(`Unit ${order}:`.length).trim() || rawTitle
			: rawTitle;
	return order ? `Unit ${order}: ${title}` : title;
});
const unitSaveActionLabel = computed(() => {
	if (unitPending.value) return 'Saving...';
	return creatingUnit.value ? 'Create Unit Plan' : 'Save Unit Plan';
});
const unitSaveStatusLabel = computed(() => {
	if (unitPending.value) return 'Saving...';
	if (creatingUnit.value) return unitFormDirty.value ? 'Draft not saved yet' : 'Draft unit';
	return unitFormDirty.value ? 'Unsaved changes' : 'All changes saved';
});
const unitSaveSupportText = computed(() => {
	if (unitPending.value) return 'Saving the governed unit now.';
	if (creatingUnit.value) {
		return unitFormDirty.value
			? 'Create this governed unit when the draft looks right.'
			: 'Start filling the draft, then save it from here or from the sticky rail.';
	}
	return unitFormDirty.value
		? 'Save the unit before leaving so linked classes inherit the latest shared guidance.'
		: 'This governed unit is up to date.';
});
const navigationSections = computed<WorkspaceNavigationSection[]>(() => {
	const sections: WorkspaceNavigationSection[] = [
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

function coursePlanSectionStorageKey() {
	return `ifitwala.course-plan.sections.${props.coursePlan}`;
}

function coursePlanUnitPanelStorageKey() {
	return `ifitwala.course-plan.unit-panels.${props.coursePlan}`;
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

function loadCollapsedUnitPanels() {
	Object.assign(collapsedUnitPanels, collapsedUnitPanelDefaults);
	if (typeof window === 'undefined' || !props.coursePlan) return;
	try {
		const raw = window.localStorage.getItem(coursePlanUnitPanelStorageKey());
		if (!raw) return;
		const parsed = JSON.parse(raw) as Partial<Record<UnitPanelId, boolean>>;
		for (const panelId of Object.values(UNIT_PANEL_IDS)) {
			if (typeof parsed?.[panelId] === 'boolean') {
				collapsedUnitPanels[panelId] = parsed[panelId] as boolean;
			}
		}
	} catch {
		Object.assign(collapsedUnitPanels, collapsedUnitPanelDefaults);
	}
}

function persistCollapsedSections() {
	if (typeof window === 'undefined' || !props.coursePlan) return;
	window.localStorage.setItem(coursePlanSectionStorageKey(), JSON.stringify(collapsedSections));
}

function persistCollapsedUnitPanels() {
	if (typeof window === 'undefined' || !props.coursePlan) return;
	window.localStorage.setItem(
		coursePlanUnitPanelStorageKey(),
		JSON.stringify(collapsedUnitPanels)
	);
}

function isSectionCollapsed(sectionId: WorkspaceSectionId) {
	return Boolean(collapsedSections[sectionId]);
}

function isUnitPanelCollapsed(panelId: UnitPanelId) {
	return Boolean(collapsedUnitPanels[panelId]);
}

function setSectionCollapsed(sectionId: WorkspaceSectionId, collapsed: boolean) {
	collapsedSections[sectionId] = collapsed;
	persistCollapsedSections();
}

function setUnitPanelCollapsed(panelId: UnitPanelId, collapsed: boolean) {
	collapsedUnitPanels[panelId] = collapsed;
	persistCollapsedUnitPanels();
}

function setSectionExpanded(sectionId: WorkspaceSectionId, expanded: boolean) {
	setSectionCollapsed(sectionId, !expanded);
}

function setUnitPanelExpanded(panelId: UnitPanelId, expanded: boolean) {
	setUnitPanelCollapsed(panelId, !expanded);
}

function toggleSection(sectionId: WorkspaceSectionId) {
	setSectionCollapsed(sectionId, !isSectionCollapsed(sectionId));
}

function toggleUnitPanel(panelId: UnitPanelId) {
	setUnitPanelCollapsed(panelId, !isUnitPanelCollapsed(panelId));
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

function isStandardExpanded(localId: number) {
	return expandedStandardIds.value.includes(localId);
}

function toggleStandardExpansion(localId: number) {
	if (isStandardExpanded(localId)) {
		expandedStandardIds.value = expandedStandardIds.value.filter(id => id !== localId);
		return;
	}
	expandedStandardIds.value = [...expandedStandardIds.value, localId];
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

async function scrollToUnitPanel(panelId: UnitPanelId) {
	if (typeof document === 'undefined') return;
	setSectionExpanded(SECTION_IDS.unitEditor, true);
	setUnitPanelExpanded(panelId, true);
	await nextTick();
	document.getElementById(panelId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
	setUnitPanelExpanded(UNIT_PANEL_IDS.setup, true);
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
	unitForm.standards = (unit?.standards || []).map(standard =>
		buildEditableStandard(nextId, standard, unit?.program || '')
	);
	expandedStandardIds.value = [];
	unitForm.reflections = (unit?.shared_reflections || []).map(reflection =>
		buildEditableReflection(
			nextId,
			reflection,
			derivedReflectionAcademicYear.value,
			derivedReflectionSchool.value
		)
	);
	unitDraftSnapshot.value = buildUnitDraftSignature(
		unitForm,
		serializeStandards(unitForm.standards),
		serializeReflections(
			unitForm.reflections,
			derivedReflectionAcademicYear.value,
			derivedReflectionSchool.value
		)
	);
}

function syncQuizBankForm(bank: StaffCoursePlanQuizQuestionBank | null) {
	quizBankForm.quiz_question_bank = bank?.quiz_question_bank || '';
	quizBankForm.record_modified = bank?.record_modified || '';
	quizBankForm.bank_title = bank?.bank_title || '';
	quizBankForm.description = bank?.description || '';
	quizBankForm.is_published = bank?.is_published !== 0;
	quizBankForm.questions = (bank?.questions || []).map(question =>
		buildEditableQuizQuestion(nextId, question)
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
	setUnitPanelExpanded(UNIT_PANEL_IDS.setup, true);
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
			buildEditableStandard(
				nextId,
				{
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
				},
				unitForm.program || ''
			)
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
	expandedStandardIds.value = expandedStandardIds.value.filter(id => id !== localId);
}

function addReflection() {
	unitForm.reflections.push(
		buildEditableReflection(
			nextId,
			undefined,
			derivedReflectionAcademicYear.value,
			derivedReflectionSchool.value
		)
	);
}

function removeReflection(localId: number) {
	unitForm.reflections = unitForm.reflections.filter(
		reflection => reflection.local_id !== localId
	);
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
	quizBankForm.questions.push(buildBlankQuizQuestion(nextId));
}

function removeQuizQuestion(localId: number) {
	quizBankForm.questions = quizBankForm.questions.filter(
		question => question.local_id !== localId
	);
}

function addQuizOption(question: EditableQuizQuestion) {
	question.options.push(buildEditableQuizOption(nextId));
}

function removeQuizOption(question: EditableQuizQuestion, localId: number) {
	question.options = question.options.filter(option => option.local_id !== localId);
}

function handleQuizQuestionTypeChange(question: EditableQuizQuestion) {
	syncQuizQuestionType(question, nextId);
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
			standards: serializeStandards(unitForm.standards),
			reflections: serializeReflections(
				unitForm.reflections,
				derivedReflectionAcademicYear.value,
				derivedReflectionSchool.value
			),
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
			questions: serializeQuizQuestions(quizBankForm.questions),
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
		loadCollapsedUnitPanels();
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
	loadCollapsedUnitPanels();
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
