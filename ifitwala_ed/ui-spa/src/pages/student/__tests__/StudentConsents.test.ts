import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getStudentConsentBoardMock } = vi.hoisted(() => ({
	getStudentConsentBoardMock: vi.fn(),
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

vi.mock('@/lib/services/studentConsent/studentConsentService', () => ({
	getStudentConsentBoard: getStudentConsentBoardMock,
}))

import StudentConsents from '@/pages/student/StudentConsents.vue'

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
				return h(StudentConsents)
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
	getStudentConsentBoardMock.mockReset()
	while (cleanupFns.length) cleanupFns.pop()?.()
	document.body.innerHTML = ''
})

describe('StudentConsents', () => {
	it('renders student action-needed form requests', async () => {
		getStudentConsentBoardMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-22T09:00:00',
				student: { name: 'STU-1' },
			},
			identity: { student: 'STU-1' },
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
						request_title: 'Lab participation consent',
						request_type: 'Mutable Consent',
						decision_mode: 'Grant / Deny',
						student: 'STU-1',
						student_name: 'Amina Example',
						organization: 'ORG-1',
						school: 'University One',
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
		expect(text).toContain('Lab participation consent')
		expect(text).toContain('Action needed')
		expect(text).toContain('Grant / Deny')
	})
})
