// ifitwala_ed/ui-spa/src/lib/__tests__/frappe.test.ts

import { beforeEach, describe, expect, it, vi } from 'vitest'

const { setConfigMock } = vi.hoisted(() => ({
	setConfigMock: vi.fn(),
}))

vi.mock('frappe-ui', () => ({
	setConfig: setConfigMock,
}))

import { apiMethod, apiRequest, setCsrfToken, setupFrappeUI } from '@/lib/frappe'

describe('lib/frappe transport contract', () => {
	beforeEach(() => {
		setConfigMock.mockReset()
		vi.restoreAllMocks()
		setCsrfToken('csrf-from-window')
	})

	it('apiRequest unwraps canonical message envelope', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				text: async () => JSON.stringify({ message: { ok: true } }),
			})
		)

		const payload = await apiRequest<{ ok: boolean }>({ url: '/api/method/x' })

		expect(payload).toEqual({ ok: true })
	})

	it('apiRequest unwraps axios-style data.message envelope', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				text: async () => JSON.stringify({ data: { message: { id: 'A-1' } } }),
			})
		)

		const payload = await apiRequest<{ id: string }>({ url: '/api/method/x' })

		expect(payload).toEqual({ id: 'A-1' })
	})

	it('apiRequest preserves already-unwrapped payloads with top-level message fields', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				text: async () =>
					JSON.stringify({
						message: 'Showing the shared course plan.',
						learning: {
							selected_context: {
								unit_plan: 'UNIT-1',
							},
						},
					}),
			})
		)

		const payload = await apiRequest<{
			message: string
			learning: { selected_context: { unit_plan: string } }
		}>({ url: '/api/method/x' })

		expect(payload).toEqual({
			message: 'Showing the shared course plan.',
			learning: {
				selected_context: {
					unit_plan: 'UNIT-1',
				},
			},
		})
	})

	it('apiRequest preserves already-unwrapped payloads whose only field is message', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				text: async () => JSON.stringify({ message: 'Roster repaired.' }),
			})
		)

		const payload = await apiRequest<{ message: string }>({ url: '/api/method/x' })

		expect(payload).toEqual({ message: 'Roster repaired.' })
	})

	it('apiRequest throws on null payload', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				text: async () => 'null',
			})
		)

		await expect(apiRequest({ url: '/api/method/x' })).rejects.toThrow('Invalid response shape')
	})

	it('apiMethod uses canonical POST request shape', async () => {
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			text: async () => JSON.stringify({ message: { done: 1 } }),
		})
		vi.stubGlobal('fetch', fetchMock)

		await apiMethod('ifitwala_ed.api.guardian_home.get_guardian_home_snapshot', {
			anchor_date: '2026-02-12',
		})

		expect(fetchMock).toHaveBeenCalledWith(
			'/api/method/ifitwala_ed.api.guardian_home.get_guardian_home_snapshot',
			expect.objectContaining({
				method: 'POST',
				credentials: 'same-origin',
				body: JSON.stringify({ anchor_date: '2026-02-12' }),
			})
		)
	})

	it('setupFrappeUI wires resourceFetcher and CSRF headers', async () => {
		await setupFrappeUI()

		expect(setConfigMock).toHaveBeenCalledWith('resourceFetcher', expect.any(Function))
		expect(setConfigMock).toHaveBeenCalledWith('fetchOptions', {
			credentials: 'same-origin',
			headers: { 'X-Frappe-CSRF-Token': 'csrf-from-window' },
		})
	})

	it('apiRequest falls back to fetching a CSRF token when boot data is missing', async () => {
		setCsrfToken(null)

		const fetchMock = vi
			.fn()
			.mockResolvedValueOnce({
				ok: true,
				json: async () => ({ message: 'csrf-from-api' }),
			})
			.mockResolvedValueOnce({
				ok: true,
				text: async () => JSON.stringify({ message: { ok: true } }),
			})
		vi.stubGlobal('fetch', fetchMock)

		const payload = await apiRequest<{ ok: boolean }>({ url: '/api/method/x' })

		expect(payload).toEqual({ ok: true })
		expect(fetchMock).toHaveBeenNthCalledWith(
			1,
			'/api/method/frappe.client.get_csrf_token',
			expect.objectContaining({
				method: 'GET',
				credentials: 'same-origin',
			})
		)
		expect(fetchMock).toHaveBeenNthCalledWith(
			2,
			'/api/method/x',
			expect.objectContaining({
				headers: expect.any(Headers),
			})
		)
		const secondCall = fetchMock.mock.calls[1]
		const headers = secondCall?.[1]?.headers as Headers
		expect(headers.get('X-Frappe-CSRF-Token')).toBe('csrf-from-api')
	})

	it('apiRequest turns non-json 403 responses into structured errors', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: false,
				status: 403,
				statusText: 'Forbidden',
				text: async () => '<html>Forbidden</html>',
			})
		)

		await expect(apiRequest({ url: '/api/method/x' })).rejects.toMatchObject({
			message: 'Forbidden',
			status: 403,
		})
	})
})
