<!-- ifitwala_ed/ui-spa/src/components/overlays/class-hub/WheelPickerOverlay.vue -->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="$emit('after-leave')">
		<Dialog
			as="div"
			class="if-overlay if-overlay--class-hub"
			:style="overlayStyle"
			:initialFocus="initialFocus"
			@close="onDialogClose"
		>
			<TransitionChild
				as="template"
				enter="if-overlay__fade-enter"
				enter-from="if-overlay__fade-from"
				enter-to="if-overlay__fade-to"
				leave="if-overlay__fade-leave"
				leave-from="if-overlay__fade-to"
				leave-to="if-overlay__fade-from"
			>
				<div class="if-overlay__backdrop" @click="emitClose('backdrop')" />
			</TransitionChild>

			<div class="if-overlay__wrap" @click.self="emitClose('backdrop')">
				<TransitionChild
					as="template"
					enter="if-overlay__panel-enter"
					enter-from="if-overlay__panel-from"
					enter-to="if-overlay__panel-to"
					leave="if-overlay__panel-leave"
					leave-from="if-overlay__panel-to"
					leave-to="if-overlay__panel-from"
				>
					<DialogPanel class="if-overlay__panel wheel-picker">
						<button
							ref="initialFocus"
							type="button"
							class="sr-only"
							aria-hidden="true"
							tabindex="0"
							@click="emitClose('programmatic')"
						>
							Close
						</button>

						<div class="if-overlay__header wheel-picker__header">
							<div class="wheel-picker__headline">
								<p class="type-overline wheel-picker__eyebrow">{{ sourceLabel }}</p>
								<DialogTitle as="h2" class="type-h2 text-ink">Pick a student</DialogTitle>
								<p class="type-caption text-slate-token/70">
									Choose a student fairly, then move straight into the next classroom action.
								</p>
							</div>
							<button
								type="button"
								class="if-overlay__icon-button"
								aria-label="Close picker"
								@click="emitClose('programmatic')"
							>
								<span aria-hidden="true">x</span>
							</button>
						</div>

						<div class="if-overlay__body wheel-picker__body">
							<section v-if="viewState === 'loading'" class="wheel-picker__state">
								<p class="type-body-strong text-ink">Loading your class picker...</p>
								<p class="type-body text-slate-token/70">
									We are checking your live class and preparing the student list.
								</p>
							</section>

							<section v-else-if="viewState === 'multiple_current'" class="wheel-picker__state">
								<div class="wheel-picker__state-copy">
									<p class="type-body-strong text-ink">
										{{ resolutionMessage || 'Choose the class you want to use.' }}
									</p>
									<p class="type-body text-slate-token/70">
										You have more than one live class right now, so the picker needs one class
										before it can continue.
									</p>
								</div>
								<div class="wheel-picker__option-list">
									<button
										v-for="context in contextOptions"
										:key="context.student_group"
										type="button"
										class="wheel-picker__option"
										@click="chooseContext(context)"
									>
										<div>
											<p class="type-body-strong text-ink">{{ context.title }}</p>
											<p class="type-caption text-slate-token/70">
												{{ formatNowLine(context.now) }}
											</p>
										</div>
										<span class="wheel-picker__option-meta"
											>{{ context.students.length }} students</span
										>
									</button>
								</div>
							</section>

							<section v-else-if="viewState === 'no_current_class'" class="wheel-picker__state">
								<div class="wheel-picker__state-copy">
									<p class="type-body-strong text-ink">
										{{ resolutionMessage || 'No live class is available right now.' }}
									</p>
									<p class="type-body text-slate-token/70">
										Open your next class hub when you are ready, or come back once a class is live
										on your schedule.
									</p>
								</div>

								<div v-if="nextClass" class="wheel-picker__next-class">
									<p class="type-overline text-slate-token/70">Next class</p>
									<p class="type-body-strong text-ink">{{ nextClass.title }}</p>
									<p class="type-caption text-slate-token/70">
										{{ formatNowLine(nextClass.now) }}
									</p>
									<button
										type="button"
										class="wheel-picker__secondary"
										@click="openClassHub(nextClass)"
									>
										Open next class hub
									</button>
								</div>
							</section>

							<section v-else-if="viewState === 'unavailable'" class="wheel-picker__state">
								<div class="wheel-picker__state-copy">
									<p class="type-body-strong text-ink">
										{{ resolutionMessage || 'This picker is not available right now.' }}
									</p>
									<p class="type-body text-slate-token/70">
										Try opening the class hub directly from your schedule, then start the picker
										there.
									</p>
								</div>
							</section>

							<section v-else class="wheel-picker__layout">
								<div class="wheel-picker__stage">
									<div class="wheel-picker__context-card">
										<p class="type-overline text-slate-token/70">Class</p>
										<p class="type-body-strong text-ink">{{ activeContext?.title }}</p>
										<p class="type-caption text-slate-token/70">
											{{ activeContext ? formatNowLine(activeContext.now) : '' }}
										</p>
									</div>

									<div class="wheel-picker__wheel-shell">
										<div class="wheel-picker__pointer" aria-hidden="true"></div>
										<svg
											viewBox="0 0 100 100"
											class="wheel-picker__wheel"
											:style="wheelStyle"
											role="img"
											aria-label="Student picker wheel"
										>
											<template v-if="wheelSegments.length === 1">
												<circle cx="50" cy="50" r="48" :fill="wheelSegments[0].color" />
												<g transform="translate(50 28)">
													<text
														text-anchor="middle"
														dominant-baseline="middle"
														class="wheel-picker__label"
														:style="{ fontSize: `${labelFontSize}px` }"
													>
														{{ wheelSegments[0].label }}
													</text>
												</g>
											</template>
											<template v-else>
												<g v-for="segment in wheelSegments" :key="segment.student">
													<path
														:d="segment.path"
														:fill="segment.color"
														stroke="rgba(255,255,255,0.44)"
														stroke-width="0.8"
													/>
													<g :transform="segment.labelTransform">
														<text
															text-anchor="middle"
															dominant-baseline="middle"
															class="wheel-picker__label"
															:style="{ fontSize: `${labelFontSize}px` }"
														>
															{{ segment.label }}
														</text>
													</g>
												</g>
											</template>
											<circle
												cx="50"
												cy="50"
												r="48"
												fill="none"
												stroke="rgba(255,255,255,0.5)"
												stroke-width="1.1"
											/>
										</svg>
										<button
											type="button"
											class="wheel-picker__spin-core"
											:disabled="spinDisabled"
											@click="spinWheel"
										>
											<span class="type-overline text-amber-100/80">Ready</span>
											<span class="type-body-strong text-white">
												{{ spinning ? 'Picking...' : 'Pick' }}
											</span>
										</button>

										<div
											v-if="showCelebration"
											:key="celebrationSeed"
											class="wheel-picker__confetti"
											aria-hidden="true"
										>
											<span
												v-for="piece in confettiPieces"
												:key="piece.id"
												class="wheel-picker__confetti-piece"
												:style="piece.style"
											></span>
										</div>
									</div>

									<p class="type-caption text-slate-token/70">
										{{ wheelFootnote }}
									</p>
								</div>

								<div class="wheel-picker__controls">
									<div class="wheel-picker__control-card">
										<div class="wheel-picker__stat-row">
											<div>
												<p class="type-overline text-slate-token/70">Students ready</p>
												<p class="type-h3 text-ink">
													{{ availableStudents.length }}
													<span class="type-caption text-slate-token/60">
														of {{ totalStudents }}
													</span>
												</p>
											</div>
											<button
												type="button"
												class="wheel-picker__secondary"
												:disabled="!hasRemovedStudents"
												@click="resetRemovedStudents"
											>
												Reset names
											</button>
										</div>

										<label class="wheel-picker__checkbox-row">
											<input
												v-model="persistentRemoval"
												type="checkbox"
												class="wheel-picker__checkbox"
											/>
											<span class="type-body text-ink">Keep picked names removed until reset</span>
										</label>

										<p class="type-caption text-slate-token/70">
											{{ persistenceHelpText }}
										</p>
									</div>

									<div v-if="pickerMessage" class="wheel-picker__message">
										<p class="type-body text-ink">{{ pickerMessage }}</p>
									</div>

									<div v-if="selectedStudent" class="wheel-picker__selected-card">
										<p class="type-overline text-emerald-100/80">Selected student</p>
										<h3 class="type-h2 text-white">{{ selectedStudent.student_name }}</h3>
										<p class="type-body text-emerald-50/85">{{ selectedStudentHelpText }}</p>

										<div class="wheel-picker__action-grid">
											<button
												type="button"
												class="wheel-picker__primary"
												@click="openSelectedStudent"
											>
												Open student
											</button>
											<button
												type="button"
												class="wheel-picker__primary wheel-picker__primary--soft"
												@click="openQuickEvidence"
											>
												Add evidence
											</button>
											<button
												v-if="canCreateStudentLog"
												type="button"
												class="wheel-picker__primary wheel-picker__primary--soft"
												@click="openStudentLog"
											>
												Add note
											</button>
											<button
												type="button"
												class="wheel-picker__primary wheel-picker__primary--soft"
												:disabled="!canSpinAgain"
												@click="spinAgain"
											>
												Spin again
											</button>
										</div>
									</div>

									<div v-else class="wheel-picker__control-card wheel-picker__control-card--muted">
										<p class="type-body-strong text-ink">Teacher-friendly, student-friendly</p>
										<p class="type-body text-slate-token/70">
											The picker uses a fair random selection, then keeps the next classroom
											actions one click away.
										</p>
									</div>
								</div>
							</section>
						</div>

						<div class="if-overlay__footer wheel-picker__footer">
							<button
								type="button"
								class="wheel-picker__secondary"
								@click="emitClose('programmatic')"
							>
								Close
							</button>
							<button
								v-if="activeContext"
								type="button"
								class="wheel-picker__secondary"
								@click="openClassHub(activeContext)"
							>
								Open class hub
							</button>
						</div>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';

