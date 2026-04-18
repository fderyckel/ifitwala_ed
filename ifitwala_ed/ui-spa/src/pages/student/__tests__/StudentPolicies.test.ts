// ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentPolicies.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getStudentPolicyOverviewMock, acknowledgeStudentPolicyMock, toastSuccessMock, toastErrorMock } =
	vi.hoisted(() => ({
		getStudentPolicyOverviewMock: vi.fn(),
		acknowledgeStudentPolicyMock: vi.fn(),
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

vi.mock('@/lib/services/studentPolicy/studentPolicyService', () => ({
	getStudentPolicyOverview: getStudentPolicyOverviewMock,
	acknowledgeStudentPolicy: acknowledgeStudentPolicyMock,
}))

vi.mock('vue-router', () => ({
	useRoute: () => ({
		query: routeQueryMock,
	}),
}))

import StudentPolicies from '@/pages/student/StudentPolicies.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountStudentPolicies() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(StudentPolicies)
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
	getStudentPolicyOverviewMock.mockReset()
	acknowledgeStudentPolicyMock.mockReset()
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

describe('StudentPolicies', () => {
	it('renders pending student policy rows from the canonical payload', async () => {
		getStudentPolicyOverviewMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-13T09:00:00',
				student: { name: 'STU-0001' },
			},
			identity: { student: 'STU-0001', user: 'student@example.com' },
			counts: {
				total_policies: 2,
				acknowledged_policies: 1,
				pending_policies: 1,
			},
			rows: [
				{
					policy_name: 'POL-1',
					policy_key: 'student_handbook',
					policy_title: 'Student Handbook',
					policy_category: 'Handbooks',
					policy_version: 'VER-1',
					version_label: '2026',
					organization: 'ORG-1',
					school: 'SCHOOL-1',
					description: 'Review handbook expectations.',
					policy_text: '<h2>Student Handbook</h2><p>Policy text</p>',
					effective_from: '2026-04-01',
					effective_to: '',
					approved_on: '2026-04-01 09:00:00',
					expected_signature_name: 'Amina Example',
					acknowledgement_clauses: [],
					ack_context_doctype: 'Student',
					ack_context_name: 'STU-0001',
					is_acknowledged: false,
					acknowledged_at: '',
					acknowledged_by: '',
				},
			],
		})

		mountStudentPolicies()
		await flushUi()

		const text = document.body.textContent || ''
		expect(getStudentPolicyOverviewMock).toHaveBeenCalledTimes(1)
		expect(text).toContain('Student Policies')
		expect(text).toContain('Student Handbook')
		expect(text).toContain('Pending acknowledgement')
		expect(text).toContain('Review handbook expectations.')
		expect(document.querySelector('.policy-richtext h2')?.textContent).toBe('Student Handbook')
		expect(document.body.innerHTML).not.toContain('&lt;h2&gt;')
	})

	it('acknowledges a pending student policy and reloads the overview', async () => {
		getStudentPolicyOverviewMock
			.mockResolvedValueOnce({
				meta: { generated_at: '2026-04-13T09:00:00', student: { name: 'STU-0001' } },
				identity: { student: 'STU-0001', user: 'student@example.com' },
				counts: { total_policies: 1, acknowledged_policies: 0, pending_policies: 1 },
				rows: [
					{
						policy_name: 'POL-1',
						policy_key: 'student_handbook',
						policy_title: 'Student Handbook',
						policy_category: 'Handbooks',
						policy_version: 'VER-1',
						version_label: '2026',
						organization: 'ORG-1',
						school: 'SCHOOL-1',
						description: '',
						policy_text: '<p>Policy text</p>',
						effective_from: '',
						effective_to: '',
						approved_on: '',
						expected_signature_name: 'Amina Example',
						acknowledgement_clauses: [],
						ack_context_doctype: 'Student',
						ack_context_name: 'STU-0001',
						is_acknowledged: false,
						acknowledged_at: '',
						acknowledged_by: '',
					},
				],
			})
			.mockResolvedValueOnce({
				meta: { generated_at: '2026-04-13T09:01:00', student: { name: 'STU-0001' } },
				identity: { student: 'STU-0001', user: 'student@example.com' },
				counts: { total_policies: 1, acknowledged_policies: 1, pending_policies: 0 },
				rows: [
					{
						policy_name: 'POL-1',
						policy_key: 'student_handbook',
						policy_title: 'Student Handbook',
						policy_category: 'Handbooks',
						policy_version: 'VER-1',
						version_label: '2026',
						organization: 'ORG-1',
						school: 'SCHOOL-1',
						description: '',
						policy_text: '<p>Policy text</p>',
						effective_from: '',
						effective_to: '',
						approved_on: '',
						expected_signature_name: 'Amina Example',
						acknowledgement_clauses: [],
						ack_context_doctype: 'Student',
						ack_context_name: 'STU-0001',
						is_acknowledged: true,
						acknowledged_at: '2026-04-13 09:01:00',
						acknowledged_by: 'student@example.com',
					},
				],
			})
		acknowledgeStudentPolicyMock.mockResolvedValue({
			ok: true,
			status: 'acknowledged',
			acknowledgement_name: 'ACK-1',
			policy_version: 'VER-1',
		})

		mountStudentPolicies()
		await flushUi()

		const input = document.querySelector('input[type="text"]') as HTMLInputElement
		input.value = 'Amina Example'
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

		expect(acknowledgeStudentPolicyMock).toHaveBeenCalledWith({
			policy_version: 'VER-1',
			typed_signature_name: 'Amina Example',
			attestation_confirmed: 1,
			checked_clause_names: [],
		})
		expect(getStudentPolicyOverviewMock).toHaveBeenCalledTimes(2)
		expect(toastSuccessMock).toHaveBeenCalled()
	})

	it('focuses the requested policy version from the route query', async () => {
		routeQueryMock.policy_version = 'VER-2'
		getStudentPolicyOverviewMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-13T09:00:00',
				student: { name: 'STU-0001' },
			},
			identity: { student: 'STU-0001', user: 'student@example.com' },
			counts: {
				total_policies: 2,
				acknowledged_policies: 1,
				pending_policies: 1,
			},
			rows: [
				{
					policy_name: 'POL-1',
					policy_key: 'student_handbook',
					policy_title: 'Student Handbook',
					policy_category: 'Handbooks',
					policy_version: 'VER-1',
					version_label: '2026',
					organization: 'ORG-1',
					school: 'SCHOOL-1',
					description: '',
					policy_text: '<p>Policy text</p>',
					effective_from: '',
					effective_to: '',
					approved_on: '',
					expected_signature_name: 'Amina Example',
					acknowledgement_clauses: [],
					ack_context_doctype: 'Student',
					ack_context_name: 'STU-0001',
					is_acknowledged: true,
					acknowledged_at: '2026-04-13 09:01:00',
					acknowledged_by: 'student@example.com',
				},
				{
					policy_name: 'POL-2',
					policy_key: 'device_policy',
					policy_title: 'Device Policy',
					policy_category: 'Operations',
					policy_version: 'VER-2',
					version_label: '2026',
					organization: 'ORG-1',
					school: 'SCHOOL-1',
					description: 'Focus this policy.',
					policy_text: '<p>Device policy</p>',
					effective_from: '',
					effective_to: '',
					approved_on: '',
					expected_signature_name: 'Amina Example',
					acknowledgement_clauses: [],
					ack_context_doctype: 'Student',
					ack_context_name: 'STU-0001',
					is_acknowledged: false,
					acknowledged_at: '',
					acknowledged_by: '',
				},
			],
		})

		mountStudentPolicies()
		await flushUi()

		const focusedRow = document.querySelector('[data-policy-version="VER-2"]')
		expect(focusedRow?.getAttribute('data-policy-focused')).toBe('true')
	})
})
