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
				<div class="rounded-xl border border-moss/30 bg-moss/10 p-4">
					<div class="mb-2 h-8 w-8 rounded-lg border border-moss/40 bg-moss/20" />
					<p class="type-body-strong text-moss">Moss</p>
					<p class="type-caption text-ink/70">Attendance is recorded as present for that day.</p>
				</div>
				<div class="rounded-xl border border-jacaranda/30 bg-jacaranda/10 p-4">
					<div class="mb-2 h-8 w-8 rounded-lg border border-jacaranda/40 bg-jacaranda/20" />
					<p class="type-body-strong text-jacaranda">Jacaranda</p>
					<p class="type-caption text-ink/70">
						The day includes a late arrival or another tardy attendance signal.
					</p>
				</div>
				<div class="rounded-xl border border-flame/30 bg-flame/10 p-4">
					<div class="mb-2 h-8 w-8 rounded-lg border border-flame/40 bg-flame/20" />
					<p class="type-body-strong text-flame">Flame</p>
					<p class="type-caption text-ink/70">
						The day includes an absence or other non-present code.
					</p>
				</div>
				<div class="rounded-xl border border-line-soft bg-surface-soft p-4">
					<div class="mb-2 h-8 w-8 rounded-lg border border-dashed border-line-soft bg-white/70" />
					<p class="type-body-strong text-ink">Grey</p>
					<p class="type-caption text-ink/70">
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
						<div class="rounded-xl border px-3 py-2" :class="summaryCardClass('tracked')">
							<p class="type-caption">Tracked</p>
							<p class="type-body-strong" :class="summaryValueClass('tracked')">
								{{ student.summary.tracked_days }}
							</p>
						</div>
						<div class="rounded-xl border px-3 py-2" :class="summaryCardClass('present')">
							<p class="type-caption">On track</p>
							<p class="type-body-strong" :class="summaryValueClass('present')">
								{{ student.summary.present_days }}
							</p>
						</div>
						<div class="rounded-xl border px-3 py-2" :class="summaryCardClass('late')">
							<p class="type-caption">Late</p>
							<p class="type-body-strong" :class="summaryValueClass('late')">
								{{ student.summary.late_days }}
							</p>
						</div>
						<div class="rounded-xl border px-3 py-2" :class="summaryCardClass('absence')">
							<p class="type-caption">Absent</p>
							<p class="type-body-strong" :class="summaryValueClass('absence')">
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
										class="aspect-square rounded-lg border border-dashed border-line-soft/60 bg-white/50"
										aria-hidden="true"
									/>
									<button
										v-else
										type="button"
										class="aspect-square rounded-lg border px-2 py-1 text-left transition focus:outline-none focus:ring-2 focus:ring-jacaranda"
										:class="cellClass(student.student, cell)"
										:aria-label="cellAriaLabel(student.student_name, cell)"
										:aria-pressed="isSelectedCell(student.student, cell.date) ? 'true' : 'false'"
										:disabled="!cell.hasDetails"
										@click="selectDay(student.student, cell.date)"
									>
										<span class="text-xs font-semibold">{{ cell.dayNumber }}</span>
									</button>
								</template>
							</div>
						</section>
					</div>

					<section
						v-if="selectedDay(student.student)"
						class="rounded-2xl border border-line-soft bg-white p-4"
					>
						<div class="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
							<div>
								<h3 class="type-body-strong text-ink">
									{{ student.student_name }} on
									{{ formatDetailDate(selectedDay(student.student)?.date || '') }}
								</h3>
								<p class="type-caption text-ink/60">
									{{ selectedDay(student.student)?.details.length || 0 }} attendance detail(s)
								</p>
							</div>
							<p
								class="rounded-full px-3 py-1 type-caption"
								:class="detailStateClass(selectedDay(student.student)?.state || 'present')"
							>
								{{ detailStateLabel(selectedDay(student.student)?.state || 'present') }}
							</p>
						</div>

						<ul class="space-y-3">
							<li
								v-for="detail in selectedDay(student.student)?.details || []"
								:key="detail.attendance"
								class="rounded-xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-body-strong text-ink">{{ detail.attendance_code_name }}</p>
								<p class="type-caption text-ink/60">
									{{ detail.whole_day ? 'Whole day' : detail.time || 'Time not recorded' }}
									<span v-if="detail.course"> - {{ detail.course }}</span>
									<span v-if="detail.location"> - {{ detail.location }}</span>
								</p>
								<p v-if="detail.remark" class="mt-2 type-body text-ink/80">{{ detail.remark }}</p>
							</li>
						</ul>
					</section>
				</div>
			</article>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

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

const loading = ref(true);
const errorMessage = ref('');
const snapshot = ref<GuardianAttendanceSnapshot | null>(null);
const selectedStudent = ref('');
const selectedDays = ref(60);
const selectedCell = ref<{ student: string; date: string } | null>(null);

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
	loading.value = true;
	errorMessage.value = '';
	try {
		snapshot.value = await getGuardianAttendanceSnapshot({
			student: selectedStudent.value || undefined,
			days: selectedDays.value,
		});
		if (selectedCell.value && !selectedDay(selectedCell.value.student)) {
			selectedCell.value = null;
		}
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

function selectDay(student: string, date: string) {
	selectedCell.value = { student, date };
}

function isSelectedCell(student: string, date: string): boolean {
	return selectedCell.value?.student === student && selectedCell.value?.date === date;
}

function selectedDay(student: string): GuardianAttendanceDay | null {
	if (selectedCell.value?.student !== student) return null;
	return studentDayMaps.value.get(student)?.get(selectedCell.value.date) ?? null;
}

function cellClass(student: string, cell: CalendarCell): string {
	const selected = isSelectedCell(student, cell.date) ? 'ring-2 ring-jacaranda' : '';
	if (cell.state === 'present') {
		return `border-moss/35 bg-moss/15 text-ink ${selected}`.trim();
	}
	if (cell.state === 'late') {
		return `border-jacaranda/40 bg-jacaranda/12 text-jacaranda ${selected}`.trim();
	}
	if (cell.state === 'absence') {
		return `border-flame/45 bg-flame/12 text-flame ${selected}`.trim();
	}
	return `border-line-soft bg-white text-ink/45 ${selected}`.trim();
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

function detailStateClass(state: GuardianAttendanceDay['state']): string {
	if (state === 'late') return 'bg-jacaranda/12 text-jacaranda';
	if (state === 'absence') return 'bg-flame/12 text-flame';
	return 'bg-moss/15 text-ink';
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

function formatDetailDate(value: string): string {
	if (!value) return '';
	return new Intl.DateTimeFormat(undefined, {
		weekday: 'long',
		day: 'numeric',
		month: 'long',
		year: 'numeric',
	}).format(parseIsoDate(value));
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
	selectedCell.value = null;
	void loadSnapshot();
});

onMounted(() => {
	void loadSnapshot();
});
</script>
