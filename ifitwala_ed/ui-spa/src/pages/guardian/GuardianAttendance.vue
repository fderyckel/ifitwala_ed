<!-- ifitwala_ed/ui-spa/src/pages/guardian/GuardianAttendance.vue -->
<template>
	<div class="portal-page">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
				<div>
					<p class="type-overline text-ink/60">Guardian Portal</p>
					<h1 class="type-h1 text-ink">Family Attendance</h1>
					<p class="type-body text-ink/70">
						Check daily attendance for your child or children in one place, then filter by child
						when needed.
					</p>
				</div>
				<div class="grid gap-3 sm:grid-cols-3">
					<label class="space-y-1">
						<span class="type-caption text-ink/60">Child filter</span>
						<select
							v-model="selectedStudent"
							class="w-full rounded-xl border border-line-soft bg-white px-3 py-2 type-body text-ink"
						>
							<option value="">All linked children</option>
							<option v-for="child in children" :key="child.student" :value="child.student">
								{{ child.full_name }}
							</option>
						</select>
					</label>
					<label class="space-y-1">
						<span class="type-caption text-ink/60">Window</span>
						<select
							v-model.number="selectedDays"
							class="w-full rounded-xl border border-line-soft bg-white px-3 py-2 type-body text-ink"
						>
							<option :value="30">30 days</option>
							<option :value="60">60 days</option>
							<option :value="90">90 days</option>
						</select>
					</label>
					<div class="flex items-end">
						<button
							type="button"
							class="if-action w-full"
							:disabled="loading"
							@click="loadSnapshot"
						>
							Refresh
						</button>
					</div>
				</div>
			</div>
		</header>

		<section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
			<article class="card-surface p-4" :class="summaryCardClass('tracked')">
				<p class="type-caption">Tracked days</p>
				<p class="type-h3" :class="summaryValueClass('tracked')">{{ counts.tracked_days }}</p>
			</article>
			<article class="card-surface p-4" :class="summaryCardClass('present')">
				<p class="type-caption">On-track days</p>
				<p class="type-h3" :class="summaryValueClass('present')">{{ counts.present_days }}</p>
			</article>
			<article class="card-surface p-4" :class="summaryCardClass('late')">
				<p class="type-caption">Late days</p>
				<p class="type-h3" :class="summaryValueClass('late')">{{ counts.late_days }}</p>
			</article>
			<article class="card-surface p-4" :class="summaryCardClass('absence')">
				<p class="type-caption">Absence days</p>
				<p class="type-h3" :class="summaryValueClass('absence')">{{ counts.absence_days }}</p>
			</article>
		</section>

		<section class="card-surface p-5">
			<h2 class="mb-3 type-h3 text-ink">How to read this view</h2>
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
				<div
					class="rounded-xl border-2 bg-moss/10 p-4"
					style="border-color: rgb(var(--moss-rgb) / 0.72)"
				>
					<div
						class="mb-2 h-8 w-8 rounded-lg border bg-moss/20"
						style="border-color: rgb(var(--moss-rgb) / 0.52)"
					/>
					<p class="text-lg font-semibold tracking-tight" style="color: rgb(var(--moss-rgb) / 1)">
						On track
					</p>
					<p class="type-body text-ink/75">Attendance is recorded as present for that day.</p>
				</div>
				<div
					class="rounded-xl border-2 border-[rgb(var(--jacaranda-rgb)/0.55)] bg-jacaranda/10 p-4"
				>
					<div class="mb-2 h-8 w-8 rounded-lg border border-jacaranda/40 bg-jacaranda/20" />
					<p class="text-lg font-semibold tracking-tight text-jacaranda">Late or tardy</p>
					<p class="type-body text-ink/75">
						The day includes a late arrival or another tardy attendance signal.
					</p>
				</div>
				<div class="rounded-xl border-2 border-[rgb(var(--flame-rgb)/0.55)] bg-flame/10 p-4">
					<div class="mb-2 h-8 w-8 rounded-lg border border-flame/40 bg-flame/20" />
					<p class="text-lg font-semibold tracking-tight text-flame">Absent</p>
					<p class="type-body text-ink/75">
						The day includes an absence or other non-present code.
					</p>
				</div>
				<div class="rounded-xl border-2 border-line-soft bg-surface-soft p-4">
					<div class="mb-2 h-8 w-8 rounded-lg border border-dashed border-line-soft bg-white/70" />
					<p class="text-lg font-semibold tracking-tight text-ink">No record</p>
					<p class="type-body text-ink/75">
						No attendance record is available for that date in this window.
					</p>
				</div>
			</div>
		</section>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading family attendance...</p>
		</section>

		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">Could not load family attendance.</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<section v-else-if="!students.length" class="card-surface p-5">
			<p class="type-body text-ink/70">
				No linked children are available in this attendance view.
			</p>
		</section>

		<section v-else class="space-y-4">
			<article v-for="student in students" :key="student.student" class="card-surface p-5">
				<div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(34rem,38rem)] lg:items-start">
					<div>
						<h2 class="type-h3 text-ink">{{ student.student_name }}</h2>
						<p class="type-caption text-ink/60">
							Last {{ selectedDays }} days from {{ filters.start_date }} to {{ filters.end_date }}
						</p>
					</div>
					<div class="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:w-full">
						<div class="rounded-xl border px-4 py-3" :class="summaryCardClass('tracked')">
							<p class="text-sm font-semibold text-ink/80 sm:text-base">Tracked</p>
							<p
								class="mt-1 text-xl font-semibold sm:text-2xl"
								:class="summaryValueClass('tracked')"
							>
								{{ student.summary.tracked_days }}
							</p>
						</div>
						<div class="rounded-xl border px-4 py-3" :class="summaryCardClass('present')">
							<p class="text-sm font-semibold text-ink/80 sm:text-base">On track</p>
							<p
								class="mt-1 text-xl font-semibold sm:text-2xl"
								:class="summaryValueClass('present')"
							>
								{{ student.summary.present_days }}
							</p>
						</div>
						<div class="rounded-xl border px-4 py-3" :class="summaryCardClass('late')">
							<p class="text-sm font-semibold text-ink/80 sm:text-base">Late</p>
							<p class="mt-1 text-xl font-semibold sm:text-2xl" :class="summaryValueClass('late')">
								{{ student.summary.late_days }}
							</p>
						</div>
						<div class="rounded-xl border px-4 py-3" :class="summaryCardClass('absence')">
							<p class="text-sm font-semibold text-ink/80 sm:text-base">Absent</p>
							<p
								class="mt-1 text-xl font-semibold sm:text-2xl"
								:class="summaryValueClass('absence')"
							>
								{{ student.summary.absence_days }}
							</p>
						</div>
					</div>
				</div>

				<div v-if="!student.days.length" class="mt-4 type-body text-ink/70">
					No attendance records in this window.
				</div>

				<div v-else class="mt-5 space-y-5">
					<div class="grid gap-4 xl:grid-cols-2">
						<section
							v-for="month in calendarMonths(student)"
							:key="month.key"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<div class="mb-3 flex items-center justify-between">
								<h3 class="type-body-strong text-ink">{{ month.label }}</h3>
								<p class="type-caption text-ink/60">{{ month.activeDays }} tracked days</p>
							</div>

							<div class="mb-2 grid grid-cols-7 gap-2">
								<p
									v-for="weekday in weekdayLabels"
									:key="`${month.key}-${weekday}`"
									class="text-center type-caption text-ink/60"
								>
									{{ weekday }}
								</p>
							</div>

							<div class="grid grid-cols-7 gap-2">
								<template v-for="(cell, index) in month.cells" :key="`${month.key}-${index}`">
									<div
										v-if="!cell"
										class="aspect-square rounded-lg border-2 border-dashed border-line-soft/70 bg-white/50"
										aria-hidden="true"
									/>
									<button
										v-else
										type="button"
										class="aspect-square rounded-lg border-2 px-2 py-1 text-left transition focus:outline-none focus:ring-2 focus:ring-jacaranda"
										:class="cellClass(student.student, cell)"
										:style="cellStyle(cell)"
										:aria-label="cellAriaLabel(student.student_name, cell)"
										:aria-haspopup="cell.hasDetails ? 'dialog' : undefined"
										:aria-pressed="isSelectedCell(student.student, cell.date) ? 'true' : 'false'"
										:disabled="!cell.hasDetails"
										@click="selectDay(student.student, student.student_name, cell.date)"
									>
										<span class="text-xs font-semibold">{{ cell.dayNumber }}</span>
									</button>
								</template>
							</div>
						</section>
					</div>
				</div>
			</article>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { useOverlayStack } from '@/composables/useOverlayStack';
