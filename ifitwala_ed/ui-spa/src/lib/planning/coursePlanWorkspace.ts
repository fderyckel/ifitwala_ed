import type {
	StaffCoursePlanQuizQuestion,
	StaffCoursePlanQuizQuestionOption,
} from '@/types/contracts/staff_teaching/get_staff_course_plan_surface';
import type {
	StaffPlanningReflection,
	StaffPlanningStandard,
} from '@/types/contracts/staff_teaching/get_staff_class_planning_surface';

export const SECTION_IDS = {
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

export const UNIT_PANEL_IDS = {
	setup: 'course-plan-unit-setup',
	narrative: 'course-plan-unit-narrative',
	learningFocus: 'course-plan-unit-learning-focus',
} as const;

export type WorkspaceSectionId = (typeof SECTION_IDS)[keyof typeof SECTION_IDS];
export type UnitPanelId = (typeof UNIT_PANEL_IDS)[keyof typeof UNIT_PANEL_IDS];

export type WorkspaceNavigationSection = {
	id: WorkspaceSectionId;
	label: string;
	count?: number | null;
};

export type EditableStandard = StaffPlanningStandard & {
	local_id: number;
};

export type EditableReflection = StaffPlanningReflection & {
	local_id: number;
};

export type EditableQuizQuestionOption = Omit<StaffCoursePlanQuizQuestionOption, 'is_correct'> & {
	local_id: number;
	is_correct: boolean;
};

export type EditableQuizQuestion = Omit<StaffCoursePlanQuizQuestion, 'options' | 'is_published'> & {
	local_id: number;
	is_published: boolean;
	options: EditableQuizQuestionOption[];
};

export type CoursePlanFormState = {
	record_modified: string;
	title: string;
	academic_year: string;
	cycle_label: string;
	plan_status: string;
	summary: string;
};

export type UnitFormState = {
	unit_plan: string;
	record_modified: string;
	title: string;
	program: string;
	unit_code: string;
	unit_order: number | null;
	unit_status: string;
	version: string;
	duration: string;
	estimated_duration: string;
	is_published: boolean;
	overview: string;
	essential_understanding: string;
	misconceptions: string;
	content: string;
	skills: string;
	concepts: string;
	standards: EditableStandard[];
	reflections: EditableReflection[];
};

export type QuizBankFormState = {
	quiz_question_bank: string;
	record_modified: string;
	bank_title: string;
	description: string;
	is_published: boolean;
	questions: EditableQuizQuestion[];
};

export const coursePlanStatusOptions = ['Draft', 'Active', 'Archived'] as const;
export const unitStatusOptions = ['Draft', 'Active', 'Archived'] as const;
export const coverageLevelOptions = ['Introduced', 'Reinforced', 'Mastered'] as const;
export const alignmentStrengthOptions = ['Exact', 'Partial', 'Broad'] as const;
export const quizQuestionTypeOptions = [
	'Single Choice',
	'Multiple Answer',
	'True / False',
	'Short Answer',
	'Essay',
] as const;

type NextId = () => number;

export function parseIsoDate(value?: string | null) {
	if (!value) return null;
	const parsed = new Date(`${value}T00:00:00`);
	return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function normalizeSnapshotText(value?: string | null) {
	return String(value || '').trim();
}

export function toPlainText(value?: string | null) {
	return String(value || '')
		.replace(/<style[\s\S]*?<\/style>/gi, ' ')
		.replace(/<script[\s\S]*?<\/script>/gi, ' ')
		.replace(/<[^>]*>/g, ' ')
		.replace(/&nbsp;|&#160;/gi, ' ')
		.trim();
}

export function hasRichTextContent(value?: string | null) {
	return Boolean(toPlainText(value));
}

export function normalizeSnapshotRichText(value?: string | null) {
	return hasRichTextContent(value) ? String(value || '').trim() : '';
}

export function trimmedValue(value?: string | null) {
	return String(value || '').trim();
}

export function normalizeStandardForSnapshot(standard: StaffPlanningStandard) {
	return {
		learning_standard: normalizeSnapshotText(standard.learning_standard),
		framework_name: normalizeSnapshotText(standard.framework_name),
		framework_version: normalizeSnapshotText(standard.framework_version),
		subject_area: normalizeSnapshotText(standard.subject_area),
		program: normalizeSnapshotText(standard.program),
		strand: normalizeSnapshotText(standard.strand),
		substrand: normalizeSnapshotText(standard.substrand),
		standard_code: normalizeSnapshotText(standard.standard_code),
		standard_description: normalizeSnapshotText(standard.standard_description),
		coverage_level: normalizeSnapshotText(standard.coverage_level),
		alignment_strength: normalizeSnapshotText(standard.alignment_strength),
		alignment_type: normalizeSnapshotText(standard.alignment_type),
		notes: normalizeSnapshotText(standard.notes),
	};
}

export function normalizeReflectionForSnapshot(reflection: StaffPlanningReflection) {
	return {
		academic_year: normalizeSnapshotText(reflection.academic_year),
		school: normalizeSnapshotText(reflection.school),
		prior_to_the_unit: normalizeSnapshotRichText(reflection.prior_to_the_unit),
		during_the_unit: normalizeSnapshotRichText(reflection.during_the_unit),
		what_work_well: normalizeSnapshotRichText(reflection.what_work_well),
		what_didnt_work_well: normalizeSnapshotRichText(reflection.what_didnt_work_well),
		changes_suggestions: normalizeSnapshotRichText(reflection.changes_suggestions),
	};
}

export function buildUnitDraftSignature(
	unitForm: UnitFormState,
	standards: StaffPlanningStandard[],
	reflections: StaffPlanningReflection[]
) {
	return JSON.stringify({
		title: normalizeSnapshotText(unitForm.title),
		program: normalizeSnapshotText(unitForm.program),
		unit_code: normalizeSnapshotText(unitForm.unit_code),
		unit_order: unitForm.unit_order ?? null,
		unit_status: normalizeSnapshotText(unitForm.unit_status),
		version: normalizeSnapshotText(unitForm.version),
		duration: normalizeSnapshotText(unitForm.duration),
		estimated_duration: normalizeSnapshotText(unitForm.estimated_duration),
		is_published: unitForm.is_published ? 1 : 0,
		overview: normalizeSnapshotRichText(unitForm.overview),
		essential_understanding: normalizeSnapshotRichText(unitForm.essential_understanding),
		misconceptions: normalizeSnapshotRichText(unitForm.misconceptions),
		content: normalizeSnapshotRichText(unitForm.content),
		skills: normalizeSnapshotRichText(unitForm.skills),
		concepts: normalizeSnapshotRichText(unitForm.concepts),
		standards: standards.map(standard => normalizeStandardForSnapshot(standard)),
		reflections: reflections.map(reflection => normalizeReflectionForSnapshot(reflection)),
	});
}

export function standardSummaryTokens(standard: EditableStandard) {
	const strand = trimmedValue(standard.strand);
	const substrand = trimmedValue(standard.substrand);
	const coverageLevel = trimmedValue(standard.coverage_level);
	const alignmentType = trimmedValue(standard.alignment_type);
	const alignmentStrength = trimmedValue(standard.alignment_strength);

	return [
		{
			key: 'strand',
			label: strand || 'Strand pending',
			pending: !strand,
		},
		{
			key: 'substrand',
			label: substrand || 'Substrand pending',
			pending: !substrand,
		},
		{
			key: 'coverage-level',
			label: coverageLevel ? `Coverage: ${coverageLevel}` : 'Coverage pending',
			pending: !coverageLevel,
		},
		{
			key: 'alignment-type',
			label: alignmentType ? `Type: ${alignmentType}` : 'Type pending',
			pending: !alignmentType,
		},
		{
			key: 'alignment-strength',
			label: alignmentStrength ? `Strength: ${alignmentStrength}` : 'Strength pending',
			pending: !alignmentStrength,
		},
	];
}

export function standardSummaryDescription(standard: EditableStandard) {
	return toPlainText(standard.standard_description) || 'Standard description pending.';
}

export function isChoiceQuestion(questionType?: string | null) {
	return ['Single Choice', 'Multiple Answer', 'True / False'].includes(questionType || '');
}

export function buildEditableStandard(
	nextId: NextId,
	standard?: StaffPlanningStandard,
	fallbackProgram = ''
): EditableStandard {
	return {
		local_id: nextId(),
		learning_standard: standard?.learning_standard || '',
		framework_name: standard?.framework_name || '',
		framework_version: standard?.framework_version || '',
		subject_area: standard?.subject_area || '',
		program: standard?.program || fallbackProgram,
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

export function buildEditableReflection(
	nextId: NextId,
	reflection?: StaffPlanningReflection,
	academicYear = '',
	school = ''
): EditableReflection {
	return {
		local_id: nextId(),
		academic_year: reflection?.academic_year || academicYear,
		school: reflection?.school || school,
		prior_to_the_unit: reflection?.prior_to_the_unit || '',
		during_the_unit: reflection?.during_the_unit || '',
		what_work_well: reflection?.what_work_well || '',
		what_didnt_work_well: reflection?.what_didnt_work_well || '',
		changes_suggestions: reflection?.changes_suggestions || '',
	};
}

export function buildEditableQuizOption(
	nextId: NextId,
	option?: StaffCoursePlanQuizQuestionOption
): EditableQuizQuestionOption {
	return {
		local_id: nextId(),
		option_text: option?.option_text || '',
		is_correct: Boolean(option?.is_correct),
	};
}

export function buildEditableQuizQuestion(
	nextId: NextId,
	question?: StaffCoursePlanQuizQuestion
): EditableQuizQuestion {
	return {
		local_id: nextId(),
		quiz_question: question?.quiz_question || '',
		title: question?.title || '',
		question_type: question?.question_type || 'Single Choice',
		is_published: question?.is_published !== 0,
		prompt: question?.prompt || '',
		accepted_answers: question?.accepted_answers || '',
		explanation: question?.explanation || '',
		options: (question?.options || []).map(option => buildEditableQuizOption(nextId, option)),
	};
}

export function handleQuizQuestionTypeChange(question: EditableQuizQuestion, nextId: NextId) {
	if (question.question_type === 'True / False') {
		question.options = [
			buildEditableQuizOption(nextId, { option_text: 'True', is_correct: 1 }),
			buildEditableQuizOption(nextId, { option_text: 'False', is_correct: 0 }),
		];
		question.accepted_answers = '';
		return;
	}

	if (isChoiceQuestion(question.question_type)) {
		if (question.options.length < 2) {
			question.options = [buildEditableQuizOption(nextId), buildEditableQuizOption(nextId)];
		}
		question.accepted_answers = '';
		return;
	}

	question.options = [];
	if (question.question_type !== 'Short Answer') {
		question.accepted_answers = '';
	}
}

export function buildBlankQuizQuestion(nextId: NextId, questionType = 'Single Choice') {
	const question = buildEditableQuizQuestion(nextId, {
		title: '',
		question_type: questionType,
		is_published: 1,
		prompt: '',
		accepted_answers: '',
		explanation: '',
		options: [],
	});
	handleQuizQuestionTypeChange(question, nextId);
	return question;
}

export function serializeStandards(standards: EditableStandard[]): StaffPlanningStandard[] {
	return standards.map(({ local_id, ...row }) => row);
}

export function serializeReflections(
	reflections: EditableReflection[],
	derivedAcademicYear = '',
	derivedSchool = ''
): StaffPlanningReflection[] {
	return reflections.map(({ local_id, academic_year, school, ...row }) => ({
		...row,
		academic_year: derivedAcademicYear || academic_year || null,
		school: derivedSchool || school || null,
	}));
}

export function serializeQuizQuestions(
	questions: EditableQuizQuestion[]
): StaffCoursePlanQuizQuestion[] {
	return questions.map(({ local_id, is_published, options, ...question }) => ({
		...question,
		is_published: is_published ? 1 : 0,
		options: options.map(({ local_id: optionLocalId, is_correct, ...option }) => ({
			...option,
			is_correct: is_correct ? 1 : 0,
		})),
	}));
}
