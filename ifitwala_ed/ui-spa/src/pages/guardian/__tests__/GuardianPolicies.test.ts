// ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getGuardianPolicyOverviewMock, acknowledgeGuardianPolicyMock, toastSuccessMock, toastErrorMock } =
	vi.hoisted(() => ({
		getGuardianPolicyOverviewMock: vi.fn(),
		acknowledgeGuardianPolicyMock: vi.fn(),
		toastSuccessMock: vi.fn(),
		toastErrorMock: vi.fn(),
	}))

vi.mock('frappe-ui', () => ({
	toast: {
		success: toastSuccessMock,
		error: toastErrorMock,
	},
}))

vi.mock('@/lib/services/guardianPolicy/guardianPolicyService', () => ({
	getGuardianPolicyOverview: getGuardianPolicyOverviewMock,
	acknowledgeGuardianPolicy: acknowledgeGuardianPolicyMock,
}))

import GuardianPolicies from '@/pages/guardian/GuardianPolicies.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountGuardianPolicies() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(GuardianPolicies)
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
	getGuardianPolicyOverviewMock.mockReset()
	acknowledgeGuardianPolicyMock.mockReset()
	toastSuccessMock.mockReset()
	toastErrorMock.mockReset()
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('GuardianPolicies', () => {
	it('renders pending guardian policy rows from the canonical payload', async () => {
		getGuardianPolicyOverviewMock.mockResolvedValue({
			meta: {
				generated_at: '2026-03-13T09:00:00',
				guardian: { name: 'GRD-0001' },
			},
			family: {
				children: [{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' }],
			},
			counts: {
				total_policies: 2,
				acknowledged_policies: 1,
				pending_policies: 1,
			},
			rows: [
				{
					policy_name: 'POL-1',
					policy_key: 'privacy',
					policy_title: 'Privacy Policy',
					policy_category: 'Privacy & Data Protection',
					policy_version: 'VER-1',
					version_label: 'v1',
					organization: 'ORG-1',
					school: 'SCHOOL-1',
					description: 'Review privacy expectations.',
					policy_text: 'Policy text',
					effective_from: '2026-03-01',
					effective_to: '',
					approved_on: '2026-03-01 09:00:00',
					ack_context_doctype: 'Guardian',
					ack_context_name: 'GRD-0001',
					is_acknowledged: false,
					acknowledged_at: '',
					acknowledged_by: '',
				},
			],
		})

		mountGuardianPolicies()
		await flushUi()

		const text = document.body.textContent || ''
		expect(getGuardianPolicyOverviewMock).toHaveBeenCalledTimes(1)
		expect(text).toContain('Guardian Policies')
		expect(text).toContain('Privacy Policy')
		expect(text).toContain('Pending acknowledgement')
		expect(text).toContain('Review privacy expectations.')
	})

	it('acknowledges a pending policy and reloads the overview', async () => {
		getGuardianPolicyOverviewMock
			.mockResolvedValueOnce({
				meta: { generated_at: '2026-03-13T09:00:00', guardian: { name: 'GRD-0001' } },
				family: { children: [] },
				counts: { total_policies: 1, acknowledged_policies: 0, pending_policies: 1 },
				rows: [
					{
						policy_name: 'POL-1',
						policy_key: 'privacy',
						policy_title: 'Privacy Policy',
						policy_category: 'Privacy & Data Protection',
						policy_version: 'VER-1',
						version_label: 'v1',
						organization: 'ORG-1',
						school: 'SCHOOL-1',
						description: '',
						policy_text: 'Policy text',
						effective_from: '',
						effective_to: '',
						approved_on: '',
						ack_context_doctype: 'Guardian',
						ack_context_name: 'GRD-0001',
						is_acknowledged: false,
						acknowledged_at: '',
						acknowledged_by: '',
					},
				],
			})
			.mockResolvedValueOnce({
				meta: { generated_at: '2026-03-13T09:01:00', guardian: { name: 'GRD-0001' } },
				family: { children: [] },
				counts: { total_policies: 1, acknowledged_policies: 1, pending_policies: 0 },
				rows: [
					{
						policy_name: 'POL-1',
						policy_key: 'privacy',
						policy_title: 'Privacy Policy',
						policy_category: 'Privacy & Data Protection',
						policy_version: 'VER-1',
						version_label: 'v1',
						organization: 'ORG-1',
						school: 'SCHOOL-1',
						description: '',
						policy_text: 'Policy text',
						effective_from: '',
						effective_to: '',
						approved_on: '',
						ack_context_doctype: 'Guardian',
						ack_context_name: 'GRD-0001',
						is_acknowledged: true,
						acknowledged_at: '2026-03-13 09:01:00',
						acknowledged_by: 'guardian@example.com',
					},
				],
			})
		acknowledgeGuardianPolicyMock.mockResolvedValue({
			ok: true,
			status: 'acknowledged',
			acknowledgement_name: 'ACK-1',
			policy_version: 'VER-1',
		})

		mountGuardianPolicies()
		await flushUi()

		const button = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Acknowledge')
		)
		button?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(acknowledgeGuardianPolicyMock).toHaveBeenCalledWith({ policy_version: 'VER-1' })
		expect(getGuardianPolicyOverviewMock).toHaveBeenCalledTimes(2)
		expect(toastSuccessMock).toHaveBeenCalled()
	})
})
