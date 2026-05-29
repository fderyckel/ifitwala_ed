<!-- ifitwala_ed/ui-spa/src/pages/guardian/GuardianFinance.vue -->
<template>
	<div class="portal-page">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">{{ __('Guardian Portal') }}</p>
					<h1 class="type-h1 text-ink">{{ __('Family Finance') }}</h1>
					<p class="type-body text-ink/70">
						{{
							__(
								'View invoices and payment history for account holders this guardian account is authorized to see.'
							)
						}}
					</p>
				</div>
				<button
					type="button"
					class="if-action self-start"
					:disabled="loading"
					@click="loadSnapshot"
				>
					{{ __('Refresh') }}
				</button>
			</div>
		</header>

		<section class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			<article class="card-surface p-4">
				<p class="type-caption">{{ __('Invoices') }}</p>
				<p class="type-h3 text-ink">{{ counts.total_invoices }}</p>
			</article>
			<article class="card-surface p-4">
				<p class="type-caption">{{ __('Open invoices') }}</p>
				<p class="type-h3 text-ink">{{ counts.open_invoices }}</p>
			</article>
			<article class="card-surface p-4">
				<p class="type-caption">{{ __('Overdue invoices') }}</p>
				<p class="type-h3 text-ink">{{ counts.overdue_invoices }}</p>
			</article>
			<article class="card-surface p-4">
				<p class="type-caption">{{ __('Payments recorded') }}</p>
				<p class="type-h3 text-ink">{{ counts.payment_history_count }}</p>
			</article>
		</section>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">{{ __('Loading family finance...') }}</p>
		</section>

		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">{{ __('Could not load family finance.') }}</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<section v-else-if="!meta.finance_access" class="card-surface p-5">
			<p class="type-body-strong text-ink">
				{{ __('Finance access is limited for this guardian account.') }}
			</p>
			<p class="type-body text-ink/70">
				{{
					__(
						'No linked account holder currently passes the finance authority rule for this portal login.'
					)
				}}
			</p>
		</section>

		<template v-else>
			<section class="card-surface p-5">
				<h2 class="mb-3 type-h3 text-ink">{{ __('Authorized Account Holders') }}</h2>
				<div class="space-y-3">
					<article
						v-for="holder in accountHolders"
						:key="holder.account_holder"
						class="rounded-xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
							<div>
								<p class="type-body-strong text-ink">{{ holder.label }}</p>
								<p class="type-caption text-ink/60">
									{{ holder.organization }} · {{ holder.status }}
								</p>
							</div>
							<p class="type-caption text-ink/60">
								{{ holder.primary_email_masked || __('No billing email on file') }}
							</p>
						</div>
						<p class="mt-2 type-body text-ink/70">
							{{
								__('Students: {0}', [
									holder.students.map(student => student.full_name).join(', ') ||
										__('None linked'),
								])
							}}
						</p>
					</article>
				</div>
			</section>

			<section class="card-surface p-5">
				<div class="mb-3 flex items-center justify-between">
					<h2 class="type-h3 text-ink">{{ __('Invoices') }}</h2>
					<p class="type-caption text-ink/60">
						{{ __('Outstanding: {0}', [formatMoney(counts.total_outstanding)]) }}
					</p>
				</div>
				<div v-if="!invoices.length" class="type-body text-ink/70">
					{{ __('No submitted invoices found.') }}
				</div>
				<div v-else class="space-y-3">
					<article
						v-for="invoice in invoices"
						:key="invoice.sales_invoice"
						class="rounded-xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
							<div>
								<p class="type-body-strong text-ink">{{ invoice.sales_invoice }}</p>
								<p class="type-caption text-ink/60">
									{{ invoice.status }} · {{ __('Posted {0}', [invoice.posting_date]) }}
									<span v-if="invoice.due_date"> · {{ __('Due {0}', [invoice.due_date]) }} </span>
								</p>
							</div>
							<div class="text-left sm:text-right">
								<p class="type-body-strong text-ink">{{ formatMoney(invoice.grand_total) }}</p>
								<p class="type-caption text-ink/60">
									{{
										__('Paid {0} · Outstanding {1}', [
											formatMoney(invoice.paid_amount),
											formatMoney(invoice.outstanding_amount),
										])
									}}
								</p>
							</div>
						</div>
						<p class="mt-2 type-body text-ink/70">
							{{ __('Account holder: {0}', [accountHolderLabel(invoice.account_holder)]) }}
						</p>
						<p class="type-body text-ink/70">
							{{
								__('Students: {0}', [
									invoice.students.map(student => student.full_name).join(', ') ||
										__('Not tagged to individual students'),
								])
							}}
						</p>
						<p v-if="invoice.remarks" class="type-caption text-ink/60">{{ invoice.remarks }}</p>
					</article>
				</div>
			</section>

			<section class="card-surface p-5">
				<div class="mb-3 flex items-center justify-between">
					<h2 class="type-h3 text-ink">{{ __('Payment History') }}</h2>
					<p class="type-caption text-ink/60">
						{{ __('Recorded: {0}', [formatMoney(counts.total_paid)]) }}
					</p>
				</div>
				<div v-if="!payments.length" class="type-body text-ink/70">
					{{ __('No submitted payments found.') }}
				</div>
				<div v-else class="space-y-3">
					<article
						v-for="payment in payments"
						:key="payment.payment_entry"
						class="rounded-xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
							<div>
								<p class="type-body-strong text-ink">{{ payment.payment_entry }}</p>
								<p class="type-caption text-ink/60">
									{{ payment.posting_date }} · {{ accountHolderLabel(payment.account_holder) }}
								</p>
							</div>
							<div class="text-left sm:text-right">
								<p class="type-body-strong text-ink">{{ formatMoney(payment.paid_amount) }}</p>
								<p class="type-caption text-ink/60">
									{{ __('Unallocated {0}', [formatMoney(payment.unallocated_amount)]) }}
								</p>
							</div>
						</div>
						<p class="mt-2 type-body text-ink/70">
							{{ __('Applied to: {0}', [paymentReferenceLabel(payment)]) }}
						</p>
						<p v-if="payment.remarks" class="type-caption text-ink/60">{{ payment.remarks }}</p>
					</article>
				</div>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { __ } from '@/lib/i18n';
