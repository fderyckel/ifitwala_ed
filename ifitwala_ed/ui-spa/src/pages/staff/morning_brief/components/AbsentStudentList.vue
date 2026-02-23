<template>
	<div class="paper-card p-5 border-l-4 border-l-flame">
		<div class="flex items-center justify-between mb-4">
			<h3 class="section-header flex items-center gap-2 text-flame">
				<FeatherIcon name="user-x" class="h-3 w-3" /> Absences Today
			</h3>
			<span class="text-xs font-bold bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
				{{ students.length }}
			</span>
		</div>

		<div class="space-y-3 max-h-96 overflow-y-auto custom-scrollbar pr-1">
			<div
				v-for="(stu, idx) in students"
				:key="idx"
				class="flex items-start gap-3 p-2 rounded-lg hover:bg-slate-50 transition-colors"
			>
				<div
					class="h-10 w-10 rounded-full bg-slate-100 overflow-hidden flex-shrink-0 border border-slate-200"
				>
					<img
						v-if="stu.student_image"
						:src="stu.student_image"
						class="h-full w-full object-cover"
					/>
					<div
						v-else
						class="h-full w-full flex items-center justify-center text-sm font-bold text-slate-400"
					>
						{{ stu.student_name.substring(0, 2) }}
					</div>
				</div>

				<div class="flex-1 min-w-0">
					<div class="flex justify-between items-start">
						<h4 class="text-sm font-bold text-ink truncate">{{ stu.student_name }}</h4>
						<span
							class="text-[10px] font-bold px-1.5 py-0.5 rounded border"
							:style="{
								borderColor: stu.status_color,
								color: stu.status_color,
								backgroundColor: stu.status_color + '10',
							}"
						>
							{{ stu.attendance_code }}
						</span>
					</div>

					<p class="text-xs text-slate-500 mt-0.5 flex items-center gap-1">
						<FeatherIcon name="users" class="h-3 w-3" /> {{ stu.student_group }}
					</p>

					<div
						v-if="stu.remark"
						class="mt-1.5 text-xs text-slate-600 bg-slate-100 p-1.5 rounded italic border-l-2 border-slate-300"
					>
						"{{ stu.remark }}"
					</div>
					<div v-else class="mt-1.5 text-[10px] text-red-500 font-medium flex items-center gap-1">
						<FeatherIcon name="alert-circle" class="h-3 w-3" /> Unexplained
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { FeatherIcon } from 'frappe-ui';

defineProps({
	students: {
		type: Array,
		default: () => [],
	},
});
</script>