import { useOverlayStack } from '@/composables/useOverlayStack';
import { createClassHubService } from '@/lib/classHubService';
import {
	buildWheelTargetRotation,
	clearClassHubWheelPersistence,
	filterAvailableWheelStudents,
	loadClassHubWheelPersistence,
	saveClassHubWheelPersistence,
	secureRandomIndex,
} from '@/lib/classHubWheel';
import type {
	ClassHubWheelContext,
	ClassHubWheelResolution,
	ClassHubWheelStudent,
} from '@/types/classHub';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';
type ViewState = 'loading' | 'ready' | 'multiple_current' | 'no_current_class' | 'unavailable';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string | null;
	resolve_current_class?: boolean;
	source_label?: string | null;
	student_group?: string | null;
	title?: string | null;
	students?: ClassHubWheelStudent[];
	now?: Partial<ClassHubWheelContext['now']> | null;
	class_session?: string | null;
	can_create_student_log?: boolean;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const overlay = useOverlayStack();
const router = useRouter();
const service = createClassHubService();

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 60 }));
const sourceLabel = computed(() => props.source_label || 'Class Hub');

const viewState = ref<ViewState>('loading');
const resolutionMessage = ref('');
const contextOptions = ref<ClassHubWheelContext[]>([]);
const nextClass = ref<ClassHubWheelResolution['next_class']>(null);
const activeContext = ref<ClassHubWheelContext | null>(null);

