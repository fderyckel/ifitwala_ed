// ui-spa/src/types/contracts/focus/acknowledge_staff_policy.ts

export type Request = {
	focus_item_id: string;
	client_request_id?: string | null;
	typed_signature_name?: string | null;
	attestation_confirmed?: 0 | 1;
};

export type Response = {
	ok: boolean;
	idempotent: boolean;
	status: 'processed' | 'already_processed';
	policy_version: string;
	employee: string;
	acknowledgement: string;
	acknowledged_at?: string | null;
	closed_todos?: number;
};
