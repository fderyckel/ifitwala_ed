<template>
	<div class="portal-page">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">Guardian Portal</p>
					<h1 class="type-h1 text-ink">Forms &amp; Signatures</h1>
					<p class="type-body text-ink/70">
						Review operational forms that need guardian action for each child.
					</p>
				</div>
				<button type="button" class="if-action self-start" :disabled="loading" @click="loadBoard">
					Refresh
				</button>
			</div>
		</header>

		<section class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
			<article class="card-surface p-4">
				<p class="type-caption text-ink/65">Action needed</p>
				<p class="type-h3 text-clay">{{ counts.pending + counts.overdue }}</p>
			</article>
			<article class="card-surface p-4">
				<p class="type-caption text-ink/65">Completed</p>
				<p class="type-h3 text-canopy">{{ counts.completed }}</p>
			</article>
			<article class="card-surface p-4">
				<p class="type-caption text-ink/65">Declined</p>
				<p class="type-h3 text-flame">{{ counts.declined }}</p>
			</article>
			<article class="card-surface p-4">
				<p class="type-caption text-ink/65">Withdrawn</p>
				<p class="type-h3 text-ink">{{ counts.withdrawn }}</p>
			</article>
			<article class="card-surface p-4">
				<p class="type-caption text-ink/65">Expired</p>
				<p class="type-h3 text-ink">{{ counts.expired }}</p>
			</article>
			<article class="card-surface p-4">
				<p class="type-caption text-ink/65">Overdue</p>
				<p class="type-h3 text-flame">{{ counts.overdue }}</p>
			</article>
		</section>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading forms and signatures...</p>
		</section>

		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">Could not load forms and signatures.</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<section v-else-if="isEmpty" class="card-surface p-5">
			<p class="type-body-strong text-ink">No guardian form requests are in scope.</p>
			<p class="type-body text-ink/70">
				New operational forms will appear here when your school publishes them to the family
				portal.
			</p>
		</section>

		<template v-else>
			<section
				v-if="groups.action_needed.length"
				class="student-hub-section student-hub-section--warm"
			>
				<div class="mb-4 flex items-center justify-between gap-3">
					<div>
						<p class="type-overline text-ink/60">Action Needed</p>
						<h2 class="type-h2 text-ink">
							Complete the forms that are waiting for your signature
						</h2>
					</div>
					<span class="chip chip-warm">{{ groups.action_needed.length }}</span>
				</div>
				<div class="space-y-3">
					<RouterLink
						v-for="row in groups.action_needed"
						:key="rowKey(row)"
						:to="detailLink(row)"
						class="card-surface block p-4 transition hover:border-jacaranda/30 hover:bg-jacaranda/5"
					>
						<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
							<div>
								<p class="type-caption text-ink/60">
									{{ row.student_name }}<span v-if="row.school"> · {{ row.school }}</span>
								</p>
								<h3 class="type-h3 text-ink">{{ row.request_title }}</h3>
								<p class="mt-1 type-body text-ink/70">
									{{ row.request_type }} · {{ row.decision_mode }}
								</p>
								<p v-if="row.due_on" class="mt-2 type-caption text-ink/60">Due {{ row.due_on }}</p>
							</div>
							<div class="flex flex-col items-start gap-2 sm:items-end">
								<span
									class="chip"
									:class="row.current_status === 'overdue' ? 'chip-alert' : 'chip-warm'"
								>
									{{ row.current_status_label }}
								</span>
								<p class="type-caption text-ink/60">{{ row.completion_channel_mode }}</p>
							</div>
						</div>
					</RouterLink>
				</div>
			</section>

			<section
				v-if="groups.completed.length"
				class="student-hub-section student-hub-section--support"
			>
				<div class="mb-4 flex items-center justify-between gap-3">
					<h2 class="type-h3 text-ink">Completed</h2>
					<span class="chip chip-success">{{ groups.completed.length }}</span>
				</div>
				<div class="space-y-3">
					<RouterLink
						v-for="row in groups.completed"
						:key="rowKey(row)"
						:to="detailLink(row)"
						class="card-surface block p-4 transition hover:border-canopy/25 hover:bg-canopy/5"
					>
						<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
							<div>
								<p class="type-caption text-ink/60">{{ row.student_name }}</p>
								<h3 class="type-body-strong text-ink">{{ row.request_title }}</h3>
								<p class="mt-1 type-caption text-ink/65">
									{{ row.current_status_label }}
									<span v-if="row.last_decision_at">· {{ row.last_decision_at }}</span>
								</p>
							</div>
							<span class="chip chip-success">{{ row.current_status_label }}</span>
						</div>
					</RouterLink>
				</div>
			</section>

			<section
				v-if="groups.declined_or_withdrawn.length"
				class="student-hub-section border border-flame/20 bg-flame/5"
			>
				<div class="mb-4 flex items-center justify-between gap-3">
					<h2 class="type-h3 text-ink">Declined or withdrawn</h2>
					<span class="chip chip-alert">{{ groups.declined_or_withdrawn.length }}</span>
				</div>
				<div class="space-y-3">
					<RouterLink
						v-for="row in groups.declined_or_withdrawn"
						:key="rowKey(row)"
						:to="detailLink(row)"
						class="card-surface block p-4 transition hover:border-flame/25 hover:bg-flame/5"
					>
						<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
							<div>
								<p class="type-caption text-ink/60">{{ row.student_name }}</p>
								<h3 class="type-body-strong text-ink">{{ row.request_title }}</h3>
								<p class="mt-1 type-caption text-ink/65">
									{{ row.current_status_label }}
									<span v-if="row.last_decision_at">· {{ row.last_decision_at }}</span>
								</p>
							</div>
							<span class="chip chip-alert">{{ row.current_status_label }}</span>
						</div>
					</RouterLink>
				</div>
			</section>

			<section v-if="groups.expired.length" class="student-hub-section">
				<div class="mb-4 flex items-center justify-between gap-3">
					<h2 class="type-h3 text-ink">Expired</h2>
					<span class="chip">{{ groups.expired.length }}</span>
				</div>
				<div class="space-y-3">
					<RouterLink
						v-for="row in groups.expired"
						:key="rowKey(row)"
						:to="detailLink(row)"
						class="card-surface block p-4 transition hover:border-ink/15 hover:bg-surface-soft"
					>
						<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
							<div>
								<p class="type-caption text-ink/60">{{ row.student_name }}</p>
								<h3 class="type-body-strong text-ink">{{ row.request_title }}</h3>
								<p class="mt-1 type-caption text-ink/65">
									Expired<span v-if="row.effective_to"> · {{ row.effective_to }}</span>
								</p>
							</div>
							<span class="chip">{{ row.current_status_label }}</span>
						</div>
					</RouterLink>
				</div>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';

