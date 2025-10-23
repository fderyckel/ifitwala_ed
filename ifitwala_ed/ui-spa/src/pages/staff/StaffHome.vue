<!-- ifitwala_ed/ifitwala_ed/ui-spa/src/pages/staff/schedule/StaffHome.vue -->
<template>
	<div class="flex w-full flex-col items-center justify-center gap-6 text-center">
		<div class="space-y-2">
			<h2 class="text-2xl font-semibold text-slate-900">Welcome to the Staff Portal</h2>
			<p class="max-w-md text-sm text-slate-500">
				Start by opening the Student Groups workspace or jump back to the Desk for the traditional experience.
			</p>
		</div>

		<div class="flex flex-wrap items-center justify-center gap-3">
			<RouterLink
				:to="{ name: 'staff-student-groups' }"
				class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
			>
				Open Student Groups
			</RouterLink>

			<a
				href="/app"
				class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-blue-300 hover:text-blue-600"
			>
				Switch to Desk
			</a>
		</div>
	</div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>