const persistentRemoval = ref(false);
const removedStudentIds = ref<string[]>([]);
const selectedStudent = ref<ClassHubWheelStudent | null>(null);
const spinning = ref(false);
const rotation = ref(0);
const spinDurationMs = ref(4800);
const celebrationSeed = ref(0);
const showCelebration = ref(false);
const pickerMessage = ref('');
const lastSpinStudents = ref<ClassHubWheelStudent[] | null>(null);

const motionQuery = ref<MediaQueryList | null>(null);
const prefersReducedMotion = ref(false);

let spinTimer: number | null = null;
let celebrationTimer: number | null = null;

const wheelPalette = [
	'#0f5b52',
	'#c79843',
	'#1e3f53',
	'#a95d45',
	'#527667',
	'#394c6d',
	'#d9ab58',
	'#5f7a90',
];

const confettiPieces = [
	{
		id: 'c1',
		style: { '--x': '-86px', '--delay': '0ms', '--rotate': '-24deg', '--color': '#d7a54f' },
	},
	{
		id: 'c2',
		style: { '--x': '-72px', '--delay': '60ms', '--rotate': '18deg', '--color': '#eff2eb' },
	},
	{
		id: 'c3',
		style: { '--x': '-58px', '--delay': '20ms', '--rotate': '32deg', '--color': '#1e7a64' },
	},
	{
		id: 'c4',
		style: { '--x': '-42px', '--delay': '90ms', '--rotate': '-8deg', '--color': '#f0c979' },
	},
	{
		id: 'c5',
		style: { '--x': '-24px', '--delay': '30ms', '--rotate': '12deg', '--color': '#7ca7a0' },
	},
	{
		id: 'c6',
		style: { '--x': '-8px', '--delay': '70ms', '--rotate': '24deg', '--color': '#f4ede1' },
	},
	{
		id: 'c7',
		style: { '--x': '12px', '--delay': '0ms', '--rotate': '-28deg', '--color': '#d7a54f' },
	},
	{
		id: 'c8',
		style: { '--x': '28px', '--delay': '50ms', '--rotate': '16deg', '--color': '#1b6f5d' },
	},
	{
		id: 'c9',
		style: { '--x': '46px', '--delay': '15ms', '--rotate': '-14deg', '--color': '#f6e2b0' },
	},
	{
		id: 'c10',
		style: { '--x': '62px', '--delay': '80ms', '--rotate': '20deg', '--color': '#dfe6de' },
	},
	{
		id: 'c11',
		style: { '--x': '80px', '--delay': '45ms', '--rotate': '-16deg', '--color': '#7aa699' },
	},
	{
		id: 'c12',
		style: { '--x': '96px', '--delay': '95ms', '--rotate': '28deg', '--color': '#d7a54f' },
	},
];

