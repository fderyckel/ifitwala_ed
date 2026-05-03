<script setup lang="ts">
import type { AttendanceKpiSource, KpiTile, Snapshot } from './types';

const props = defineProps<{
	snapshot: Snapshot;
	avatarLoadFailed: boolean;
	kpiTiles: KpiTile[];
}>();

const emit = defineEmits<{
	(e: 'avatar-error'): void;
	(e: 'attendance-kpi-source', value: AttendanceKpiSource): void;
}>();
</script>

<template>
	<section
		class="rounded-2xl border border-slate-200 bg-[rgb(var(--surface-rgb)/0.92)] px-4 py-5 shadow-sm"
	>
		<div class="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
			<div class="flex gap-4">
				<div
					class="flex h-16 w-16 items-center justify-center overflow-hidden rounded-2xl bg-slate-100 text-lg font-semibold text-slate-600"
				>
					<img
						v-if="props.snapshot.identity.photo && !props.avatarLoadFailed"
						:src="props.snapshot.identity.photo"
						alt="Student avatar"
						class="h-full w-full object-cover"
						@error="emit('avatar-error')"
					/>
					<span v-else>
						{{
							props.snapshot.identity.full_name?.[0] ||
							props.snapshot.meta.student_name?.[0] ||
							'?'
						}}
					</span>
				</div>
				<div class="space-y-1 text-sm text-slate-700">
					<div class="flex flex-wrap items-center gap-2">
						<h2 class="text-lg font-semibold text-slate-900">
							{{
								props.snapshot.identity.full_name || props.snapshot.meta.student_name || 'Student'
							}}
						</h2>
						<span
							v-if="props.snapshot.identity.cohort"
							class="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700"
						>
							{{ props.snapshot.identity.cohort }}
						</span>
					</div>
					<p class="text-xs text-slate-500">
						{{
							props.snapshot.identity.program_enrollment?.program || props.snapshot.meta.program
						}}
						<span v-if="props.snapshot.identity.school?.label">
							· {{ props.snapshot.identity.school?.label }}
						</span>
					</p>
					<p class="text-xs text-slate-500">
							<span v-if="props.snapshot.identity.student_age">
								Age {{ props.snapshot.identity.student_age }}
							</span>
							<span v-else-if="props.snapshot.identity.age">Age {{ props.snapshot.identity.age }}</span>
							<span
								v-if="
									(props.snapshot.identity.student_age || props.snapshot.identity.age) &&
									props.snapshot.identity.gender
								"
							>
								·
							</span>
						<span v-if="props.snapshot.identity.gender">{{ props.snapshot.identity.gender }}</span>
					</p>
				</div>
			</div>
			<div class="flex flex-col gap-2">
				<div class="grid grid-cols-2 gap-3 md:grid-cols-4">
					<div
						v-for="tile in props.kpiTiles"
						:key="tile.label"
						:class="[
							'overflow-hidden rounded-xl border px-3 py-3 shadow-sm',
							'border-[rgb(var(--border-rgb)/0.65)] bg-[rgb(var(--surface-rgb)/0.92)]',
							tile.clickable
								? 'cursor-pointer hover:border-[#1f7a45] hover:bg-[rgb(var(--surface-rgb))]'
								: '',
						]"
						@click="tile.onClick && tile.onClick()"
					>
						<div class="flex items-center justify-between gap-2">
							<p class="text-[11px] font-semibold uppercase tracking-wide text-ink/70">
								{{ tile.label }}
							</p>
						</div>

						<p class="mt-1 text-sm font-semibold text-ink">{{ tile.value }}</p>

						<div
							v-if="tile.sourceToggle?.active"
							class="mt-1 flex flex-wrap items-center gap-1"
							@click.stop
						>
							<button
								v-for="opt in tile.sourceToggle.options"
								:key="opt.id"
								type="button"
								class="chip inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold transition"
								:class="[opt.id === tile.sourceToggle.active ? 'chip-active' : '']"
								@click="emit('attendance-kpi-source', opt.id)"
							>
								{{ opt.label }}
							</button>
						</div>

						<p class="mt-1 text-[11px] text-ink/70">{{ tile.sub }}</p>
					</div>
				</div>
			</div>
		</div>
	</section>
</template>