import { getGuardianConsentBoard } from '@/lib/services/guardianConsent/guardianConsentService';

import type { Response as GuardianConsentBoardResponse } from '@/types/contracts/guardian/get_guardian_consent_board';
import type { ConsentBoardRow } from '@/types/contracts/family_consent/shared';

const loading = ref(true);
const errorMessage = ref('');
const board = ref<GuardianConsentBoardResponse | null>(null);

const counts = computed(
	() =>
		board.value?.counts ?? {
			pending: 0,
			completed: 0,
			declined: 0,
			withdrawn: 0,
			expired: 0,
			overdue: 0,
		}
);
const groups = computed(
	() =>
		board.value?.groups ?? {
			action_needed: [],
			completed: [],
			declined_or_withdrawn: [],
			expired: [],
		}
);
const isEmpty = computed(
	() =>
		!groups.value.action_needed.length &&
		!groups.value.completed.length &&
		!groups.value.declined_or_withdrawn.length &&
		!groups.value.expired.length
);

function rowKey(row: ConsentBoardRow): string {
	return `${row.request_key}:${row.student}`;
}

function detailLink(row: ConsentBoardRow) {
	return {
		name: 'guardian-consent-detail',
		params: { request_key: row.request_key, student_id: row.student },
	};
}

async function loadBoard() {
	loading.value = true;
	errorMessage.value = '';
	try {
		board.value = await getGuardianConsentBoard();
	} catch (error) {
		errorMessage.value = error instanceof Error ? error.message : 'Unknown error';
	} finally {
		loading.value = false;
	}
}

onMounted(() => {
	loadBoard();
});
</script>