const totalStudents = computed(() => activeContext.value?.students.length || 0);
const availableStudents = computed(() => {
	if (!activeContext.value) return [];
	if (!persistentRemoval.value) return activeContext.value.students;
	return filterAvailableWheelStudents(activeContext.value.students, removedStudentIds.value);
});
const wheelStudents = computed(() => {
	if (lastSpinStudents.value && (spinning.value || selectedStudent.value))
		return lastSpinStudents.value;
	return availableStudents.value;
});
const canCreateStudentLog = computed(() =>
	Boolean(activeContext.value?.permissions?.can_create_student_log)
);
const hasRemovedStudents = computed(() => removedStudentIds.value.length > 0);
const spinDisabled = computed(() => spinning.value || availableStudents.value.length === 0);
const canSpinAgain = computed(() => !spinning.value && availableStudents.value.length > 0);

const wheelFootnote = computed(() => {
	if (spinning.value) return 'Picking a student now...';
	if (!activeContext.value) return '';
	if (totalStudents.value === 0) return 'No active students are available for this class yet.';
	if (availableStudents.value.length === 0)
		return 'All available names are currently removed. Reset names to continue.';
	return `${availableStudents.value.length} students are ready for the next fair pick.`;
});

const persistenceHelpText = computed(() =>
	persistentRemoval.value
		? 'Picked names stay out until you reset the list for this class.'
		: 'Each pick stays independent, so the same student can appear again later.'
);
const selectedStudentHelpText = computed(() =>
	props.class_session
		? 'Use the next action while the class context is already in place.'
		: 'Use the next action here, or open the class hub for live session tools.'
);

const labelFontSize = computed(() => {
	const count = wheelStudents.value.length;
	if (count >= 14) return 2.7;
	if (count >= 10) return 3.1;
	if (count >= 7) return 3.6;
	return 4.2;
});

const wheelStyle = computed(() => ({
	transform: `rotate(${rotation.value}deg)`,
	transitionDuration: `${spinDurationMs.value}ms`,
	transitionTimingFunction: 'cubic-bezier(0.12, 0.82, 0.16, 1)',
}));

const wheelSegments = computed(() => {
	const students = wheelStudents.value;
	const count = students.length;
	if (!count) return [];

	const angle = 360 / count;
	return students.map((student, index) => {
		const startAngle = index * angle;
		const endAngle = count === 1 ? 359.999 : (index + 1) * angle;
		const midAngle = startAngle + angle / 2;
		const labelPoint = polarPoint(50, 50, 30, midAngle);
		const labelRotation = midAngle <= 180 ? midAngle : midAngle + 180;

		return {
			student: student.student,
			label: shortenLabel(student.student_name, count),
			color: wheelPalette[index % wheelPalette.length],
			path: count === 1 ? '' : describeSectorPath(50, 50, 48, startAngle, endAngle),
			labelTransform: `translate(${labelPoint.x} ${labelPoint.y}) rotate(${labelRotation})`,
		};
	});
});

const initialFocus = ref<HTMLElement | null>(null);

watch(
	() => props.open,
	isOpen => {
		if (!isOpen) return;
		void hydratePicker();
	},
	{ immediate: true }
);

watch(
	() =>
		[
			persistentRemoval.value,
			removedStudentIds.value.join('|'),
			activeContext.value?.student_group,
		].join('::'),
	() => {
		const studentGroup = activeContext.value?.student_group;
		if (!studentGroup) return;

		if (!persistentRemoval.value) {
			clearClassHubWheelPersistence(studentGroup);
			return;
		}

		saveClassHubWheelPersistence(studentGroup, {
			persistent: true,
			removed_student_ids: removedStudentIds.value,
		});
	}
);

