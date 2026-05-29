<template>
	<div class="staff-shell space-y-6">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
				<div class="space-y-2">
					<p class="type-overline text-ink/60">{{ __('Expenses') }}</p>
					<h1 class="type-h1 text-ink">{{ __('My Reimbursements') }}</h1>
				</div>
				<button type="button" class="if-button if-button--secondary" @click="loadBoard">
					<FeatherIcon name="refresh-cw" class="h-4 w-4" />
					<span>{{ __('Refresh') }}</span>
				</button>
			</div>
		</header>

		<section class="grid gap-3 sm:grid-cols-4">
			<article class="mini-kpi-card">
				<p class="type-overline text-slate-token/70">{{ __('Draft') }}</p>
				<p class="type-h2 text-ink">{{ board?.stats.draft ?? 0 }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="type-overline text-slate-token/70">{{ __('Submitted') }}</p>
				<p class="type-h2 text-ink">{{ board?.stats.submitted ?? 0 }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="type-overline text-slate-token/70">{{ __('Approved') }}</p>
				<p class="type-h2 text-ink">{{ board?.stats.approved ?? 0 }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="type-overline text-slate-token/70">{{ __('Outstanding') }}</p>
				<p class="type-h2 text-ink">{{ money(board?.stats.outstanding || 0) }}</p>
			</article>
		</section>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-slate-token">{{ __('Loading expense claims...') }}</p>
		</section>

		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">{{ errorMessage }}</p>
		</section>

		<template v-else-if="board">
			<section class="card-surface p-5 sm:p-6">
				<form class="space-y-5" @submit.prevent="submitDraft">
					<div class="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
						<label class="space-y-2">
							<span class="type-label text-ink">{{ __('Title') }}</span>
							<input v-model.trim="draft.claim_title" class="form-input" type="text" required />
						</label>
						<label class="space-y-2">
							<span class="type-label text-ink">{{ __('Claim Date') }}</span>
							<input v-model="draft.claim_date" class="form-input" type="date" required />
						</label>
					</div>

					<label class="space-y-2">
						<span class="type-label text-ink">{{ __('Purpose') }}</span>
						<textarea v-model.trim="draft.purpose" class="form-textarea min-h-20" />
					</label>

					<div class="space-y-3">
						<div class="flex items-center justify-between gap-3">
							<h2 class="type-h3 text-ink">{{ __('Items') }}</h2>
							<button type="button" class="if-button if-button--secondary" @click="addItem">
								<FeatherIcon name="plus" class="h-4 w-4" />
								<span>{{ __('Add') }}</span>
							</button>
						</div>

						<div class="overflow-x-auto rounded-lg border border-slate-200">
							<table class="min-w-full divide-y divide-slate-200 text-left">
								<thead class="bg-slate-50">
									<tr>
										<th class="px-3 py-2 type-label text-slate-token">{{ __('Date') }}</th>
										<th class="px-3 py-2 type-label text-slate-token">
											{{ __('Category') }}
										</th>
										<th class="px-3 py-2 type-label text-slate-token">
											{{ __('Description') }}
										</th>
										<th class="px-3 py-2 type-label text-slate-token">{{ __('Amount') }}</th>
										<th class="w-12 px-3 py-2"></th>
									</tr>
								</thead>
								<tbody class="divide-y divide-slate-100 bg-white">
									<tr v-for="item in draft.items" :key="item.uid">
										<td class="px-3 py-2 align-top">
											<input
												v-model="item.expense_date"
												class="form-input min-w-36"
												type="date"
												required
											/>
										</td>
										<td class="px-3 py-2 align-top">
											<select
												v-model="item.expense_category"
												class="form-select min-w-48"
												required
											>
												<option
													v-for="category in board.options.categories"
													:key="category"
													:value="category"
												>
													{{ category }}
												</option>
											</select>
										</td>
										<td class="px-3 py-2 align-top">
											<input
												v-model.trim="item.description"
												class="form-input min-w-64"
												type="text"
												required
											/>
										</td>
										<td class="px-3 py-2 align-top">
											<input
												v-model.number="item.claimed_amount"
												class="form-input min-w-32"
												min="0"
												step="0.01"
												type="number"
												required
											/>
										</td>
										<td class="px-3 py-2 align-top">
											<button
												type="button"
												class="if-button if-button--quiet"
												:disabled="draft.items.length === 1"
												@click="removeItem(item.uid)"
											>
												<FeatherIcon name="trash-2" class="h-4 w-4" />
											</button>
										</td>
									</tr>
								</tbody>
							</table>
						</div>
					</div>

					<div class="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
						<label class="space-y-2">
							<span class="type-label text-ink">{{ __('Receipts') }}</span>
							<input class="form-input" type="file" multiple @change="onReceiptFilesChange" />
						</label>
						<div class="text-right">
							<p class="type-overline text-slate-token/70">{{ __('Total') }}</p>
							<p class="type-h2 text-ink">{{ money(draftTotal) }}</p>
						</div>
					</div>

					<div v-if="receiptFiles.length" class="flex flex-wrap gap-2">
						<span
							v-for="file in receiptFiles"
							:key="file.name"
							class="rounded-full bg-slate-100 px-3 py-1 type-caption text-slate-token"
						>
							{{ file.name }}
						</span>
					</div>

					<p v-if="formError" class="type-body-strong text-flame">{{ formError }}</p>

					<div class="flex flex-wrap justify-end gap-3">
						<button type="button" class="if-button if-button--secondary" @click="resetDraft">
							<FeatherIcon name="x" class="h-4 w-4" />
							<span>{{ __('Clear') }}</span>
						</button>
						<button type="submit" class="if-button if-button--primary" :disabled="saving">
							<FeatherIcon name="send" class="h-4 w-4" />
							<span>{{ saving ? __('Submitting...') : __('Submit Claim') }}</span>
						</button>
					</div>
				</form>
			</section>

			<section class="space-y-3">
				<h2 class="type-h2 text-ink">{{ __('My Claims') }}</h2>
				<article v-if="!board.my_claims.length" class="card-surface p-5">
					<p class="type-body text-slate-token">{{ __('No expense claims yet.') }}</p>
				</article>
				<article v-for="claim in board.my_claims" :key="claim.name" class="card-surface p-5">
					<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
						<div class="min-w-0 space-y-2">
							<div class="flex flex-wrap items-center gap-2">
								<h3 class="type-h3 text-ink">{{ claim.claim_title }}</h3>
								<span
									class="rounded-full bg-slate-100 px-2 py-0.5 type-badge-label text-slate-token"
								>
									{{ claim.status }}
								</span>
							</div>
							<p class="type-caption text-slate-token">
								{{ formatDate(claim.claim_date) }} · {{ claim.name }}
							</p>
							<div class="flex flex-wrap gap-2">
								<a
									v-for="receipt in claim.receipts"
									:key="receipt.row_name"
									:href="receipt.attachment?.open_url || receipt.external_url || '#'"
									target="_blank"
									rel="noopener"
									class="rounded-full bg-sky/15 px-3 py-1 type-caption text-canopy"
								>
									{{ receipt.title }}
								</a>
							</div>
						</div>
						<div class="grid gap-1 text-right">
							<p class="type-overline text-slate-token/70">{{ __('Claimed') }}</p>
							<p class="type-h3 text-ink">{{ money(claim.claimed_total) }}</p>
							<p v-if="claim.outstanding_amount" class="type-caption text-flame">
								{{ __('Outstanding {0}', [money(claim.outstanding_amount)]) }}
							</p>
						</div>
					</div>
					<div v-if="canCancel(claim)" class="mt-4 flex justify-end">
						<button
							type="button"
							class="if-button if-button--secondary"
							@click="cancelClaim(claim.name)"
						>
							<FeatherIcon name="slash" class="h-4 w-4" />
							<span>{{ __('Cancel') }}</span>
						</button>
					</div>
				</article>
			</section>

			<section v-if="board.approval_queue.length" class="space-y-3">
				<h2 class="type-h2 text-ink">{{ __('Approvals') }}</h2>
				<article v-for="claim in board.approval_queue" :key="claim.name" class="card-surface p-5">
					<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
						<div class="space-y-2">
							<h3 class="type-h3 text-ink">{{ claim.claim_title }}</h3>
							<p class="type-caption text-slate-token">
								{{ claim.employee_name }} · {{ money(claim.claimed_total) }}
							</p>
							<ul class="space-y-1">
								<li
									v-for="item in claim.items"
									:key="item.row_name || item.description"
									class="type-caption text-slate-token"
								>
									{{ item.expense_category }} · {{ item.description }} ·
									{{ money(item.claimed_amount) }}
								</li>
							</ul>
						</div>
						<div class="flex flex-wrap gap-2">
							<button
								type="button"
								class="if-button if-button--secondary"
								@click="decide(claim.name, 'reject')"
							>
								<FeatherIcon name="x" class="h-4 w-4" />
								<span>{{ __('Reject') }}</span>
							</button>
							<button
								type="button"
								class="if-button if-button--primary"
								@click="decide(claim.name, 'approve')"
							>
								<FeatherIcon name="check" class="h-4 w-4" />
								<span>{{ __('Approve') }}</span>
							</button>
						</div>
					</div>
				</article>
			</section>

			<section v-if="board.viewer.can_finance && board.finance_queue.length" class="space-y-3">
				<h2 class="type-h2 text-ink">{{ __('Finance Queue') }}</h2>
				<article v-for="claim in board.finance_queue" :key="claim.name" class="card-surface p-5">
					<div class="space-y-4">
						<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
							<div>
								<h3 class="type-h3 text-ink">{{ claim.claim_title }}</h3>
								<p class="type-caption text-slate-token">
									{{ claim.employee_name }} · {{ claim.status }} ·
									{{ money(claim.sanctioned_total) }}
								</p>
							</div>
							<p v-if="claim.outstanding_amount" class="type-body-strong text-flame">
								{{ __('{0} outstanding', [money(claim.outstanding_amount)]) }}
							</p>
						</div>

						<div v-if="financeForms[claim.name]" class="grid gap-3 lg:grid-cols-3">
							<label v-if="claim.status === 'Approved'" class="space-y-2">
								<span class="type-label text-ink">{{ __('Expense Account') }}</span>
								<select v-model="financeForms[claim.name].expense_account" class="form-select">
									<option value=""></option>
									<option
										v-for="account in board.options.expense_accounts"
										:key="account.value"
										:value="account.value"
									>
										{{ accountLabel(account) }}
									</option>
								</select>
							</label>
							<label v-if="claim.status === 'Approved'" class="space-y-2">
								<span class="type-label text-ink">{{ __('Payable Account') }}</span>
								<select v-model="financeForms[claim.name].payable_account" class="form-select">
									<option value=""></option>
									<option
										v-for="account in board.options.payable_accounts"
										:key="account.value"
										:value="account.value"
									>
										{{ accountLabel(account) }}
									</option>
								</select>
							</label>
							<label v-if="claim.status === 'Payable Posted'" class="space-y-2">
								<span class="type-label text-ink">{{ __('Bank or Cash') }}</span>
								<select v-model="financeForms[claim.name].paid_to" class="form-select">
									<option value=""></option>
									<option
										v-for="account in board.options.bank_accounts"
										:key="account.value"
										:value="account.value"
									>
										{{ accountLabel(account) }}
									</option>
								</select>
							</label>
							<label v-if="claim.status === 'Payable Posted'" class="space-y-2">
								<span class="type-label text-ink">{{ __('Paid Amount') }}</span>
								<input
									v-model.number="financeForms[claim.name].paid_amount"
									class="form-input"
									min="0"
									step="0.01"
									type="number"
								/>
							</label>
						</div>

						<div class="flex justify-end">
							<button
								v-if="claim.status === 'Approved'"
								type="button"
								class="if-button if-button--primary"
								@click="postPayable(claim.name)"
							>
								<FeatherIcon name="file-plus" class="h-4 w-4" />
								<span>{{ __('Post Payable') }}</span>
							</button>
							<button
								v-if="claim.status === 'Payable Posted'"
								type="button"
								class="if-button if-button--primary"
								@click="payClaim(claim.name)"
							>
								<FeatherIcon name="credit-card" class="h-4 w-4" />
								<span>{{ __('Pay') }}</span>
							</button>
						</div>
					</div>
				</article>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { FeatherIcon, toast } from 'frappe-ui';

import { __ } from '@/lib/i18n';
import {
	cancelExpenseClaim,
	createExpenseClaimPayment,
	decideExpenseClaim,
	getExpenseClaimBoard,
	postExpenseClaimPayable,
	saveExpenseClaimDraft,
	submitExpenseClaim,
	uploadExpenseClaimReceipt,
} from '@/lib/services/expenseClaims/expenseClaimService';
import type {
	ExpenseClaimAccountOption,
	ExpenseClaimBoard,
	ExpenseClaimItemRow,
	ExpenseClaimRow,
} from '@/types/contracts/expense_claims/shared';

type DraftItem = ExpenseClaimItemRow & { uid: string };
type FinanceForm = {
	expense_account: string;
	payable_account: string;
	paid_to: string;
	paid_amount: number | null;
};

const loading = ref(true);
const saving = ref(false);
const errorMessage = ref('');
const formError = ref('');
const board = ref<ExpenseClaimBoard | null>(null);
const receiptFiles = ref<File[]>([]);
const financeForms = reactive<Record<string, FinanceForm>>({});

const draft = reactive<{
	claim_title: string;
	claim_date: string;
	purpose: string;
	items: DraftItem[];
}>({
	claim_title: '',
	claim_date: '',
	purpose: '',
	items: [],
});

const draftTotal = computed(() =>
	draft.items.reduce((total, item) => total + Number(item.claimed_amount || 0), 0)
);

function todayString() {
	return new Date().toISOString().slice(0, 10);
}

function newItem(): DraftItem {
	return {
		uid: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
		expense_date: draft.claim_date || todayString(),
		expense_category: board.value?.options.categories[0] || 'Meals',
		description: '',
		claimed_amount: 0,
	};
}

function resetDraft() {
	draft.claim_title = '';
	draft.claim_date = board.value?.defaults.claim_date || todayString();
	draft.purpose = '';
	draft.items = [newItem()];
	receiptFiles.value = [];
	formError.value = '';
}

function addItem() {
	draft.items.push(newItem());
}

function removeItem(uid: string) {
	if (draft.items.length === 1) return;
	draft.items = draft.items.filter(item => item.uid !== uid);
}

function onReceiptFilesChange(event: Event) {
	const input = event.target as HTMLInputElement;
	receiptFiles.value = Array.from(input.files || []);
}

function money(value: number) {
	return new Intl.NumberFormat(undefined, {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	}).format(Number(value || 0));
}

function formatDate(value: string | null | undefined) {
	if (!value) return '';
	const [year, month, day] = String(value)
		.split('-')
		.map(part => Number(part));
	if (year && month && day) {
		return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(
			new Date(year, month - 1, day)
		);
	}
	return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function accountLabel(account: ExpenseClaimAccountOption) {
	return account.account_number ? `${account.account_number} - ${account.label}` : account.label;
}

function canCancel(claim: ExpenseClaimRow) {
	return ['Draft', 'Submitted', 'Approved'].includes(claim.status);
}

function ensureFinanceForm(claim: ExpenseClaimRow) {
	if (financeForms[claim.name]) return;
	financeForms[claim.name] = {
		expense_account: claim.items.find(item => item.expense_account)?.expense_account || '',
		payable_account: claim.payable_account || '',
		paid_to: '',
		paid_amount: claim.outstanding_amount || claim.sanctioned_total || null,
	};
}

watch(
	board,
	value => {
		for (const claim of value?.finance_queue || []) {
			ensureFinanceForm(claim);
		}
		if (!draft.claim_date) {
			draft.claim_date = value?.defaults.claim_date || todayString();
		}
		if (!draft.items.length) {
			draft.items = [newItem()];
		}
	},
	{ immediate: true }
);

async function loadBoard() {
	loading.value = true;
	errorMessage.value = '';
	try {
		board.value = await getExpenseClaimBoard();
	} catch (error: any) {
		errorMessage.value = error?.message || __('Unknown error');
	} finally {
		loading.value = false;
	}
}

function validateDraft() {
	if (!board.value?.viewer.expense_approver) {
		return __('No expense approver is set on your Employee record.');
	}
	if (!draft.claim_title.trim()) {
		return __('Title is required.');
	}
	if (!draft.items.length) {
		return __('At least one expense item is required.');
	}
	if (draft.items.some(item => Number(item.claimed_amount || 0) <= 0)) {
		return __('Each item needs an amount greater than zero.');
	}
	return '';
}

async function submitDraft() {
	formError.value = validateDraft();
	if (formError.value) return;

	saving.value = true;
	try {
		const saveResponse = await saveExpenseClaimDraft({
			claim_title: draft.claim_title,
			claim_date: draft.claim_date,
			purpose: draft.purpose || null,
			items: draft.items.map(({ uid, ...item }) => item),
		});
		board.value = saveResponse.board;

		for (const file of receiptFiles.value) {
			await uploadExpenseClaimReceipt(saveResponse.expense_claim.name, file);
		}

		const submitResponse = await submitExpenseClaim({
			expense_claim: saveResponse.expense_claim.name,
		});
		board.value = submitResponse.board;
		resetDraft();
		toast.create({ title: __('Expense claim submitted'), icon: 'check' });
	} catch (error: any) {
		formError.value = error?.message || __('Could not submit this claim.');
		toast.create({
			title: __('Could not submit claim'),
			text: formError.value,
			icon: 'alert-circle',
		});
	} finally {
		saving.value = false;
	}
}

async function cancelClaim(expenseClaim: string) {
	try {
		const response = await cancelExpenseClaim({ expense_claim: expenseClaim });
		board.value = response.board;
		toast.create({ title: __('Expense claim cancelled'), icon: 'check' });
	} catch (error: any) {
		toast.create({
			title: __('Could not cancel claim'),
			text: error?.message || '',
			icon: 'alert-circle',
		});
	}
}

async function decide(expenseClaim: string, decision: 'approve' | 'reject') {
	try {
		const response = await decideExpenseClaim({ expense_claim: expenseClaim, decision });
		board.value = response.board;
		toast.create({
			title: decision === 'approve' ? __('Expense claim approved') : __('Expense claim rejected'),
			icon: 'check',
		});
	} catch (error: any) {
		toast.create({
			title: __('Could not decide claim'),
			text: error?.message || '',
			icon: 'alert-circle',
		});
	}
}

async function postPayable(expenseClaim: string) {
	const form = financeForms[expenseClaim];
	if (!form?.expense_account || !form?.payable_account) {
		toast.create({ title: __('Select accounts before posting'), icon: 'alert-circle' });
		return;
	}
	try {
		const response = await postExpenseClaimPayable({
			expense_claim: expenseClaim,
			expense_account: form.expense_account,
			payable_account: form.payable_account,
		});
		board.value = response.board;
		toast.create({ title: __('Payable posted'), icon: 'check' });
	} catch (error: any) {
		toast.create({
			title: __('Could not post payable'),
			text: error?.message || '',
			icon: 'alert-circle',
		});
	}
}

async function payClaim(expenseClaim: string) {
	const form = financeForms[expenseClaim];
	if (!form?.paid_to) {
		toast.create({ title: __('Select a bank or cash account'), icon: 'alert-circle' });
		return;
	}
	try {
		const response = await createExpenseClaimPayment({
			expense_claim: expenseClaim,
			paid_to: form.paid_to,
			paid_amount: form.paid_amount,
		});
		board.value = response.board;
		toast.create({ title: __('Payment posted'), icon: 'check' });
	} catch (error: any) {
		toast.create({
			title: __('Could not post payment'),
			text: error?.message || '',
			icon: 'alert-circle',
		});
	}
}

onMounted(loadBoard);
</script>
