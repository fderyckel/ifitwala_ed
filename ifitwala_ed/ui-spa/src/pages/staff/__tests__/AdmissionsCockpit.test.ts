import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	getAdmissionsCockpitDataMock,
	sendAdmissionsCockpitOfferMock,
	hydrateAdmissionsCockpitRequestMock,
	generateAdmissionsCockpitDepositInvoiceMock,
	getAdmissionsCaseThreadMock,
	markAdmissionsCaseReadMock,
	sendAdmissionsCaseMessageMock,
	overlayOpenMock,
} = vi.hoisted(() => ({
	getAdmissionsCockpitDataMock: vi.fn(),
	sendAdmissionsCockpitOfferMock: vi.fn(),
	hydrateAdmissionsCockpitRequestMock: vi.fn(),
	generateAdmissionsCockpitDepositInvoiceMock: vi.fn(),
	getAdmissionsCaseThreadMock: vi.fn(),
	markAdmissionsCaseReadMock: vi.fn(),
	sendAdmissionsCaseMessageMock: vi.fn(),
	overlayOpenMock: vi.fn(),
}));

vi.mock('@/components/filters/FiltersBar.vue', () => ({
	default: defineComponent({
		name: 'FiltersBarStub',
		setup(_, { slots }) {
			return () => h('div', { 'data-testid': 'filters-bar' }, slots.default?.());
		},
	}),
}));

vi.mock('@/components/analytics/KpiRow.vue', () => ({
	default: defineComponent({
		name: 'KpiRowStub',
		setup() {
			return () => h('div', { 'data-testid': 'kpi-row' }, 'KPI Row');
		},
	}),
}));

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: overlayOpenMock,
	}),
}));

vi.mock('@/lib/admission', () => ({
	getAdmissionsCockpitData: getAdmissionsCockpitDataMock,
	sendAdmissionsCockpitOffer: sendAdmissionsCockpitOfferMock,
	hydrateAdmissionsCockpitRequest: hydrateAdmissionsCockpitRequestMock,
	generateAdmissionsCockpitDepositInvoice: generateAdmissionsCockpitDepositInvoiceMock,
	getAdmissionsCaseThread: getAdmissionsCaseThreadMock,
	markAdmissionsCaseRead: markAdmissionsCaseReadMock,
	sendAdmissionsCaseMessage: sendAdmissionsCaseMessageMock,
}));

import AdmissionsCockpit from '@/pages/staff/admissions/AdmissionsCockpit.vue';

const cleanupFns: Array<() => void> = [];

function buildPayload(
	status: string,
	options: {
		canSendOffer?: boolean;
		canHydrateRequest?: boolean;
		requestName?: string | null;
		requestUrl?: string | null;
		deposit?: Record<string, unknown> | null;
	} = {}
) {
	return {
		config: {
			organizations: ['ORG-1'],
			schools: ['SCH-1'],
		},
		counts: {
			active_applications: 1,
			blocked_applications: 0,
			ready_for_decision: 0,
			accepted_pending_promotion: 1,
			my_open_assignments: 0,
			unread_applicant_replies: 0,
		},
		blockers: [],
		columns: [
			{
				id: 'accepted_pending_promotion',
				title: 'Accepted (Pending Promotion)',
				items: [
					{
						name: 'APP-0001',
						display_name: 'Ada Applicant',
						application_status: 'Approved',
						ready: true,
						school: 'SCH-1',
						program_offering: 'PO-2026',
						top_blockers: [],
						readiness: {
							profile_ok: true,
							documents_ok: true,
							policies_ok: true,
							health_ok: true,
							recommendations_ok: true,
						},
						recommendations: {
							required_total: 0,
							received_total: 0,
							requested_total: 0,
							pending_review_count: 0,
							latest_submitted_on: null,
							first_pending_review: null,
						},
						open_url: '/desk/student-applicant/APP-0001',
						blockers: [],
						interviews: {
							count: 0,
							latest: null,
						},
						comms: {
							thread_name: null,
							unread_count: 0,
							last_message_at: null,
							last_message_preview: '',
							last_message_from: null,
							needs_reply: false,
						},
						aep: {
							has_plan: true,
							name: 'AEP-0001',
							status,
							open_url: '/desk/applicant-enrollment-plan/AEP-0001',
							offer_expires_on: '2026-05-01',
							program_enrollment_request: options.requestName || null,
							program_enrollment_request_url: options.requestUrl || null,
							can_send_offer: Boolean(options.canSendOffer),
							can_hydrate_request: Boolean(options.canHydrateRequest),
							deposit: options.deposit || null,
						},
					},
				],
			},
		],
	};
}

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountAdmissionsCockpit() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(AdmissionsCockpit);
			},
		})
	);

	app.mount(host);
	cleanupFns.push(() => {
		app.unmount();
		host.remove();
	});
}

