// ifitwala_ed/ui-spa/src/lib/__tests__/frappe.test.ts

import { beforeEach, describe, expect, it, vi } from 'vitest'

const setConfigMock = vi.fn()
const frappeRequestMock = vi.fn()

vi.mock('frappe-ui', () => ({
	setConfig: setConfigMock,
	frappeRequest: frappeRequestMock,
}))

import { apiMethod, apiRequest, setupFrappeUI } from '@/lib/frappe'

describe('lib/frappe transport contract', () => {
	beforeEach(() => {
		setConfigMock.mockReset()
		frappeRequestMock.mockReset()
		;(window as any).csrf_token = 'csrf-from-window'
	})

	it('apiRequest unwraps canonical message envelope', async () => {
		frappeRequestMock.mockResolvedValue({ message: { ok: true } })

		const payload = await apiRequest<{ ok: boolean }>({ url: '/api/method/x' })

		expect(payload).toEqual({ ok: true })
	})

	it('apiRequest unwraps axios-style data.message envelope', async () => {
		frappeRequestMock.mockResolvedValue({ data: { message: { id: 'A-1' } } })

		const payload = await apiRequest<{ id: string }>({ url: '/api/method/x' })

		expect(payload).toEqual({ id: 'A-1' })
	})

	it('apiRequest throws on null payload', async () => {
		frappeRequestMock.mockResolvedValue(null)

		await expect(apiRequest({ url: '/api/method/x' })).rejects.toThrow('Invalid response shape')
	})

	it('apiMethod uses canonical POST request shape', async () => {
		frappeRequestMock.mockResolvedValue({ message: { done: 1 } })

		await apiMethod('ifitwala_ed.api.guardian_home.get_guardian_home_snapshot', {
			anchor_date: '2026-02-12',
		})

		expect(frappeRequestMock).toHaveBeenCalledWith({
			url: '/api/method/ifitwala_ed.api.guardian_home.get_guardian_home_snapshot',
			method: 'POST',
			params: { anchor_date: '2026-02-12' },
		})
	})

	it('setupFrappeUI wires resourceFetcher and CSRF headers', async () => {
		frappeRequestMock.mockResolvedValue({ message: { ok: 1 } })

		await setupFrappeUI()

		expect(setConfigMock).toHaveBeenCalledWith('resourceFetcher', expect.any(Function))
		expect(setConfigMock).toHaveBeenCalledWith('fetchOptions', {
			credentials: 'same-origin',
			headers: { 'X-Frappe-CSRF-Token': 'csrf-from-window' },
		})
	})
})
