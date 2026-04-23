import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { loadDetailMock, submitDecisionMock, overlayOpenMock } = vi.hoisted(() => ({
	loadDetailMock: vi.fn(),
	submitDecisionMock: vi.fn(),
	overlayOpenMock: vi.fn(),
}))

vi.mock('vue-router', async () => {
	const { defineComponent, h } = await import('vue')

	return {
		RouterLink: defineComponent({
			name: 'RouterLinkStub',
			setup(_, { slots }) {
				return () => h('a', {}, slots.default?.())
			},
		}),
	}
})

vi.mock('frappe-ui', () => ({
	toast: {
		success: vi.fn(),
	},
}))

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: overlayOpenMock,
	}),
}))

vi.mock('@/components/attachments/AttachmentPreviewCard.vue', async () => {
	const { defineComponent, h } = await import('vue')
	return {
		default: defineComponent({
			name: 'AttachmentPreviewCardStub',
			props: {
				title: {
					type: String,
					required: false,
					default: '',
				},
			},
			setup(props) {
				return () => h('div', { 'data-testid': 'attachment-preview-card' }, props.title)
			},
		}),
	}
})

import ConsentDetailView from '@/components/family_consent/ConsentDetailView.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountComponent() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(ConsentDetailView, {
					portalLabel: 'Guardian Portal',
					titleLabel: 'Form detail',
					backRouteName: 'guardian-consents',
					requestKey: 'FCR-1',
					studentId: 'STU-1',
					loadDetail: loadDetailMock,
					submitDecision: submitDecisionMock,
				})
			},
		})
	)

	app.mount(host)
	cleanupFns.push(() => {
		app.unmount()
		host.remove()
	})
}

afterEach(() => {
	loadDetailMock.mockReset()
	submitDecisionMock.mockReset()
	overlayOpenMock.mockReset()
	while (cleanupFns.length) cleanupFns.pop()?.()
	document.body.innerHTML = ''
})

describe('ConsentDetailView', () => {
	it('renders the governed request attachment section when a source attachment preview is present', async () => {
		loadDetailMock.mockResolvedValue({
			meta: { generated_at: '2026-04-22T09:00:00' },
			request: {
				family_consent_request: 'FCR-1',
				request_key: 'FCR-1',
				request_title: 'Field trip approval',
				request_type: 'One-off Permission Request',
				status: 'Published',
				decision_mode: 'Approve / Decline',
				completion_channel_mode: 'Portal Only',
				request_text: '<p>Trip details</p>',
				source_attachment_preview: {
					kind: 'pdf',
					preview_mode: 'pdf_embed',
					display_name: 'Field trip packet',
					open_url: '/api/method/ifitwala_ed.api.file_access.open_family_consent_request_source_attachment?request_key=FCR-1&student=STU-1',
					preview_url: '/api/method/ifitwala_ed.api.file_access.preview_family_consent_request_source_attachment?request_key=FCR-1&student=STU-1',
				},
				effective_from: '2026-04-20',
				effective_to: '2026-04-26',
				due_on: '2026-04-25',
				requires_typed_signature: 1,
				requires_attestation: 1,
			},
			target: {
				student: 'STU-1',
				student_name: 'Amina Example',
				organization: 'ORG-1',
				school: 'School One',
				current_status: 'pending',
				current_status_label: 'Action needed',
			},
			signer: {
				doctype: 'Guardian',
				name: 'GRD-1',
				expected_signature_name: 'Amira Example',
			},
			fields: [],
			history: [],
		})

		mountComponent()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('Reference document')
		expect(text).toContain('Field trip packet')
	})
})