watch(persistentRemoval, (enabled, previous) => {
	if (enabled === previous) return;
	if (!enabled) {
		removedStudentIds.value = [];
	}
	pickerMessage.value = '';
});

onMounted(() => {
	if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
		const query = window.matchMedia('(prefers-reduced-motion: reduce)');
		motionQuery.value = query;
		prefersReducedMotion.value = query.matches;
		query.addEventListener?.('change', handleMotionChange);
	}
});

onBeforeUnmount(() => {
	clearTimers();
	motionQuery.value?.removeEventListener?.('change', handleMotionChange);
	if (typeof document !== 'undefined') {
		document.removeEventListener('keydown', onKeydown, true);
	}
});

watch(
	() => props.open,
	isOpen => {
		if (typeof document === 'undefined') return;
		if (isOpen) document.addEventListener('keydown', onKeydown, true);
		else document.removeEventListener('keydown', onKeydown, true);
	},
	{ immediate: true }
);

function handleMotionChange(event: MediaQueryListEvent) {
	prefersReducedMotion.value = event.matches;
}

function clearTimers() {
	if (spinTimer) {
		window.clearTimeout(spinTimer);
		spinTimer = null;
	}
	if (celebrationTimer) {
		window.clearTimeout(celebrationTimer);
		celebrationTimer = null;
	}
}

function clearSelection() {
	selectedStudent.value = null;
	showCelebration.value = false;
	lastSpinStudents.value = null;
	pickerMessage.value = '';
}

function resetWheelState() {
	clearTimers();
	clearSelection();
	contextOptions.value = [];
	nextClass.value = null;
	activeContext.value = null;
	persistentRemoval.value = false;
	removedStudentIds.value = [];
	spinning.value = false;
	rotation.value = 0;
	spinDurationMs.value = prefersReducedMotion.value ? 120 : 4800;
}

async function hydratePicker() {
	resetWheelState();
	viewState.value = 'loading';
	resolutionMessage.value = '';

	if (props.resolve_current_class) {
		try {
			const payload = await service.resolveCurrentPickerContext();
			applyResolution(payload);
			return;
		} catch (err) {
			console.error('[WheelPickerOverlay] resolveCurrentPickerContext failed', err);
			viewState.value = 'unavailable';
			resolutionMessage.value = 'The picker could not resolve your current class right now.';
			return;
		}
	}

	if (!props.student_group) {
		viewState.value = 'unavailable';
		resolutionMessage.value = 'Open this picker from a class that is already in context.';
		return;
	}

	activateContext(buildContextFromProps());
}

function applyResolution(payload: ClassHubWheelResolution) {
	resolutionMessage.value = payload.message || '';
	nextClass.value = payload.next_class || null;

	if (payload.status === 'ready' && payload.contexts.length) {
		activateContext(payload.contexts[0]);
		return;
	}

	if (payload.status === 'multiple_current') {
		contextOptions.value = payload.contexts || [];
		viewState.value = 'multiple_current';
		return;
	}

	viewState.value = payload.status === 'unavailable' ? 'unavailable' : 'no_current_class';
}

function buildContextFromProps(): ClassHubWheelContext {
	return {
		student_group: String(props.student_group || '').trim(),
		title: String(props.title || props.student_group || '').trim(),
		academic_year: null,
		course: null,
		permissions: {
			can_create_student_log: Boolean(props.can_create_student_log),
		},
		now: {
			date_iso: props.now?.date_iso ?? null,
			date_label: props.now?.date_label || 'Today',
			block_number: props.now?.block_number ?? null,
			block_label: props.now?.block_label ?? null,
			time_range: props.now?.time_range ?? null,
			location: props.now?.location ?? null,
		},
		students: (props.students || []).map(student => ({
			student: student.student,
			student_name: student.student_name,
		})),
	};
}

function activateContext(context: ClassHubWheelContext) {
	activeContext.value = context;
	viewState.value = 'ready';
	loadPersistenceForContext(context.student_group);
}

function chooseContext(context: ClassHubWheelContext) {
	activateContext(context);
}

function loadPersistenceForContext(studentGroup: string) {
	const persisted = loadClassHubWheelPersistence(studentGroup);
	persistentRemoval.value = persisted.persistent;
	removedStudentIds.value = persisted.persistent ? persisted.removed_student_ids : [];
}

