// ifitwala_ed/ui-spa/src/composables/__tests__/useCalendarEvents.test.ts

import { beforeEach, describe, expect, it, vi } from 'vitest'

const { apiMethodMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

function buildPayload(id: string) {
	return {
		timezone: 'Asia/Bangkok',
		window: {
			from: '2026-04-18T00:00:00+07:00',
			to: '2026-04-25T00:00:00+07:00',
		},
		generated_at: '2026-04-18T09:00:00+07:00',
		sources: ['meeting'],
		counts: { meeting: 1 },
		events: [
			{
				id,
				title: `Event ${id}`,
				start: '2026-04-18T09:00:00+07:00',
				end: '2026-04-18T10:00:00+07:00',
				allDay: false,
				source: 'meeting',
				color: '#2563eb',
				meta: {},
			},
		],
	}
}

async function loadComposable() {
	vi.resetModules()
	return import('@/composables/useCalendarEvents')
}

describe('useCalendarEvents', () => {
	beforeEach(() => {
		apiMethodMock.mockReset()
		window.sessionStorage.clear()
		;(window as any).frappe = {
			session: {
				user: 'alice@example.com',
				user_info: {
					name: 'alice@example.com',
				},
			},
		}
	})

	it('reuses cached calendar payloads for the same user and range', async () => {
		apiMethodMock.mockResolvedValue(buildPayload('ALICE-1'))

		const { useCalendarEvents } = await loadComposable()
		const first = useCalendarEvents({ role: 'staff', sources: ['meeting'] })
		const second = useCalendarEvents({ role: 'staff', sources: ['meeting'] })

		await first.setRange('2026-04-18T00:00:00+07:00', '2026-04-25T00:00:00+07:00')
		await second.setRange('2026-04-18T00:00:00+07:00', '2026-04-25T00:00:00+07:00')

		expect(apiMethodMock).toHaveBeenCalledTimes(1)
		expect(second.events.value[0]?.id).toBe('ALICE-1')
	})

	it('does not reuse cached calendar payloads across different users', async () => {
		apiMethodMock
			.mockResolvedValueOnce(buildPayload('ALICE-1'))
			.mockResolvedValueOnce(buildPayload('BOB-1'))

		const { useCalendarEvents } = await loadComposable()
		const alice = useCalendarEvents({ role: 'staff', sources: ['meeting'] })

		await alice.setRange('2026-04-18T00:00:00+07:00', '2026-04-25T00:00:00+07:00')

		;(window as any).frappe.session.user = 'bob@example.com'
		;(window as any).frappe.session.user_info = { name: 'bob@example.com' }

		const bob = useCalendarEvents({ role: 'staff', sources: ['meeting'] })
		await bob.setRange('2026-04-18T00:00:00+07:00', '2026-04-25T00:00:00+07:00')

		expect(apiMethodMock).toHaveBeenCalledTimes(2)
		expect(bob.events.value[0]?.id).toBe('BOB-1')
	})

	it('surfaces actionable calendar error messages from the API layer', async () => {
		apiMethodMock.mockRejectedValue({
			status: 403,
			messages: ['Your user is not linked to an Employee record.'],
		})

		const { useCalendarEvents } = await loadComposable()
		const calendar = useCalendarEvents({ role: 'staff', sources: ['meeting'] })

		await calendar.setRange('2026-04-18T00:00:00+07:00', '2026-04-25T00:00:00+07:00')

		expect(calendar.error.value).toBe('Your user is not linked to an Employee record.')
	})
})
