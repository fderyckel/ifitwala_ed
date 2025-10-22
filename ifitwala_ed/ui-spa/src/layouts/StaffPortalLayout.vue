<template>
	<div class="min-h-screen bg-slate-50 flex flex-col">
		<header class="bg-white border-b border-slate-200">
			<div class="mx-auto flex w-full max-w-6xl items-center justify-between gap-3 px-4 py-4 sm:px-6 lg:px-8">
				<h1 class="text-lg font-semibold tracking-tight text-slate-900">Staff Portal</h1>

				<a
					href="/app"
					class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-blue-300 hover:text-blue-600"
				>
					Switch to Desk
				</a>
			</div>
		</header>

		<main class="mx-auto flex w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
			<slot />
		</main>

		<footer class="border-t border-slate-200 bg-white">
			<div class="mx-auto max-w-6xl px-4 py-4 text-xs text-slate-500 sm:px-6 lg:px-8">
				© {{ year }} Staff Portal
			</div>
		</footer>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const year = computed(() => new Date().getFullYear())
</script>