function emitClose(reason: CloseReason) {
	emit('close', reason);
}

function onDialogClose(_payload: unknown) {
	// OverlayHost owns close enforcement.
}

function onKeydown(event: KeyboardEvent) {
	if (!props.open) return;
	if (event.key === 'Escape') emitClose('esc');
}

function resetRemovedStudents() {
	if (!activeContext.value) return;
	removedStudentIds.value = [];
	clearClassHubWheelPersistence(activeContext.value.student_group);
	pickerMessage.value = 'The full class list is back in the wheel.';
}

function spinWheel() {
	if (spinDisabled.value || !activeContext.value) return;

	clearTimers();
	clearSelection();

	const pool = availableStudents.value.slice();
	if (!pool.length) return;

	const selectedIndex = secureRandomIndex(pool.length);
	const nextStudent = pool[selectedIndex];
	lastSpinStudents.value = pool;
	spinning.value = true;
	spinDurationMs.value = prefersReducedMotion.value ? 180 : 4800;
	rotation.value = buildWheelTargetRotation(
		rotation.value,
		selectedIndex,
		pool.length,
		prefersReducedMotion.value ? 1 : 7
	);

	spinTimer = window.setTimeout(() => {
		selectedStudent.value = nextStudent;
		spinning.value = false;
		if (persistentRemoval.value) {
			removedStudentIds.value = Array.from(
				new Set([...removedStudentIds.value, nextStudent.student])
			);
		}

		if (!prefersReducedMotion.value) {
			showCelebration.value = true;
			celebrationSeed.value += 1;
			celebrationTimer = window.setTimeout(() => {
				showCelebration.value = false;
			}, 1100);
		}
	}, spinDurationMs.value + 40);
}

function spinAgain() {
	if (!canSpinAgain.value) return;
	clearSelection();
	spinWheel();
}

function openSelectedStudent() {
	if (!selectedStudent.value || !activeContext.value) return;

	overlay.replaceTop('class-hub-student-context', {
		student: selectedStudent.value.student,
		student_name: selectedStudent.value.student_name,
		student_group: activeContext.value.student_group,
		class_session: props.class_session ?? null,
		can_create_student_log: activeContext.value.permissions.can_create_student_log,
	});
}

function openQuickEvidence() {
	if (!selectedStudent.value || !activeContext.value) return;

	overlay.replaceTop('class-hub-quick-evidence', {
		student_group: activeContext.value.student_group,
		class_session: props.class_session ?? null,
		students: activeContext.value.students,
		preselected_students: [selectedStudent.value],
	});
}

function openStudentLog() {
	if (!selectedStudent.value || !activeContext.value) return;
	if (!canCreateStudentLog.value) {
		pickerMessage.value = 'Student notes are not available for your current role in this flow.';
		return;
	}

	overlay.replaceTop('student-log-create', {
		mode: 'attendance',
		sourceLabel: sourceLabel.value,
		student: {
			id: selectedStudent.value.student,
			label: selectedStudent.value.student_name,
			image: null,
			meta: null,
		},
		student_group: {
			id: activeContext.value.student_group,
			label: activeContext.value.title,
		},
	});
}

function openClassHub(
	context:
		| Pick<ClassHubWheelContext, 'student_group' | 'now'>
		| NonNullable<ClassHubWheelResolution['next_class']>
) {
	const query: Record<string, string> = {};
	if (context.now?.date_iso) query.date = context.now.date_iso;
	if (context.now?.block_number) query.block = String(context.now.block_number);

	emitClose('programmatic');
	void router.push({
		name: 'ClassHub',
		params: { studentGroup: context.student_group },
		query,
	});
}

function formatNowLine(now?: Partial<ClassHubWheelContext['now']> | null) {
	if (!now) return 'Class time to be confirmed';
	const parts = [now.date_label, now.block_label, now.time_range, now.location].filter(Boolean);
	return parts.length ? parts.join(' | ') : 'Class time to be confirmed';
}

function polarPoint(cx: number, cy: number, radius: number, angleInDegrees: number) {
	const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
	return {
		x: cx + radius * Math.cos(angleInRadians),
		y: cy + radius * Math.sin(angleInRadians),
	};
}

