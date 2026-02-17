<!-- ifitwala_ed/ui-spa/src/layouts/AdmissionsLayout.vue -->

<template>
	<div
		class="min-h-screen flex flex-col text-ink bg-gradient-to-b from-sand/90 via-surface-soft/95 to-white bg-[radial-gradient(circle_at_10%_0,rgb(var(--leaf-rgb)/0.10),transparent_55%)]"
	>
		<header class="border-b border-border/70 bg-white/85 backdrop-blur sticky top-0 z-30">
			<div class="mx-auto max-w-6xl px-4 py-4 sm:px-6 lg:px-8">
				<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
					<div>
						<p class="type-caption text-ink/60">{{ __('Admissions Portal') }}</p>
						<p class="type-h2 text-ink">
							{{ applicantName || __('Loading applicant…') }}
						</p>
					</div>
					<div class="flex flex-col items-start gap-1 sm:items-end">
						<div class="flex items-center gap-2">
							<span class="type-caption text-ink/60">{{ __('Status') }}</span>
							<span
								class="rounded-full border border-border/70 bg-surface px-3 py-1 type-caption text-ink"
							>
								{{ portalStatusLabel || __('—') }}
							</span>
						</div>
						<a
							href="/?cmd=web_logout"
							class="type-caption text-ink/70 hover:text-ink underline underline-offset-4"
						>
							{{ __('Log out') }}
						</a>
					</div>
				</div>
			</div>
		</header>

		<div class="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8 flex-1">
			<div
				v-if="loading"
				class="rounded-3xl border border-border/70 bg-white px-6 py-10 shadow-soft"
			>
				<div class="flex items-center gap-3">
					<Spinner class="h-5 w-5" />
					<p class="type-body-strong text-ink">{{ __('Loading your application…') }}</p>
				</div>
			</div>

			<div
				v-else-if="error"
				class="rounded-3xl border border-rose-200 bg-rose-50 px-6 py-6 shadow-soft"
			>
				<p class="type-body-strong text-rose-900">{{ __('Unable to load admissions portal') }}</p>
				<p class="mt-2 type-caption text-rose-900/80 whitespace-pre-wrap">{{ error }}</p>
				<button
					type="button"
					class="mt-4 inline-flex items-center rounded-full border border-rose-200 bg-white px-4 py-2 type-caption text-rose-900"
					@click="refresh"
				>
					{{ __('Try again') }}
				</button>
			</div>

			<div v-else class="flex flex-col gap-6 lg:flex-row">
				<aside class="lg:w-60">
					<nav class="rounded-3xl border border-border/70 bg-white p-4 shadow-soft">
						<p class="type-caption text-ink/60 mb-3">{{ __('Application') }}</p>
						<div class="flex flex-col gap-2">
							<RouterLink
								v-for="item in navItems"
								:key="item.name"
								:to="{ name: item.route }"
								class="rounded-2xl border border-transparent px-4 py-2 type-body text-ink/70 transition"
								:class="{
									'bg-sand/60 border-border/60 text-ink': route.name === item.route,
									'hover:bg-sand/40 hover:text-ink': route.name !== item.route,
								}"
							>
								{{ item.label }}
							</RouterLink>
						</div>
					</nav>
				</aside>

				<main class="flex-1">
					<div
						v-if="readOnlyReason"
						class="mb-6 rounded-3xl border border-amber-200 bg-amber-50 px-5 py-4 shadow-soft"
					>
						<p class="type-body-strong text-amber-900">{{ __('Read-only mode') }}</p>
						<p class="mt-1 type-caption text-amber-900/80">
							{{ readOnlyReason }}
						</p>
					</div>

					<div class="rounded-3xl border border-border/70 bg-white px-6 py-6 shadow-soft">
						<slot />
					</div>
				</main>
			</div>
		</div>

		<footer class="border-t border-border/70 bg-white/80 backdrop-blur px-4 py-6 sm:px-6 lg:px-8">
			<div class="mx-auto max-w-6xl flex flex-col gap-2 text-ink/60">
				<p class="type-caption">{{ __('Need help? Contact the admissions office.') }}</p>
				<p class="type-caption">{{ __('Ifitwala Admissions Portal') }}</p>
			</div>
		</footer>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import { Spinner } from 'frappe-ui';

import { provideAdmissionsSession } from '@/composables/useAdmissionsSession';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';

const route = useRoute();

const { session, loading, error, refresh } = provideAdmissionsSession();

const navItems = [
	{ name: 'overview', label: 'Overview', route: 'admissions-overview' },
	{ name: 'health', label: 'Health', route: 'admissions-health' },
	{ name: 'documents', label: 'Documents', route: 'admissions-documents' },
	{ name: 'policies', label: 'Policies', route: 'admissions-policies' },
	{ name: 'submit', label: 'Submit', route: 'admissions-submit' },
	{ name: 'status', label: 'Status', route: 'admissions-status' },
];

const applicantName = computed(() => session.value?.applicant?.name || '');
const portalStatusLabel = computed(() => session.value?.applicant?.portal_status || '');
const readOnlyReason = computed(() => session.value?.applicant?.read_only_reason || null);

let unsubscribe: (() => void) | null = null;

onMounted(async () => {
	await refresh();
	unsubscribe = uiSignals.subscribe(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE, () => {
		refresh();
	});
});

onBeforeUnmount(() => {
	if (unsubscribe) unsubscribe();
});
</script>
