import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

import type { AdmissionsTimelineContext } from '@/types/contracts/admissions_timeline/get_admissions_timeline_context';

const {
	getAdmissionsCockpitDataMock,
	getAdmissionsTimelineContextMock,
	getOrCreateAdmissionsCockpitOfferPlanMock,
	sendAdmissionsCockpitOfferMock,
	hydrateAdmissionsCockpitRequestMock,
	generateAdmissionsCockpitDepositInvoiceMock,
	promoteAdmissionsCockpitApplicantMock,
	getAdmissionsCaseThreadMock,
	markAdmissionsCaseReadMock,
	sendAdmissionsCaseMessageMock,
	overlayOpenMock,
} = vi.hoisted(() => ({
	getAdmissionsCockpitDataMock: vi.fn(),
	getAdmissionsTimelineContextMock: vi.fn(),
	getOrCreateAdmissionsCockpitOfferPlanMock: vi.fn(),
	sendAdmissionsCockpitOfferMock: vi.fn(),
	hydrateAdmissionsCockpitRequestMock: vi.fn(),
	generateAdmissionsCockpitDepositInvoiceMock: vi.fn(),
	promoteAdmissionsCockpitApplicantMock: vi.fn(),
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
	getOrCreateAdmissionsCockpitOfferPlan: getOrCreateAdmissionsCockpitOfferPlanMock,
	sendAdmissionsCockpitOffer: sendAdmissionsCockpitOfferMock,
	hydrateAdmissionsCockpitRequest: hydrateAdmissionsCockpitRequestMock,
	generateAdmissionsCockpitDepositInvoice: generateAdmissionsCockpitDepositInvoiceMock,
	promoteAdmissionsCockpitApplicant: promoteAdmissionsCockpitApplicantMock,
	getAdmissionsCaseThread: getAdmissionsCaseThreadMock,
	markAdmissionsCaseRead: markAdmissionsCaseReadMock,
	sendAdmissionsCaseMessage: sendAdmissionsCaseMessageMock,
}));

vi.mock('@/lib/services/admissions/admissionsTimelineService', () => ({
	getAdmissionsTimelineContext: getAdmissionsTimelineContextMock,
}));

import AdmissionsCockpit from '@/pages/staff/admissions/AdmissionsCockpit.vue';

const cleanupFns: Array<() => void> = [];
let originalWindowOpen: typeof window.open;

