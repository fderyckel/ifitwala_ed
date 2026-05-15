<template>
	<div class="rounded-2xl bg-white p-3 shadow-sm transition hover:-translate-y-0.5">
		<a :href="`/desk/student/${student.student}`" target="_blank" rel="noopener" class="block">
			<img
				:src="student.student_image || DEFAULT_IMG"
				:alt="`Photo of ${student.student_name}`"
				loading="lazy"
				class="h-40 w-full rounded-xl object-cover"
				@error="onImgError"
			/>
		</a>

		<!-- Name row + icons -->
		<div class="mt-2 flex items-center gap-1">
			<a
				:href="`/desk/student/${student.student}`"
				target="_blank"
				rel="noopener"
				class="truncate text-sm font-semibold leading-tight hover:underline"
			>
				{{ student.student_name }}
			</a>

			<!-- SSG clickable badge -->
			<button
				v-if="student.has_ssg"
				type="button"
				class="ml-1 inline-flex items-center"
				title="Support guidance available"
				@click.stop="emit('open-ssg', student)"
			>
				<Badge variant="subtle">SSG</Badge>
			</button>

			<!-- Medical note icon (generic medical cross in a circle) -->
			<button
				v-if="student.medical_info"
				type="button"
				class="ml-1 inline-flex items-center text-red-600"
				title="Health note available"
				aria-label="Health note available"
				@click.stop="emit('show-medical', { student, note: student.medical_info })"
			>
				<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
					<circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2" />
					<path d="M12 8v8M8 12h8" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
				</svg>
			</button>

			<!-- Birthday icon (if within ±5 days this year) -->
			<span
				v-if="isBirthdaySoon"
				class="ml-1 inline-flex items-center text-amber-500"
				:title="birthdayTitle"
				aria-label="Upcoming birthday"
				>🎂</span
			>
		</div>

		<!-- Preferred name -->
		<div v-if="student.preferred_name" class="text-xs text-gray-500">
			{{ student.preferred_name }}
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Badge } from 'frappe-ui';

type StudentRow = {
	student: string;
	student_name: string;
	preferred_name?: string;
	student_image?: string;
	medical_info?: string;
	student_age?: string | null;
	birthday_in_window?: boolean;
	birthday_today?: boolean;
	birthday_label?: string | null;
	has_ssg?: boolean;
};

const props = defineProps<{
	student: StudentRow;
}>();

const emit = defineEmits<{
	(e: 'open-ssg', s: StudentRow): void;
	(e: 'show-medical', payload: { student: StudentRow; note: string }): void;
}>();

/** -------- Image fallback helper -------- */
const DEFAULT_IMG = '/assets/ifitwala_ed/images/default_student_image.png';
function onImgError(e: Event, fallback?: string) {
	const el = e.target as HTMLImageElement;
	el.onerror = null;
	el.src = fallback || DEFAULT_IMG;
}

const isBirthdaySoon = computed(() => {
	return !!props.student.birthday_in_window;
});

const birthdayTitle = computed(() => {
	if (props.student.birthday_today) return 'Birthday today';
	if (props.student.birthday_label) return `Birthday on ${props.student.birthday_label}`;
	return 'Birthday';
});
</script>
