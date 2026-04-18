<template>
	<div class="staff-shell space-y-6">
		<div
			class="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-line-soft bg-white/90 px-4 py-3"
		>
			<div>
				<p class="type-body-strong text-ink">
					Class Teaching Plan holds the class-wide pacing. Class Session is today&apos;s live
					lesson.
				</p>
				<p class="type-caption text-ink/70">
					Start or end the live session here. Open Class Planning when you need to change units,
					pacing, resources, or the session design itself.
				</p>
			</div>
			<RouterLink
				:to="{ name: 'staff-class-planning', params: { studentGroup } }"
				class="if-action inline-flex"
			>
				Open Class Planning
			</RouterLink>
		</div>

		<ClassHubHeader
			:header="currentBundle.header"
			:now="currentBundle.now"
			:session="currentBundle.session"
			@start="handleStartSession"
			@quick-evidence="openQuickEvidence"
			@pick-student="openWheelPicker"
			@end="handleEndSession"
		/>

		<div v-if="visibleMessage" class="rounded-xl border border-slate-200 bg-white/90 px-4 py-3">
			<p class="type-caption text-ink/75">{{ visibleMessage }}</p>
		</div>

		<TodayList :items="currentBundle.today_items" @open="openTodayItem" />

		<FocusStudentsRow :students="currentBundle.focus_students" @open="openFocusStudent" />

		<StudentsGrid :students="currentBundle.students" @open="openStudent" />

		<MyTeachingPanel
			:notes="currentBundle.notes_preview"
			:tasks="currentBundle.task_items"
			@add-note="openStudentLogQuickCreate()"
			@open-note="openNote"
			@open-task="openTask"
		/>

		<ClassPulse :items="currentBundle.pulse_items" />

		<FollowUpsList :items="currentBundle.follow_up_items" @open="openFollowUp" />
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import { useOverlayStack } from '@/composables/useOverlayStack';
import { createClassHubService } from '@/lib/classHubService';
import type { ClassHubBundle } from '@/types/classHub';

import ClassHubHeader from '@/components/class-hub/ClassHubHeader.vue';
import TodayList from '@/components/class-hub/TodayList.vue';
import FocusStudentsRow from '@/components/class-hub/FocusStudentsRow.vue';
import StudentsGrid from '@/components/class-hub/StudentsGrid.vue';
import MyTeachingPanel from '@/components/class-hub/MyTeachingPanel.vue';
import ClassPulse from '@/components/class-hub/ClassPulse.vue';
import FollowUpsList from '@/components/class-hub/FollowUpsList.vue';

type HubServerMessageEntry = { message?: string };

const route = useRoute();
const overlay = useOverlayStack();
const service = createClassHubService();

const bundle = ref<ClassHubBundle | null>(null);
const actionMessage = ref('');
const loading = ref(false);

const studentGroup = computed(() => String(route.params.studentGroup || '').trim());
const queryDate = computed(() => (route.query.date ? String(route.query.date) : null));
const queryBlock = computed(() => {
	if (!route.query.block) return null;
	const parsed = Number(route.query.block);
	return Number.isFinite(parsed) ? parsed : null;
});

const emptyBundle = computed(() => buildEmptyBundle(studentGroup.value || '', queryDate.value));
const currentBundle = computed(() => bundle.value || emptyBundle.value);
const visibleMessage = computed(() => actionMessage.value || currentBundle.value.message || '');

function parseServerMessages(raw: unknown): string[] {
	if (typeof raw !== 'string' || !raw.trim()) return [];
	try {
		const parsed = JSON.parse(raw) as unknown[];
		if (!Array.isArray(parsed)) return [];
		return parsed
			.map(entry => {
				if (typeof entry === 'string') {
					try {
						const nested = JSON.parse(entry) as HubServerMessageEntry;
						if (nested && typeof nested.message === 'string') return nested.message;
					} catch {
						return entry;
					}
				}
				if (entry && typeof entry === 'object' && 'message' in entry) {
					return String((entry as HubServerMessageEntry).message || '');
				}
				return '';
			})
			.filter(Boolean);
	} catch {
		return [raw];
	}
}