function describeSectorPath(
	cx: number,
	cy: number,
	radius: number,
	startAngle: number,
	endAngle: number
) {
	const start = polarPoint(cx, cy, radius, endAngle);
	const end = polarPoint(cx, cy, radius, startAngle);
	const largeArcFlag = endAngle - startAngle <= 180 ? 0 : 1;

	return [
		`M ${cx} ${cy}`,
		`L ${start.x} ${start.y}`,
		`A ${radius} ${radius} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`,
		'Z',
	].join(' ');
}

function shortenLabel(label: string, segmentCount: number) {
	const maxLength = segmentCount >= 12 ? 10 : segmentCount >= 8 ? 14 : 18;
	const clean = String(label || '').trim();
	if (clean.length <= maxLength) return clean;
	return `${clean.slice(0, maxLength - 1).trim()}...`;
}
</script>

<style scoped>
.wheel-picker {
	max-width: min(1120px, calc(100vw - 2rem));
	background:
		radial-gradient(circle at top, rgba(208, 152, 67, 0.12), transparent 32%),
		linear-gradient(160deg, rgba(245, 247, 245, 0.98), rgba(233, 239, 237, 0.94));
	border: 1px solid rgba(31, 55, 49, 0.1);
}

.wheel-picker__header,
.wheel-picker__footer {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
	padding: 1.5rem;
}

.wheel-picker__headline {
	display: grid;
	gap: 0.35rem;
}

.wheel-picker__eyebrow {
	color: rgb(15 91 82 / 0.74);
}

.wheel-picker__body {
	padding: 0 1.5rem 1.5rem;
}

.wheel-picker__layout {
	display: grid;
	gap: 1.25rem;
}

.wheel-picker__stage,
.wheel-picker__controls,
.wheel-picker__state {
	display: grid;
	gap: 1rem;
}

.wheel-picker__context-card,
.wheel-picker__control-card,
.wheel-picker__state,
.wheel-picker__next-class {
	border: 1px solid rgba(31, 55, 49, 0.12);
	border-radius: 1.25rem;
	background: rgba(255, 255, 255, 0.88);
	box-shadow: 0 12px 30px rgba(22, 36, 33, 0.08);
	padding: 1rem;
}

.wheel-picker__control-card--muted {
	background: rgba(245, 247, 245, 0.82);
}

