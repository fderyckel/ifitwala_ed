import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const {
	searchFollowUpUsersMock,
	submitStudentLogFollowUpMock,
	reviewStudentLogOutcomeMock,
} = vi.hoisted(() => ({
	searchFollowUpUsersMock: vi.fn(),
	submitStudentLogFollowUpMock: vi.fn(),
	reviewStudentLogOutcomeMock: vi.fn(),
}))

vi.mock('@/lib/services/studentLog/studentLogService', () => ({
	createStudentLogService: () => ({
		searchFollowUpUsers: searchFollowUpUsersMock,
	}),
}))

vi.mock('@/lib/services/focus/focusService', () => ({
	createFocusService: () => ({
		submitStudentLogFollowUp: submitStudentLogFollowUpMock,
		reviewStudentLogOutcome: reviewStudentLogOutcomeMock,
	}),
}))

import StudentLogFollowUpAction from '@/components/focus/StudentLogFollowUpAction.vue'

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
				return h(StudentLogFollowUpAction, {
					focusItemId: 'FOCUS:Student Log:LOG-0001:student_log.follow_up.review.decide:user@example.com',
					context: {
						focus_item_id:
							'FOCUS:Student Log:LOG-0001:student_log.follow_up.review.decide:user@example.com',
						action_type: 'student_log.follow_up.review.decide',
						reference_doctype: 'Student Log',
						reference_name: 'LOG-0001',
						mode: 'author',
						log: {
							name: 'LOG-0001',
							student: 'STU-0001',
							student_name: 'Student One',
							next_step: 'CALL_HOME',
							follow_up_status: 'In Progress',
						},
						inquiry: null,
						follow_ups: [],
						review_assignment: null,
						policy_signature: null,
					},
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
	searchFollowUpUsersMock.mockReset()
	submitStudentLogFollowUpMock.mockReset()
	reviewStudentLogOutcomeMock.mockReset()
	while (cleanupFns.length) cleanupFns.pop()?.()
	document.body.innerHTML = ''
})

describe('StudentLogFollowUpAction author reassignment', () => {
	it('searches scoped staff by typed full name and submits the selected user id', async () => {
		searchFollowUpUsersMock.mockImplementation(({ query }: { query?: string | null }) =>
			Promise.resolve(
				query === 'Mari'
					? [{ value: 'maria.gomez@example.com', label: 'Maria Gomez', meta: 'Primary School' }]
					: [{ value: 'other.user@example.com', label: 'Other User', meta: 'Primary School' }]
			)
		)
		reviewStudentLogOutcomeMock.mockResolvedValue({
			ok: true,
			idempotent: false,
			status: 'processed',
			log_name: 'LOG-0001',
			result: 'reassigned:maria.gomez@example.com',
		})

		mountComponent()
		await flushUi()

		expect(searchFollowUpUsersMock).toHaveBeenCalledWith({
			next_step: 'CALL_HOME',
			student: 'STU-0001',
			query: '',
			limit: 20,
		})
		expect(document.body.textContent || '').toContain('Search by the employee')

		const input = document.querySelector('input.if-input') as HTMLInputElement | null
		expect(input).not.toBeNull()
		if (!input) return

		input.value = 'Mari'
		input.dispatchEvent(new Event('input', { bubbles: true }))
		await flushUi()

		expect(searchFollowUpUsersMock).toHaveBeenLastCalledWith({
			next_step: 'CALL_HOME',
			student: 'STU-0001',
			query: 'Mari',
			limit: 20,
		})
		expect(document.body.textContent || '').toContain('Maria Gomez')

		const candidateButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Maria Gomez')
		)
		candidateButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		const reassignButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Reassign follow-up')
		)
		reassignButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(reviewStudentLogOutcomeMock).toHaveBeenCalledWith({
			focus_item_id:
				'FOCUS:Student Log:LOG-0001:student_log.follow_up.review.decide:user@example.com',
			decision: 'reassign',
			follow_up_person: 'maria.gomez@example.com',
			client_request_id: expect.stringMatching(/^rvw_/),
		})
	})
})
