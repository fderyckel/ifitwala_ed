<template>
	<div class="rounded-2xl bg-white p-3 shadow-sm transition hover:-translate-y-0.5">
		<a :href="`/desk/student/${student.student}`" target="_blank" rel="noopener" class="block">
			<img
				:src="thumb(student.student_image)"
				:alt="`Photo of ${student.student_name}`"
				loading="lazy"
				class="h-40 w-full rounded-xl object-cover"
				@error="onImgError($event, student.student_image)"
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
	birth_date?: string | null;
	has_ssg?: boolean;
};

const props = defineProps<{
	student: StudentRow;
}>();

const emit = defineEmits<{
	(e: 'open-ssg', s: StudentRow): void;
	(e: 'show-medical', payload: { student: StudentRow; note: string }): void;
}>();

/** -------- Thumbnail helpers (match server/client logic) -------- */
const DEFAULT_IMG = '/assets/ifitwala_ed/images/default_student_image.png';
function slugify(filename: string) {
	return filename
		.replace(/\.[^.]+$/, '')
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '_')
		.replace(/^_+|_+$/g, '');
}
function thumb(original_url?: string) {
	if (!original_url) return DEFAULT_IMG;
	if (original_url.startsWith('/files/gallery_resized/student/')) return original_url;
	if (!original_url.startsWith('/files/student/')) return DEFAULT_IMG;
	const base = slugify(original_url.split('/').pop() || '');
	return `/files/gallery_resized/student/thumb_${base}.webp`;
}
function onImgError(e: Event, fallback?: string) {
	const el = e.target as HTMLImageElement;
	el.onerror = null;
	el.src = fallback || DEFAULT_IMG;
}

/** -------- Birthday proximity (±5 days in current year) -------- */
const isBirthdaySoon = computed(() => {
	const iso = props.student.birth_date;
	if (!iso) return false;
	try {
		const b = new Date(iso);
		if (Number.isNaN(b.getTime())) return false;

		const today = new Date();
		const thisYear = new Date(today.getFullYear(), b.getMonth(), b.getDate());
		const diffDays = Math.floor((thisYear.getTime() - startOfDay(today).getTime()) / 86400000);
		return Math.abs(diffDays) <= 5;
	} catch {
		return false;
	}
});

const birthdayTitle = computed(() => {
	const iso = props.student.birth_date;
	if (!iso) return '';
	try {
		const b = new Date(iso);
		const today = new Date();
		const thisYear = new Date(today.getFullYear(), b.getMonth(), b.getDate());
		return thisYear.toLocaleDateString(undefined, {
			weekday: 'long',
			month: 'long',
			day: 'numeric',
		});
	} catch {
		return '';
	}
});

function startOfDay(d: Date) {
	return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}
</script>