function buildPayload(
	status: string,
	options: {
		canSendOffer?: boolean;
		canHydrateRequest?: boolean;
		hasPlan?: boolean;
		requestName?: string | null;
		requestUrl?: string | null;
		deposit?: Record<string, unknown> | null;
	} = {}
) {
	const hasPlan = options.hasPlan !== false;
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
							has_plan: hasPlan,
							name: hasPlan ? 'AEP-0001' : null,
							status: hasPlan ? status : null,
							open_url: hasPlan ? '/desk/applicant-enrollment-plan/AEP-0001' : null,
							offer_expires_on: hasPlan ? '2026-05-01' : null,
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

function timelineContext(overrides: Partial<AdmissionsTimelineContext> = {}): AdmissionsTimelineContext {
	return {
		ok: true,
		generated_at: '2026-04-28T08:16:00',
		context: {
			doctype: 'Student Applicant',
			name: 'APP-0001',
			label: 'Ada Applicant',
			organization: 'ORG-1',
			school: 'SCH-1',
			inquiry: 'INQ-0001',
			student_applicant: 'APP-0001',
			conversation: null,
			limit: 40,
		},
		summary: {
			headline: 'Ada Applicant',
			latest_at: '2026-04-28T08:10:00',
			needs_reply: false,
			counts: { applicant: 1 },
			completion_ladder: [
				{ id: 'applicant', label: 'Applicant', state: 'done', source: 'Student Applicant' },
				{ id: 'offer_sent', label: 'Offer Sent', state: 'current', source: 'Applicant Enrollment Plan' },
			],
		},
		items: [
			{
				id: 'applicant:APP-0001',
				kind: 'applicant',
				source_doctype: 'Student Applicant',
				source_name: 'APP-0001',
				occurred_at: '2026-04-28T08:10:00',
				title: 'Application in review',
				summary: 'Admissions team is preparing the offer.',
				actor: 'System',
				visibility: 'staff',
				context_labels: {},
				open_url: '/desk/student-applicant/APP-0001',
				actions: [],
			},
		],
		actions: [{ id: 'message_family', label: 'Message Family', enabled: true }],
		has_more: false,
		sources: { student_applicants: 1 },
		...overrides,
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

beforeEach(() => {
	originalWindowOpen = window.open;
	window.open = vi.fn() as typeof window.open;
	getAdmissionsTimelineContextMock.mockResolvedValue(timelineContext());
});

afterEach(() => {
	getAdmissionsCockpitDataMock.mockReset();
	getAdmissionsTimelineContextMock.mockReset();
	getOrCreateAdmissionsCockpitOfferPlanMock.mockReset();
	sendAdmissionsCockpitOfferMock.mockReset();
	hydrateAdmissionsCockpitRequestMock.mockReset();
	generateAdmissionsCockpitDepositInvoiceMock.mockReset();
	promoteAdmissionsCockpitApplicantMock.mockReset();
	getAdmissionsCaseThreadMock.mockReset();
	markAdmissionsCaseReadMock.mockReset();
	sendAdmissionsCaseMessageMock.mockReset();
	overlayOpenMock.mockReset();
	window.open = originalWindowOpen;
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

	it('opens the schedule interview overlay from the applicant card', async () => {
		getAdmissionsCockpitDataMock.mockResolvedValue(buildPayload('Committee Approved'));

		mountAdmissionsCockpit();
		await flushUi();

		const scheduleButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Schedule Interview')
		);
		expect(scheduleButton).toBeTruthy();

		scheduleButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(overlayOpenMock).toHaveBeenCalledWith('admissions-interview-schedule', {
			studentApplicant: 'APP-0001',
			applicantName: 'Ada Applicant',
			school: 'SCH-1',
		});
		expect(document.body.textContent || '').not.toContain('Create Interview');
	});

	it('opens the applicant timeline drawer from the card without exposing source ledger names', async () => {
		getAdmissionsCockpitDataMock.mockResolvedValue(buildPayload('Committee Approved'));
		getAdmissionsTimelineContextMock.mockResolvedValue(timelineContext());

		mountAdmissionsCockpit();
		await flushUi();

		const timelineButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').trim().includes('Timeline')
		);
		expect(timelineButton).toBeTruthy();

		timelineButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(getAdmissionsTimelineContextMock).toHaveBeenCalledWith({
			context_doctype: 'Student Applicant',
			context_name: 'APP-0001',
			limit: 40,
		});
		expect(document.body.textContent || '').toContain('Admissions Timeline');
		expect(document.body.textContent || '').toContain('Admissions team is preparing the offer.');
		expect(document.body.textContent || '').not.toContain('Student Applicant');
	});

	it('opens the admissions visit overlay from the timeline drawer', async () => {
		getAdmissionsCockpitDataMock.mockResolvedValue(buildPayload('Committee Approved'));
		getAdmissionsTimelineContextMock.mockResolvedValue(
			timelineContext({
				actions: [{ id: 'schedule_visit', label: 'Schedule Visit', enabled: true }],
			})
		);

		mountAdmissionsCockpit();
		await flushUi();

		const timelineButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').trim().includes('Timeline')
		);
		expect(timelineButton).toBeTruthy();

		timelineButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		const visitButton = document.querySelector(
			'[data-testid="admissions-timeline-action-schedule_visit"]'
		);
		expect(visitButton).toBeTruthy();

		visitButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(overlayOpenMock).toHaveBeenCalledWith('admissions-visit-schedule', {
			studentApplicant: 'APP-0001',
			visitorName: 'Ada Applicant',
			school: 'SCH-1',
		});
	});

	it('opens or creates the enrollment offer plan from the timeline drawer', async () => {
		getAdmissionsCockpitDataMock
			.mockResolvedValueOnce(buildPayload('Draft', { hasPlan: false }))
			.mockResolvedValueOnce(buildPayload('Draft'));
		getAdmissionsTimelineContextMock.mockResolvedValue(
			timelineContext({
				actions: [{ id: 'manage_offer', label: 'Manage Offer', enabled: true }],
			})
		);
		getOrCreateAdmissionsCockpitOfferPlanMock.mockResolvedValue({
			ok: true,
			created: true,
			student_applicant: 'APP-0001',
			applicant_enrollment_plan: 'AEP-0001',
			status: 'Draft',
			open_url: '/desk/applicant-enrollment-plan/AEP-0001',
		});

		mountAdmissionsCockpit();
		await flushUi();

		const timelineButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').trim().includes('Timeline')
		);
		timelineButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		const manageOfferButton = document.querySelector(
			'[data-testid="admissions-timeline-action-manage_offer"]'
		);
		expect(manageOfferButton).toBeTruthy();

		manageOfferButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(getOrCreateAdmissionsCockpitOfferPlanMock).toHaveBeenCalledWith({
			student_applicant: 'APP-0001',
		});
		expect(getAdmissionsCockpitDataMock).toHaveBeenCalledTimes(2);
		expect(document.body.textContent || '').toContain('Offer plan is ready on the applicant card.');
	});

	it('checks a pending deposit from the timeline drawer', async () => {
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
		const invoicedDeposit = {
			...pendingDeposit,
			invoice: 'SI-0001',
			invoice_status: 'Draft',
			can_generate_invoice: false,
		};

		getAdmissionsCockpitDataMock
			.mockResolvedValueOnce(buildPayload('Offer Accepted', { deposit: pendingDeposit }))
			.mockResolvedValueOnce(buildPayload('Offer Accepted', { deposit: invoicedDeposit }));
		getAdmissionsTimelineContextMock.mockResolvedValue(
			timelineContext({
				actions: [{ id: 'check_deposit', label: 'Check Deposit', enabled: true }],
			})
		);
		generateAdmissionsCockpitDepositInvoiceMock.mockResolvedValue({
			ok: true,
			created: true,
			applicant_enrollment_plan: 'AEP-0001',
			deposit: invoicedDeposit,
			invoice: { invoice: 'SI-0001', invoice_status: 'Draft' },
		});

		mountAdmissionsCockpit();
		await flushUi();

		const timelineButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').trim().includes('Timeline')
		);
		timelineButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		const depositButton = document.querySelector(
			'[data-testid="admissions-timeline-action-check_deposit"]'
		);
		expect(depositButton).toBeTruthy();

		depositButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(generateAdmissionsCockpitDepositInvoiceMock).toHaveBeenCalledWith({
			applicant_enrollment_plan: 'AEP-0001',
		});
		expect(getAdmissionsCockpitDataMock).toHaveBeenCalledTimes(2);
	});

	it('promotes an approved applicant from the timeline drawer', async () => {
		getAdmissionsCockpitDataMock
			.mockResolvedValueOnce(buildPayload('Offer Accepted'))
			.mockResolvedValueOnce(buildPayload('Offer Accepted'));
		getAdmissionsTimelineContextMock.mockResolvedValue(
			timelineContext({
				actions: [{ id: 'promote', label: 'Promote', enabled: true }],
			})
		);
		promoteAdmissionsCockpitApplicantMock.mockResolvedValue({
			ok: true,
			student_applicant: 'APP-0001',
			student: 'STU-0001',
			status: 'Promoted',
		});

		mountAdmissionsCockpit();
		await flushUi();

		const timelineButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').trim().includes('Timeline')
		);
		timelineButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		const promoteButton = document.querySelector('[data-testid="admissions-timeline-action-promote"]');
		expect(promoteButton).toBeTruthy();

		promoteButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(promoteAdmissionsCockpitApplicantMock).toHaveBeenCalledWith({
			student_applicant: 'APP-0001',
		});
		expect(getAdmissionsCockpitDataMock).toHaveBeenCalledTimes(2);
	});
});