.wheel-picker__wheel-shell {
	position: relative;
	display: grid;
	place-items: center;
	padding: 1.25rem;
	border-radius: 1.75rem;
	background:
		radial-gradient(circle at 50% 42%, rgba(255, 255, 255, 0.28), transparent 50%),
		linear-gradient(180deg, #0d1f1a, #153028);
	box-shadow:
		inset 0 1px 0 rgba(255, 255, 255, 0.16),
		0 20px 50px rgba(11, 21, 18, 0.28);
	min-height: 28rem;
}

.wheel-picker__wheel {
	width: min(100%, 29rem);
	max-width: 29rem;
	filter: drop-shadow(0 14px 24px rgba(8, 15, 13, 0.22));
}

.wheel-picker__label {
	fill: rgba(255, 251, 244, 0.96);
	font-weight: 700;
	letter-spacing: 0.02em;
}

.wheel-picker__pointer {
	position: absolute;
	top: 1.1rem;
	left: 50%;
	width: 0;
	height: 0;
	transform: translateX(-50%);
	border-left: 14px solid transparent;
	border-right: 14px solid transparent;
	border-top: 28px solid #d9ab58;
	filter: drop-shadow(0 8px 14px rgba(10, 20, 16, 0.34));
	z-index: 2;
}

.wheel-picker__pointer::after {
	content: '';
	position: absolute;
	top: -28px;
	left: -5px;
	width: 10px;
	height: 14px;
	background: rgba(255, 244, 214, 0.9);
	border-radius: 999px;
}

.wheel-picker__spin-core {
	position: absolute;
	display: grid;
	gap: 0.15rem;
	place-items: center;
	width: 7.4rem;
	height: 7.4rem;
	border-radius: 999px;
	border: 1px solid rgba(255, 255, 255, 0.18);
	background:
		radial-gradient(circle at top, rgba(231, 192, 112, 0.94), rgba(203, 145, 59, 0.94)), #c58f3d;
	box-shadow:
		inset 0 1px 0 rgba(255, 251, 241, 0.45),
		0 18px 28px rgba(8, 15, 13, 0.28);
	z-index: 3;
}

.wheel-picker__spin-core:disabled {
	opacity: 0.7;
	cursor: not-allowed;
}

.wheel-picker__confetti {
	position: absolute;
	inset: 0;
	pointer-events: none;
	overflow: hidden;
	border-radius: inherit;
}

.wheel-picker__confetti-piece {
	position: absolute;
	left: 50%;
	top: 28%;
	width: 0.6rem;
	height: 1.15rem;
	border-radius: 999px;
	background: var(--color);
	transform: translateX(-50%) rotate(var(--rotate));
	animation: confetti-fall 920ms cubic-bezier(0.14, 0.66, 0.18, 1) forwards;
	animation-delay: var(--delay);
	box-shadow: 0 10px 18px rgba(7, 12, 10, 0.16);
}

.wheel-picker__stat-row {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
}

.wheel-picker__checkbox-row {
	display: flex;
	align-items: flex-start;
	gap: 0.75rem;
}

.wheel-picker__checkbox {
	margin-top: 0.25rem;
	width: 1rem;
	height: 1rem;
	accent-color: #0f5b52;
}

.wheel-picker__selected-card {
	display: grid;
	gap: 0.8rem;
	padding: 1.15rem;
	border-radius: 1.35rem;
	background:
		radial-gradient(circle at top, rgba(238, 200, 113, 0.22), transparent 38%),
		linear-gradient(160deg, #0f5b52, #17382f);
	box-shadow: 0 18px 42px rgba(12, 22, 19, 0.22);
}

.wheel-picker__action-grid,
.wheel-picker__option-list {
	display: grid;
	gap: 0.75rem;
}

.wheel-picker__option {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
	padding: 0.95rem 1rem;
	border-radius: 1rem;
	border: 1px solid rgba(31, 55, 49, 0.1);
	background: rgba(255, 255, 255, 0.9);
	text-align: left;
	transition:
		transform 160ms ease,
		border-color 160ms ease,
		box-shadow 160ms ease;
}

.wheel-picker__option:hover {
	transform: translateY(-1px);
	border-color: rgba(15, 91, 82, 0.38);
	box-shadow: 0 12px 24px rgba(12, 24, 20, 0.1);
}

.wheel-picker__option-meta {
	white-space: nowrap;
	font-size: 0.78rem;
	font-weight: 700;
	letter-spacing: 0.03em;
	text-transform: uppercase;
	color: rgba(15, 91, 82, 0.78);
}

.wheel-picker__message {
	padding: 0.95rem 1rem;
	border-radius: 1rem;
	background: rgba(255, 248, 231, 0.9);
	border: 1px solid rgba(215, 165, 79, 0.26);
}

.wheel-picker__primary,
.wheel-picker__secondary {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	padding: 0.75rem 1rem;
	border-radius: 999px;
	font-weight: 700;
	letter-spacing: 0.01em;
	transition:
		transform 160ms ease,
		background-color 160ms ease,
		border-color 160ms ease,
		color 160ms ease;
}

.wheel-picker__primary {
	background: rgba(250, 252, 249, 0.96);
	color: #113c36;
}

.wheel-picker__primary--soft {
	background: rgba(255, 255, 255, 0.18);
	color: white;
	border: 1px solid rgba(255, 255, 255, 0.18);
}

.wheel-picker__primary:disabled,
.wheel-picker__secondary:disabled {
	opacity: 0.55;
	cursor: not-allowed;
	transform: none;
}

.wheel-picker__secondary {
	border: 1px solid rgba(31, 55, 49, 0.14);
	background: rgba(255, 255, 255, 0.9);
	color: #113c36;
}

.wheel-picker__primary:not(:disabled):hover,
.wheel-picker__secondary:not(:disabled):hover {
	transform: translateY(-1px);
}

@keyframes confetti-fall {
	0% {
		opacity: 0;
		transform: translate(-50%, -4px) rotate(var(--rotate)) scale(0.7);
	}

	12% {
		opacity: 1;
	}

	100% {
		opacity: 0;
		transform: translate(calc(-50% + var(--x)), 210px) rotate(calc(var(--rotate) * 2.2))
			scale(0.95);
	}
}

@media (min-width: 960px) {
	.wheel-picker__layout {
		grid-template-columns: minmax(0, 1.2fr) minmax(21rem, 0.8fr);
		align-items: start;
	}

	.wheel-picker__stage {
		position: sticky;
		top: 1rem;
	}
}

@media (prefers-reduced-motion: reduce) {
	.wheel-picker__wheel,
	.wheel-picker__option,
	.wheel-picker__primary,
	.wheel-picker__secondary,
	.wheel-picker__confetti-piece {
		transition: none !important;
		animation: none !important;
	}
}
</style>