function extractHubErrorMessage(error: unknown, fallback: string): string {
	if (!error || typeof error !== 'object') return fallback;
	const maybe = error as {
		message?: string;
		_server_messages?: string;
		response?: { message?: string; _server_messages?: string };
	};
	return (
		parseServerMessages(maybe.response?._server_messages)[0] ||
		parseServerMessages(maybe._server_messages)[0] ||
		maybe.response?.message ||
		maybe.message ||
		fallback
	);
}

function formatFallbackDateLabel(dateIso: string): string {
	const parsed = new Date(`${dateIso}T00:00:00`);
	if (Number.isNaN(parsed.getTime())) return dateIso;
	return parsed.toLocaleDateString(undefined, {
		weekday: 'short',
		day: 'numeric',
		month: 'short',
	});
}

async function loadBundle() {
	actionMessage.value = '';

	if (!studentGroup.value) {
		actionMessage.value = 'Student group is required to load the Class Hub.';
		bundle.value = emptyBundle.value;
		return;
	}

	loading.value = true;
	try {
		const payload = await service.getBundle({
			student_group: studentGroup.value,
			date: queryDate.value,
			block_number: queryBlock.value,
		});

		if (payload && typeof payload === 'object' && payload.header) {
			bundle.value = payload;
		} else {
			bundle.value = emptyBundle.value;
			actionMessage.value = 'Unable to load the Class Hub right now.';
		}
	} catch (err) {
		bundle.value = emptyBundle.value;
		actionMessage.value = extractHubErrorMessage(err, 'Unable to load the Class Hub right now.');
		console.error('[ClassHub] bundle load failed', err);
	} finally {
		loading.value = false;
	}
}

watch(
	() => [studentGroup.value, queryDate.value, queryBlock.value],
	() => {
		loadBundle();
	}
);

onMounted(async () => {
	await loadBundle();
});

function openStudent(student: ClassHubBundle['students'][number]) {
	overlay.open('class-hub-student-context', {
		student: student.student,
		student_name: student.student_name,
		student_group: currentBundle.value.header.student_group,
		class_session: currentBundle.value.session.class_session ?? null,
		can_create_student_log: currentBundle.value.permissions.can_create_student_log,
	});
}

function openFocusStudent(student: ClassHubBundle['focus_students'][number]) {
	openStudent({
		student: student.student,
		student_name: student.student_name,
		evidence_count_today: 0,
		signal: null,
		has_note_today: false,
	});
}

function openFollowUp(item: ClassHubBundle['follow_up_items'][number]) {
	const payload = item.payload || {};
	if (!payload.student) {
		actionMessage.value = 'Unable to open follow-up right now.';
		return;
	}
	openStudent({
		student: payload.student,
		student_name: payload.student_name || 'Student',
		evidence_count_today: 0,
		signal: null,
		has_note_today: false,
	});
}

function openTodayItem(item: ClassHubBundle['today_items'][number]) {
	const payload = item.payload || {};
	if (item.overlay === 'QuickCFU') {
		openQuickCFU();
		return;
	}
	if (item.overlay === 'QuickEvidence') {
		openQuickEvidence();
		return;
	}
	if (item.overlay === 'StudentContext') {
		if (!payload.student) {
			actionMessage.value = 'Select a student before opening context.';
			return;
		}
		openStudent({
			student: payload.student,
			student_name: payload.student_name || 'Student',
			evidence_count_today: 0,
			signal: null,
			has_note_today: false,
		});
		return;
	}
	if (item.overlay === 'TaskReview') {
		openTask({ id: item.id, title: item.label, status_label: '', overlay: 'TaskReview', payload });
	}
}

function openNote(note: ClassHubBundle['notes_preview'][number]) {
	const match = currentBundle.value.students.find(
		student => student.student_name === note.student_name
	);
	if (!match) {
		actionMessage.value = 'Student not found for that note.';
		return;
	}
	openStudent(match);
}

function openTask(task: ClassHubBundle['task_items'][number]) {
	overlay.open('class-hub-task-review', {
		title: task.title,
	});
}