import { getGuardianAttendanceSnapshot } from '@/lib/services/guardianAttendance/guardianAttendanceService';

import type {
	GuardianAttendanceDay,
	GuardianAttendanceStudent,
	Response as GuardianAttendanceSnapshot,
} from '@/types/contracts/guardian/get_guardian_attendance_snapshot';

type CalendarCell = {
	date: string;
	dayNumber: number;
	state: GuardianAttendanceDay['state'] | 'none';
	hasDetails: boolean;
};

type CalendarMonth = {
	key: string;
	label: string;
	activeDays: number;
	cells: Array<CalendarCell | null>;
};

type SummaryTone = 'tracked' | 'present' | 'late' | 'absence';

const weekdayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const overlay = useOverlayStack();

const loading = ref(true);
const errorMessage = ref('');
const snapshot = ref<GuardianAttendanceSnapshot | null>(null);
const selectedStudent = ref('');
const selectedDays = ref(60);
const selectedCell = ref<{ student: string; date: string } | null>(null);
const attendanceDetailOverlayId = ref<string | null>(null);

const children = computed(() => snapshot.value?.family.children ?? []);
const students = computed<GuardianAttendanceStudent[]>(() => snapshot.value?.students ?? []);
const counts = computed(
	() =>
		snapshot.value?.counts ?? {
			tracked_days: 0,
			present_days: 0,
			late_days: 0,
			absence_days: 0,
		}
);
const filters = computed(
	() =>
		snapshot.value?.meta.filters ?? {
			student: '',
			days: 60,
			start_date: '',
			end_date: '',
		}
);

