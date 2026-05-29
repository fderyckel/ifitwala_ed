<template>
	<div class="card-panel p-5">
		<div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
			<div class="min-w-0 space-y-2">
				<p class="type-overline text-ink/60">{{ claim?.status || __('Expense Claim') }}</p>
				<h3 class="type-h3 text-ink">{{ claim?.claim_title || claim?.name }}</h3>
				<p class="type-caption text-ink/70">
					{{ claim?.employee_name || claim?.employee || claim?.name }}
				</p>
			</div>
			<div class="text-left sm:text-right">
				<p class="type-overline text-ink/60">{{ amountLabel }}</p>
				<p class="type-h3 text-ink">{{ money(amountValue) }}</p>
			</div>
		</div>

		<div v-if="claim?.decision_notes" class="mt-4 rounded-lg bg-amber-50 p-3">
			<p class="type-label text-amber-900">{{ __('Notes') }}</p>
			<p class="mt-1 type-body text-amber-950">{{ claim.decision_notes }}</p>
		</div>

		<ul
			v-if="claim?.items?.length"
			class="mt-4 divide-y divide-slate-100 rounded-lg border border-slate-200"
		>
			<li
				v-for="item in claim.items"
				:key="`${item.expense_date}-${item.description}`"
				class="p-3"
			>
				<div class="flex items-start justify-between gap-3">
					<div class="min-w-0">
						<p class="type-body-strong text-ink">{{ item.expense_category || __('Expense') }}</p>
						<p class="type-caption text-ink/70">{{ item.description }}</p>
					</div>
					<p class="type-body-strong text-ink">{{ money(item.claimed_amount || 0) }}</p>
				</div>
			</li>
		</ul>

		<div class="mt-5 flex flex-wrap justify-end gap-2">
			<Button variant="ghost" @click="emit('close')">{{ __('Close') }}</Button>
			<RouterLink :to="{ name: 'staff-expense-claims' }" custom v-slot="{ navigate }">
				<Button variant="solid" @click="openExpenseClaims(navigate)">
					{{ actionLabel }}
				</Button>
			</RouterLink>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { Button } from 'frappe-ui';

import { __ } from '@/lib/i18n';

import type { Response as GetFocusContextResponse } from '@/types/contracts/focus/get_focus_context';

const props = defineProps<{
	context: GetFocusContextResponse;
}>();

const emit = defineEmits<{
	(e: 'close'): void;
}>();

const claim = computed(() => props.context.expense_claim);

const amountLabel = computed(() => {
	if (claim.value?.status === 'Payable Posted') return __('Outstanding');
	if (claim.value?.status === 'Approved') return __('Approved');
	return __('Claimed');
});

const amountValue = computed(() => {
	if (claim.value?.status === 'Payable Posted') return claim.value?.outstanding_amount || 0;
	if (claim.value?.status === 'Approved') return claim.value?.sanctioned_total || 0;
	return claim.value?.claimed_total || 0;
});

const actionLabel = computed(() => {
	if (claim.value?.status === 'Needs Info') return __('Update claim');
	if (claim.value?.status === 'Submitted') return __('Review claim');
	return __('Open finance queue');
});

function money(value: number) {
	return new Intl.NumberFormat(undefined, {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	}).format(Number(value || 0));
}

function openExpenseClaims(navigate: () => void) {
	navigate();
	emit('close');
}
</script>
