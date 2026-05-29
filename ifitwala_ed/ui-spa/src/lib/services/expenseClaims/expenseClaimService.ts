import { apiUpload } from '@/lib/client'
import { apiMethod } from '@/resources/frappe'

import type {
	Request as CancelExpenseClaimRequest,
	Response as CancelExpenseClaimResponse,
} from '@/types/contracts/expense_claims/cancel_expense_claim'
import type {
	Request as CreateExpenseClaimPaymentRequest,
	Response as CreateExpenseClaimPaymentResponse,
} from '@/types/contracts/expense_claims/create_expense_claim_payment'
import type {
	Request as DecideExpenseClaimRequest,
	Response as DecideExpenseClaimResponse,
} from '@/types/contracts/expense_claims/decide_expense_claim'
import type {
	Request as GetExpenseClaimBoardRequest,
	Response as GetExpenseClaimBoardResponse,
} from '@/types/contracts/expense_claims/get_expense_claim_board'
import type {
	Request as PostExpenseClaimPayableRequest,
	Response as PostExpenseClaimPayableResponse,
} from '@/types/contracts/expense_claims/post_expense_claim_payable'
import type {
	Request as SaveExpenseClaimDraftRequest,
	Response as SaveExpenseClaimDraftResponse,
} from '@/types/contracts/expense_claims/save_expense_claim_draft'
import type {
	Request as SubmitExpenseClaimRequest,
	Response as SubmitExpenseClaimResponse,
} from '@/types/contracts/expense_claims/submit_expense_claim'
import type { Response as UploadExpenseClaimReceiptResponse } from '@/types/contracts/expense_claims/upload_expense_claim_receipt'

const METHODS = {
	getBoard: 'ifitwala_ed.api.expense_claims.get_expense_claim_board',
	saveDraft: 'ifitwala_ed.api.expense_claims.save_expense_claim_draft',
	submit: 'ifitwala_ed.api.expense_claims.submit_expense_claim',
	decide: 'ifitwala_ed.api.expense_claims.decide_expense_claim',
	postPayable: 'ifitwala_ed.api.expense_claims.post_expense_claim_payable',
	createPayment: 'ifitwala_ed.api.expense_claims.create_expense_claim_payment',
	cancel: 'ifitwala_ed.api.expense_claims.cancel_expense_claim',
	uploadReceipt: 'ifitwala_ed.api.expense_claim_receipts.upload_expense_claim_receipt',
} as const

export async function getExpenseClaimBoard(
	payload: GetExpenseClaimBoardRequest = {}
): Promise<GetExpenseClaimBoardResponse> {
	return apiMethod<GetExpenseClaimBoardResponse>(METHODS.getBoard, payload)
}

export async function saveExpenseClaimDraft(
	payload: SaveExpenseClaimDraftRequest
): Promise<SaveExpenseClaimDraftResponse> {
	return apiMethod<SaveExpenseClaimDraftResponse>(METHODS.saveDraft, payload)
}

export async function submitExpenseClaim(
	payload: SubmitExpenseClaimRequest
): Promise<SubmitExpenseClaimResponse> {
	return apiMethod<SubmitExpenseClaimResponse>(METHODS.submit, payload)
}

export async function decideExpenseClaim(
	payload: DecideExpenseClaimRequest
): Promise<DecideExpenseClaimResponse> {
	return apiMethod<DecideExpenseClaimResponse>(METHODS.decide, payload)
}

export async function postExpenseClaimPayable(
	payload: PostExpenseClaimPayableRequest
): Promise<PostExpenseClaimPayableResponse> {
	return apiMethod<PostExpenseClaimPayableResponse>(METHODS.postPayable, payload)
}

export async function createExpenseClaimPayment(
	payload: CreateExpenseClaimPaymentRequest
): Promise<CreateExpenseClaimPaymentResponse> {
	return apiMethod<CreateExpenseClaimPaymentResponse>(METHODS.createPayment, payload)
}

export async function cancelExpenseClaim(
	payload: CancelExpenseClaimRequest
): Promise<CancelExpenseClaimResponse> {
	return apiMethod<CancelExpenseClaimResponse>(METHODS.cancel, payload)
}

export async function uploadExpenseClaimReceipt(
	expenseClaim: string,
	file: File
): Promise<UploadExpenseClaimReceiptResponse> {
	const formData = new FormData()
	formData.append('expense_claim', expenseClaim)
	formData.append('file', file)
	return apiUpload<UploadExpenseClaimReceiptResponse>(METHODS.uploadReceipt, formData)
}
