// ifitwala_ed/ui-spa/src/lib/__tests__/client.test.ts

import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api, setCsrfToken } from '@/lib/client'

describe('lib/client API transport', () => {
	beforeEach(() => {
		setCsrfToken('csrf-token')
		vi.restoreAllMocks()
	})

	it('sends canonical POST payload body directly', async () => {
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			json: async () => ({ message: { ok: true } }),
		})
		vi.stubGlobal('fetch', fetchMock)

		const payload = await api('ifitwala_ed.api.attendance.get', { mode: 'overview' })

		expect(payload).toEqual({ ok: true })
		expect(fetchMock).toHaveBeenCalledWith(
			'/api/method/ifitwala_ed.api.attendance.get',
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({ mode: 'overview' }),
			})
		)
	})

	it('does not send body for GET calls', async () => {
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			json: async () => ({ message: { ok: true } }),
		})
		vi.stubGlobal('fetch', fetchMock)

		await api('ifitwala_ed.api.attendance.get', undefined, 'GET')

		expect(fetchMock).toHaveBeenCalledWith(
			'/api/method/ifitwala_ed.api.attendance.get',
			expect.objectContaining({ method: 'GET', body: undefined })
		)
	})

	it('raises server messages when backend responds with error', async () => {
		const fetchMock = vi.fn().mockResolvedValue({
			ok: false,
			statusText: 'Bad Request',
			json: async () => ({ _server_messages: JSON.stringify(['Validation failed']) }),
		})
		vi.stubGlobal('fetch', fetchMock)

		await expect(api('ifitwala_ed.api.attendance.get', { mode: 'overview' })).rejects.toThrow(
			'Validation failed'
		)
	})
})