function openStudentLogQuickCreate(student?: { student: string; student_name: string }) {
	actionMessage.value = '';

	if (!currentBundle.value.permissions.can_create_student_log) {
		actionMessage.value =
			'Your current Student Log permission does not allow note creation from the Hub.';
		return;
	}

	if (student) {
		overlay.open('student-log-create', {
			mode: 'attendance',
			sourceLabel: 'Class Hub',
			student: {
				id: student.student,
				label: student.student_name,
				image: null,
				meta: null,
			},
			student_group: {
				id: currentBundle.value.header.student_group,
				label: currentBundle.value.header.title,
			},
		});
		return;
	}

	overlay.open('student-log-create', {
		mode: 'home',
		sourceLabel: 'Class Hub',
	});
}

function openQuickEvidence() {
	overlay.open('class-hub-quick-evidence', {
		student_group: currentBundle.value.header.student_group,
		class_session: currentBundle.value.session.class_session ?? null,
		students: currentBundle.value.students.map(student => ({
			student: student.student,
			student_name: student.student_name,
		})),
	});
}

function openQuickCFU() {
	overlay.open('class-hub-quick-cfu', {
		student_group: currentBundle.value.header.student_group,
		class_session: currentBundle.value.session.class_session ?? null,
		students: currentBundle.value.students.map(student => ({
			student: student.student,
			student_name: student.student_name,
		})),
	});
}

function openWheelPicker() {
	overlay.open('class-hub-wheel-picker', {
		source_label: 'Class Hub',
		student_group: currentBundle.value.header.student_group,
		title: currentBundle.value.header.title,
		class_session: currentBundle.value.session.class_session ?? null,
		can_create_student_log: currentBundle.value.permissions.can_create_student_log,
		students: currentBundle.value.students.map(student => ({
			student: student.student,
			student_name: student.student_name,
		})),
		now: {
			date_iso: currentBundle.value.now.date_iso ?? queryDate.value,
			date_label: currentBundle.value.now.date_label,
			block_number: currentBundle.value.now.block_number ?? queryBlock.value,
			block_label: currentBundle.value.now.block_label ?? null,
			time_range: currentBundle.value.now.time_range ?? null,
			location: currentBundle.value.now.location ?? null,
		},
	});
}

async function handleStartSession() {
	actionMessage.value = '';
	if (!studentGroup.value) {
		actionMessage.value = 'Select a student group before starting.';
		return;
	}
	if (currentBundle.value.session.status === 'active') {
		actionMessage.value = 'This session is already in progress.';
		return;
	}
	try {
		const res = await service.startSession({
			student_group: studentGroup.value,
			date: queryDate.value,
			block_number: queryBlock.value,
		});
		await loadBundle();
		actionMessage.value = res.created
			? 'Started a new class session from the current unit.'
			: 'Session is now in progress.';
	} catch (err) {
		actionMessage.value = extractHubErrorMessage(err, 'Unable to start session right now.');
		console.error('[ClassHub] startSession failed', err);
	}
}

async function handleEndSession() {
	actionMessage.value = '';
	const classSession = currentBundle.value.session.class_session;
	if (!classSession) {
		actionMessage.value = currentBundle.value.message || 'Start a session before ending it.';
		return;
	}

	try {
		await service.endSession(classSession);
		await loadBundle();
		actionMessage.value = 'Session marked taught.';
	} catch (err) {
		actionMessage.value = extractHubErrorMessage(err, 'Unable to end session right now.');
		console.error('[ClassHub] endSession failed', err);
	}
}

function buildEmptyBundle(studentGroupValue: string, dateIso?: string | null): ClassHubBundle {
	const resolvedDate = dateIso || new Date().toISOString().slice(0, 10);
	return {
		message: null,
		header: {
			student_group: studentGroupValue,
			title: studentGroupValue || 'Class Hub',
			academic_year: null,
			course: null,
		},
		permissions: {
			can_create_student_log: false,
		},
		now: {
			date_iso: resolvedDate,
			date_label: formatFallbackDateLabel(resolvedDate),
			rotation_day_label: null,
			block_number: queryBlock.value,
			block_label: queryBlock.value ? `Block ${queryBlock.value}` : null,
			time_range: null,
			location: null,
		},
		session: {
			class_session: null,
			class_teaching_plan: null,
			title: null,
			session_status: null,
			session_date: null,
			unit_plan: null,
			status: 'none',
			live_success_criteria: null,
		},
		today_items: [],
		focus_students: [],
		students: [],
		notes_preview: [],
		task_items: [],
		pulse_items: [],
		follow_up_items: [],
	};
}
</script>
