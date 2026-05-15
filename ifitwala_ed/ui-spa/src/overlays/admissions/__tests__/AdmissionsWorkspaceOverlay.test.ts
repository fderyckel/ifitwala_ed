import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	getApplicantWorkspaceMock,
	getInterviewWorkspaceMock,
	getRecommendationReviewPayloadMock,
	reviewApplicantDocumentSubmissionMock,
	saveMyInterviewFeedbackMock,
	setDocumentRequirementOverrideMock,
	overlayOpenMock,
} = vi.hoisted(() => ({
	getApplicantWorkspaceMock: vi.fn(),
	getInterviewWorkspaceMock: vi.fn(),
	getRecommendationReviewPayloadMock: vi.fn(),
	reviewApplicantDocumentSubmissionMock: vi.fn(),
	saveMyInterviewFeedbackMock: vi.fn(),
	setDocumentRequirementOverrideMock: vi.fn(),
	overlayOpenMock: vi.fn(),
}));

vi.mock('@headlessui/vue', () => {
	const passthrough = (tag = 'div') =>
		defineComponent({
			name: `Stub${tag}`,
			props: ['as', 'show'],
			setup(props, { slots, attrs }) {
				return () => {
					if (props.show === false) return null;
					return h(props.as && props.as !== 'template' ? props.as : tag, attrs, slots.default?.());
				};
			},
		});

	return {
		Dialog: passthrough('div'),
		DialogPanel: passthrough('div'),
		DialogTitle: passthrough('h2'),
		TransitionChild: passthrough('div'),
		TransitionRoot: passthrough('div'),
	};
});

vi.mock('frappe-ui', () => ({
	FeatherIcon: defineComponent({
		name: 'FeatherIconStub',
		setup() {
			return () => h('span');
		},
	}),
}));

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: overlayOpenMock,
	}),
}));

vi.mock('@/lib/services/admissions/admissionsWorkspaceService', () => ({
	getApplicantWorkspace: getApplicantWorkspaceMock,
	getInterviewWorkspace: getInterviewWorkspaceMock,
	getRecommendationReviewPayload: getRecommendationReviewPayloadMock,
	reviewApplicantDocumentSubmission: reviewApplicantDocumentSubmissionMock,
	saveMyInterviewFeedback: saveMyInterviewFeedbackMock,
	setDocumentRequirementOverride: setDocumentRequirementOverrideMock,
}));

import AdmissionsWorkspaceOverlay from '@/overlays/admissions/AdmissionsWorkspaceOverlay.vue';
import type { ApplicantWorkspaceResponse } from '@/types/contracts/admissions/admissions_workspace';

const cleanupFns: Array<() => void> = [];

function buildWorkspace(reviewStatus: string): ApplicantWorkspaceResponse {
	return {
		ok: true,
		applicant: {
			name: 'APP-0001',
			display_name: 'Ada Applicant',
			application_status: 'Under Review',
			guardians: [],
		},
		timeline: [],
		document_review: {
			ok: reviewStatus === 'Approved',
			missing: [],
			unapproved: reviewStatus === 'Pending' ? ['Passport'] : [],
			required: ['Passport'],
			can_review_submissions: true,
			can_manage_overrides: false,
			required_rows: [
				{
					applicant_document: 'ADOC-0001',
					document_type: 'passport',
					label: 'Passport',
					is_required: true,
					required_count: 1,
					uploaded_count: 1,
					approved_count: reviewStatus === 'Approved' ? 1 : 0,
					review_status: reviewStatus,
					items: [
						{
							name: 'ITEM-0001',
							item_label: 'passport.pdf',
							review_status: reviewStatus,
							file_name: 'passport.pdf',
							open_url: '/api/open/passport',
						},
					],
				},
			],
			uploaded_rows: [
				{
					applicant_document: 'ADOC-0001',
					applicant_document_item: 'ITEM-0001',
					document_type: 'passport',
					label: 'Passport',
					document_label: 'Passport',
					item_label: 'passport.pdf',
					is_required: true,
					required_count: 1,
					uploaded_count: 1,
					approved_count: reviewStatus === 'Approved' ? 1 : 0,
					review_status: reviewStatus,
					file_name: 'passport.pdf',
					open_url: '/api/open/passport',
				},
			],
		},
		recommendations: {
			summary: {
				required_total: 0,
				received_total: 0,
				requested_total: 0,
				pending_review_count: 0,
			},
			requests: [],
			submissions: [],
			review_rows: [],
		},
		interviews: [],
	};
}

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountOverlay() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(AdmissionsWorkspaceOverlay, {
					open: true,
					mode: 'applicant',
					studentApplicant: 'APP-0001',
				});
			},
		})
	);

	app.mount(host);
	cleanupFns.push(() => {
		app.unmount();
		host.remove();
	});
}

function buttonLabels() {
	return Array.from(document.querySelectorAll('button')).map(button =>
		(button.textContent || '').trim()
	);
}

afterEach(() => {
	getApplicantWorkspaceMock.mockReset();
	getInterviewWorkspaceMock.mockReset();
	getRecommendationReviewPayloadMock.mockReset();
	reviewApplicantDocumentSubmissionMock.mockReset();
	saveMyInterviewFeedbackMock.mockReset();
	setDocumentRequirementOverrideMock.mockReset();
	overlayOpenMock.mockReset();
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('AdmissionsWorkspaceOverlay', () => {
	it('does not show review actions for an already approved submitted file', async () => {
		getApplicantWorkspaceMock.mockResolvedValue(buildWorkspace('Approved'));

		mountOverlay();
		await flushUi();

		expect(document.body.textContent || '').toContain('Approved');
		expect(buttonLabels()).not.toContain('Approve');
		expect(buttonLabels()).not.toContain('Request Changes');
		expect(buttonLabels()).not.toContain('Reject');
	});

	it('keeps review actions available for a pending submitted file', async () => {
		getApplicantWorkspaceMock.mockResolvedValue(buildWorkspace('Pending'));

		mountOverlay();
		await flushUi();

		expect(buttonLabels()).toContain('Approve');
		expect(buttonLabels()).toContain('Request Changes');
		expect(buttonLabels()).toContain('Reject');
	});
});