afterEach(() => {
	getAdmissionsCockpitDataMock.mockReset();
	sendAdmissionsCockpitOfferMock.mockReset();
	hydrateAdmissionsCockpitRequestMock.mockReset();
	generateAdmissionsCockpitDepositInvoiceMock.mockReset();
	getAdmissionsCaseThreadMock.mockReset();
	markAdmissionsCaseReadMock.mockReset();
	sendAdmissionsCaseMessageMock.mockReset();
	overlayOpenMock.mockReset();
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('AdmissionsCockpit', () => {
	it('renders AEP status and refreshes the card after sending an offer', async () => {
		getAdmissionsCockpitDataMock
			.mockResolvedValueOnce(buildPayload('Committee Approved', { canSendOffer: true }))
			.mockResolvedValueOnce(buildPayload('Offer Sent'));
		sendAdmissionsCockpitOfferMock.mockResolvedValue({
			ok: true,
			applicant_enrollment_plan: 'AEP-0001',
			status: 'Offer Sent',
		});

		mountAdmissionsCockpit();
		await flushUi();

		expect(document.body.textContent || '').toContain('AEP · Committee Approved');

		const sendOfferButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Send Offer')
		);
		expect(sendOfferButton).toBeTruthy();

		sendOfferButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(sendAdmissionsCockpitOfferMock).toHaveBeenCalledWith({
			applicant_enrollment_plan: 'AEP-0001',
		});
		expect(getAdmissionsCockpitDataMock).toHaveBeenCalledTimes(2);
		expect(document.body.textContent || '').toContain('AEP · Offer Sent');
		expect(document.body.textContent || '').not.toContain('Send Offer');
	});

	it('generates a deposit invoice from the applicant card and refreshes the cockpit', async () => {
		const pendingDeposit = {
			deposit_required: true,
			deposit_amount: 500,
			deposit_due_date: '2026-05-08',
			terms_source: 'School Default',
			override_status: 'Not Required',
			requires_override_approval: false,
			academic_approved: false,
			finance_approved: false,
			invoice: null,
			invoice_status: null,
			docstatus: null,
			amount: 500,
			paid_amount: 0,
			outstanding_amount: 500,
			due_date: '2026-05-08',
			is_overdue: false,
			is_paid: false,
			blocker_label: 'Deposit not generated',
			can_generate_invoice: true,
		};
		const paidDeposit = {
			...pendingDeposit,
			invoice: 'SI-0001',
			invoice_status: 'Paid',
			docstatus: 1,
			paid_amount: 500,
			outstanding_amount: 0,
			is_paid: true,
			blocker_label: 'Deposit paid',
			can_generate_invoice: false,
		};

		getAdmissionsCockpitDataMock
			.mockResolvedValueOnce(buildPayload('Offer Accepted', { deposit: pendingDeposit }))
			.mockResolvedValueOnce(buildPayload('Offer Accepted', { deposit: paidDeposit }));
		generateAdmissionsCockpitDepositInvoiceMock.mockResolvedValue({
			ok: true,
			created: true,
			applicant_enrollment_plan: 'AEP-0001',
			deposit: paidDeposit,
			invoice: { invoice: 'SI-0001', invoice_status: 'Paid' },
		});

		mountAdmissionsCockpit();
		await flushUi();

		expect(document.body.textContent || '').toContain('Deposit not generated');
		const generateButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Generate Invoice')
		);
		expect(generateButton).toBeTruthy();

		generateButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(generateAdmissionsCockpitDepositInvoiceMock).toHaveBeenCalledWith({
			applicant_enrollment_plan: 'AEP-0001',
		});
		expect(getAdmissionsCockpitDataMock).toHaveBeenCalledTimes(2);
		expect(document.body.textContent || '').toContain('Deposit paid');
		expect(document.body.textContent || '').toContain('SI-0001 · Paid');
		expect(document.body.textContent || '').not.toContain('Generate Invoice');
	});
});