const monthStarts = computed(() => {
	if (!filters.value.start_date || !filters.value.end_date) return [];
	return buildMonthStarts(filters.value.start_date, filters.value.end_date);
});

const studentDayMaps = computed(() => {
	const out = new Map<string, Map<string, GuardianAttendanceDay>>();
	for (const student of students.value) {
		out.set(student.student, new Map(student.days.map(day => [day.date, day])));
	}
	return out;
});

async function loadSnapshot() {
	closeDayOverlay(true);
	loading.value = true;
	errorMessage.value = '';
	try {
		snapshot.value = await getGuardianAttendanceSnapshot({
			student: selectedStudent.value || undefined,
			days: selectedDays.value,
		});
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		errorMessage.value = message || 'Unknown error';
	} finally {
		loading.value = false;
	}
}

function calendarMonths(student: GuardianAttendanceStudent): CalendarMonth[] {
	const dayMap =
		studentDayMaps.value.get(student.student) ?? new Map<string, GuardianAttendanceDay>();
	return monthStarts.value.map(monthStart => buildCalendarMonth(monthStart, dayMap));
}

function selectDay(student: string, studentName: string, date: string) {
	const day = studentDayMaps.value.get(student)?.get(date);
	if (!day || !day.details.length) return;

	closeDayOverlay();
	selectedCell.value = { student, date };
	attendanceDetailOverlayId.value = overlay.open('guardian-attendance-day', {
		studentName,
		day,
		onClose: handleAttendanceDetailClosed,
	});
}

function isSelectedCell(student: string, date: string): boolean {
	return selectedCell.value?.student === student && selectedCell.value?.date === date;
}

function closeDayOverlay(clearSelection = false) {
	const overlayId = attendanceDetailOverlayId.value;
	attendanceDetailOverlayId.value = null;
	if (overlayId) {
		overlay.close(overlayId);
	}
	if (clearSelection) {
		selectedCell.value = null;
	}
}

function handleAttendanceDetailClosed() {
	attendanceDetailOverlayId.value = null;
	selectedCell.value = null;
}

