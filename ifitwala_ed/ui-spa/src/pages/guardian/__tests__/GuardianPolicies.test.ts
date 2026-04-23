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
const { routeQueryMock } = vi.hoisted(() => ({
	routeQueryMock: {} as Record<string, unknown>,
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

vi.mock('vue-router', () => ({
	useRoute: () => ({
		query: routeQueryMock,
	}),
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
	Object.keys(routeQueryMock).forEach((key) => {
		delete routeQueryMock[key]
	})
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
					policy_text: '<h2>Guardian Privacy Policy</h2><p>Policy text</p>',
					effective_from: '2026-03-01',
					effective_to: '',
					approved_on: '2026-03-01 09:00:00',
					expected_signature_name: 'Mariam Example',
					acknowledgement_clauses: [],
					guardian_acknowledgement_mode: 'Family Acknowledgement',
					scope_label: 'Family acknowledgement',
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
		expect(document.querySelector('.policy-richtext h2')?.textContent).toBe('Guardian Privacy Policy')
		expect(document.body.innerHTML).not.toContain('&lt;h2&gt;')
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
						policy_text: '<p>Policy text</p>',
						effective_from: '',
						effective_to: '',
						approved_on: '',
						expected_signature_name: 'Mariam Example',
						acknowledgement_clauses: [],
						guardian_acknowledgement_mode: 'Family Acknowledgement',
						scope_label: 'Family acknowledgement',
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
						policy_text: '<p>Policy text</p>',
						effective_from: '',
						effective_to: '',
						approved_on: '',
						expected_signature_name: 'Mariam Example',
						acknowledgement_clauses: [],
						guardian_acknowledgement_mode: 'Family Acknowledgement',
						scope_label: 'Family acknowledgement',
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

		const input = document.querySelector('input[type="text"]') as HTMLInputElement
		input.value = 'Mariam Example'
		input.dispatchEvent(new Event('input', { bubbles: true }))
		await flushUi()

		const checkbox = Array.from(document.querySelectorAll('input[type="checkbox"]')).find(
			node => !(node as HTMLInputElement).disabled
		) as HTMLInputElement | undefined
		checkbox!.checked = true
		checkbox!.dispatchEvent(new Event('change', { bubbles: true }))
		await flushUi()

		const button = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Sign and acknowledge policy')
		)
		button?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(acknowledgeGuardianPolicyMock).toHaveBeenCalledWith({
			policy_version: 'VER-1',
			context_name: 'GRD-0001',
			typed_signature_name: 'Mariam Example',
			attestation_confirmed: 1,
			checked_clause_names: [],
		})
		expect(getGuardianPolicyOverviewMock).toHaveBeenCalledTimes(2)
		expect(toastSuccessMock).toHaveBeenCalled()
	})

	it('focuses the requested policy version from the route query', async () => {
		routeQueryMock.policy_version = 'VER-2'
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
					description: '',
					policy_text: '<p>Policy text</p>',
					effective_from: '',
					effective_to: '',
					approved_on: '',
					expected_signature_name: 'Mariam Example',
					acknowledgement_clauses: [],
					guardian_acknowledgement_mode: 'Family Acknowledgement',
					scope_label: 'Family acknowledgement',
					ack_context_doctype: 'Guardian',
					ack_context_name: 'GRD-0001',
					is_acknowledged: true,
					acknowledged_at: '2026-03-13 09:01:00',
					acknowledged_by: 'guardian@example.com',
				},
				{
					policy_name: 'POL-2',
					policy_key: 'handbook',
					policy_title: 'Family Handbook',
					policy_category: 'Handbooks',
					policy_version: 'VER-2',
					version_label: 'v2',
					organization: 'ORG-1',
					school: 'SCHOOL-1',
					description: 'Focus this policy.',
					policy_text: '<p>Handbook</p>',
					effective_from: '',
					effective_to: '',
					approved_on: '',
					expected_signature_name: 'Mariam Example',
					acknowledgement_clauses: [],
					guardian_acknowledgement_mode: 'Child Acknowledgement',
					scope_label: 'Amina Example',
					ack_context_doctype: 'Student',
					ack_context_name: 'STU-1',
					is_acknowledged: false,
					acknowledged_at: '',
					acknowledged_by: '',
				},
			],
		})

		mountGuardianPolicies()
		await flushUi()

		const focusedRow = document.querySelector('[data-policy-version="VER-2"]')
		expect(focusedRow?.getAttribute('data-policy-focused')).toBe('true')
	})
})
