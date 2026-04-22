import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getGuardianConsentBoardMock } = vi.hoisted(() => ({
	getGuardianConsentBoardMock: vi.fn(),
}))

vi.mock('vue-router', async () => {
	const { defineComponent, h } = await import('vue')

	return {
		RouterLink: defineComponent({
			name: 'RouterLinkStub',
			props: {
				to: {
					type: [String, Object],
					required: false,
					default: '',
				},
			},
			setup(_, { slots }) {
				return () => h('a', {}, slots.default?.())
			},
		}),
	}
})

vi.mock('@/lib/services/guardianConsent/guardianConsentService', () => ({
	getGuardianConsentBoard: getGuardianConsentBoardMock,
}))

import GuardianConsents from '@/pages/guardian/GuardianConsents.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountPage() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(GuardianConsents)
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
	getGuardianConsentBoardMock.mockReset()
	while (cleanupFns.length) cleanupFns.pop()?.()
	document.body.innerHTML = ''
})

describe('GuardianConsents', () => {
	it('renders guardian action-needed form requests', async () => {
		getGuardianConsentBoardMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-22T09:00:00',
				guardian: { name: 'GRD-1' },
			},
			family: { children: [{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' }] },
			counts: {
				pending: 1,
				completed: 0,
				declined: 0,
				withdrawn: 0,
				expired: 0,
				overdue: 0,
			},
			groups: {
				action_needed: [
					{
						request_key: 'FCR-1',
						request_title: 'Field trip consent',
						request_type: 'One-off Permission Request',
						decision_mode: 'Approve / Decline',
						student: 'STU-1',
						student_name: 'Amina Example',
						organization: 'ORG-1',
						school: 'School One',
						due_on: '2026-04-25',
						effective_from: '2026-04-20',
						effective_to: '2026-04-26',
						current_status: 'pending',
						current_status_label: 'Action needed',
						last_decision_at: '',
						last_decision_by: '',
						completion_channel_mode: 'Portal Only',
					},
				],
				completed: [],
				declined_or_withdrawn: [],
				expired: [],
			},
		})

		mountPage()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('Forms & Signatures')
		expect(text).toContain('Field trip consent')
		expect(text).toContain('Amina Example')
		expect(text).toContain('Action needed')
	})
})