function cellClass(student: string, cell: CalendarCell): string {
	const selected = isSelectedCell(student, cell.date) ? 'ring-2 ring-jacaranda' : '';
	if (cell.state === 'present') {
		return `bg-moss/15 text-ink ${selected}`.trim();
	}
	if (cell.state === 'late') {
		return `border-jacaranda/40 bg-jacaranda/12 text-jacaranda ${selected}`.trim();
	}
	if (cell.state === 'absence') {
		return `border-flame/45 bg-flame/12 text-flame ${selected}`.trim();
	}
	return `border-line-soft bg-white text-ink/45 ${selected}`.trim();
}

function cellStyle(cell: CalendarCell): Record<string, string> | undefined {
	if (cell.state === 'present') {
		return {
			borderColor: 'rgb(var(--moss-rgb) / 0.72)',
		};
	}
	return undefined;
}

function cellAriaLabel(studentName: string, cell: CalendarCell): string {
	if (cell.state === 'none') {
		return `${studentName} on ${cell.date}: no attendance record`;
	}
	return `${studentName} on ${cell.date}: ${detailStateLabel(cell.state)}`;
}

function detailStateLabel(state: GuardianAttendanceDay['state']): string {
	if (state === 'late') return 'Late or tardy';
	if (state === 'absence') return 'Absence recorded';
	return 'Present';
}

function summaryCardClass(tone: SummaryTone): string {
	if (tone === 'tracked') return 'border-jacaranda/20 bg-jacaranda/5';
	if (tone === 'present') return 'border-moss/30 bg-moss/10';
	if (tone === 'late') return 'border-jacaranda/30 bg-jacaranda/10';
	return 'border-flame/30 bg-flame/10';
}

function summaryValueClass(tone: SummaryTone): string {
	if (tone === 'tracked') return 'text-jacaranda';
	if (tone === 'present') return 'text-ink';
	if (tone === 'late') return 'text-jacaranda';
	return 'text-flame';
}

function buildMonthStarts(startDate: string, endDate: string): Date[] {
	const out: Date[] = [];
	let cursor = startOfMonth(parseIsoDate(startDate));
	const finalMonth = startOfMonth(parseIsoDate(endDate));
	while (cursor <= finalMonth) {
		out.push(new Date(cursor));
		cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
	}
	return out;
}

function buildCalendarMonth(
	monthStart: Date,
	dayMap: Map<string, GuardianAttendanceDay>
): CalendarMonth {
	const cells: Array<CalendarCell | null> = [];
	const offset = mondayIndex(monthStart);
	for (let index = 0; index < offset; index += 1) {
		cells.push(null);
	}

	const year = monthStart.getFullYear();
	const month = monthStart.getMonth();
	const lastDay = new Date(year, month + 1, 0).getDate();
	let activeDays = 0;

	for (let dayNumber = 1; dayNumber <= lastDay; dayNumber += 1) {
		const currentDate = new Date(year, month, dayNumber);
		const isoDate = formatIsoDate(currentDate);
		const entry = dayMap.get(isoDate);
		if (entry) activeDays += 1;
		cells.push({
			date: isoDate,
			dayNumber,
			state: entry?.state ?? 'none',
			hasDetails: Boolean(entry?.details?.length),
		});
	}

	while (cells.length % 7 !== 0) {
		cells.push(null);
	}

	return {
		key: `${year}-${String(month + 1).padStart(2, '0')}`,
		label: new Intl.DateTimeFormat(undefined, {
			month: 'long',
			year: 'numeric',
		}).format(monthStart),
		activeDays,
		cells,
	};
}

function parseIsoDate(value: string): Date {
	const [year, month, day] = value.split('-').map(Number);
	return new Date(year, month - 1, day);
}

function startOfMonth(value: Date): Date {
	return new Date(value.getFullYear(), value.getMonth(), 1);
}

function formatIsoDate(value: Date): string {
	const year = value.getFullYear();
	const month = String(value.getMonth() + 1).padStart(2, '0');
	const day = String(value.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
}

function mondayIndex(value: Date): number {
	return (value.getDay() + 6) % 7;
}

watch([selectedStudent, selectedDays], () => {
	void loadSnapshot();
});

onMounted(() => {
	void loadSnapshot();
});

onBeforeUnmount(() => {
	closeDayOverlay(true);
});
</script>