import { getGuardianFinanceSnapshot } from '@/lib/services/guardianFinance/guardianFinanceService';

import type {
	AccountHolderSummary,
	GuardianInvoice,
	GuardianPayment,
	Response as GuardianFinanceSnapshot,
} from '@/types/contracts/guardian/get_guardian_finance_snapshot';

const loading = ref(true);
const errorMessage = ref('');
const snapshot = ref<GuardianFinanceSnapshot | null>(null);

const meta = computed(
	() =>
		snapshot.value?.meta ?? {
			generated_at: '',
			guardian: { name: null },
			finance_access: false,
			access_reason: '',
		}
);
const counts = computed(
	() =>
		snapshot.value?.counts ?? {
			total_invoices: 0,
			open_invoices: 0,
			overdue_invoices: 0,
			payment_history_count: 0,
			total_outstanding: 0,
			total_paid: 0,
		}
);
const accountHolders = computed<AccountHolderSummary[]>(
	() => snapshot.value?.account_holders ?? []
);
const invoices = computed<GuardianInvoice[]>(() => snapshot.value?.invoices ?? []);
const payments = computed<GuardianPayment[]>(() => snapshot.value?.payments ?? []);

const currencyFormatter = new Intl.NumberFormat(undefined, {
	style: 'currency',
	currency: 'USD',
	maximumFractionDigits: 2,
});

function formatMoney(value: number): string {
	return currencyFormatter.format(Number(value || 0));
}

function accountHolderLabel(accountHolder: string): string {
	return (
		accountHolders.value.find(holder => holder.account_holder === accountHolder)?.label ??
		accountHolder
	);
}

function paymentReferenceLabel(payment: GuardianPayment): string {
	if (!payment.references.length) return __('No invoice allocations recorded');
	return payment.references
		.map(reference =>
			__('{0} ({1})', [reference.sales_invoice, formatMoney(reference.allocated_amount)])
		)
		.join(', ');
}

async function loadSnapshot() {
	loading.value = true;
	errorMessage.value = '';
	try {
		snapshot.value = await getGuardianFinanceSnapshot();
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		errorMessage.value = message || __('Unknown error');
	} finally {
		loading.value = false;
	}
}

onMounted(() => {
	void loadSnapshot();
});
</script>
