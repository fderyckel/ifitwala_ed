// ifitwala_ed/ui-spa/src/lib/__tests__/client.test.ts

import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api, apiPostWithProgress, apiUpload, setCsrfToken } from '@/lib/client'

type FakeResponse = {
	status: number
	statusText: string
	body: Record<string, unknown>
}

class FakeXMLHttpRequest {
	static HEADERS_RECEIVED = 2
	static response: FakeResponse = {
		status: 200,
		statusText: 'OK',
		body: { message: { ok: true } },
	}
	static instances: FakeXMLHttpRequest[] = []

	headers: Record<string, string> = {}
	method = ''
	url = ''
	withCredentials = false
	status = 0
	statusText = ''
	responseText = ''
	readyState = 0
	body: FormData | string | null = null
	onreadystatechange: (() => void) | null = null
	onload: (() => void) | null = null
	onerror: (() => void) | null = null
	onabort: (() => void) | null = null

	private uploadListeners: Record<string, Array<(event?: any) => void>> = {}

	upload = {
		addEventListener: (name: string, handler: (event?: any) => void) => {
			this.uploadListeners[name] ||= []
			this.uploadListeners[name].push(handler)
		},
	}

	constructor() {
		FakeXMLHttpRequest.instances.push(this)
	}

	open(method: string, url: string) {
		this.method = method
		this.url = url
	}

	setRequestHeader(name: string, value: string) {
		this.headers[name] = value
	}

	send(body: FormData | string) {
		this.body = body
		this.dispatchUpload('loadstart', {
			loaded: 0,
			total: 10,
			lengthComputable: true,
		})
		this.dispatchUpload('progress', {
			loaded: 5,
			total: 10,
			lengthComputable: true,
		})
		this.dispatchUpload('progress', {
			loaded: 10,
			total: 10,
			lengthComputable: true,
		})
		this.dispatchUpload('load')
		this.readyState = FakeXMLHttpRequest.HEADERS_RECEIVED
		this.onreadystatechange?.()

		this.status = FakeXMLHttpRequest.response.status
		this.statusText = FakeXMLHttpRequest.response.statusText
		this.responseText = JSON.stringify(FakeXMLHttpRequest.response.body)
		this.onload?.()
	}

	private dispatchUpload(name: string, event?: any) {
		for (const handler of this.uploadListeners[name] || []) {
			handler(event)
		}
	}
}

describe('lib/client API transport', () => {
	beforeEach(() => {
		setCsrfToken('csrf-token')
		vi.restoreAllMocks()
		vi.stubGlobal('XMLHttpRequest', FakeXMLHttpRequest as any)
		FakeXMLHttpRequest.instances = []
		FakeXMLHttpRequest.response = {
			status: 200,
			statusText: 'OK',
			body: { message: { ok: true } },
		}
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

	it('apiUpload reports upload progress and preserves csrf headers', async () => {
		const onProgress = vi.fn()
		const formData = new FormData()
		formData.append('file', new File(['bytes'], 'evidence.pdf', { type: 'application/pdf' }))

		const payload = await apiUpload<{ ok: boolean }>(
			'ifitwala_ed.api.documents.upload',
			formData,
			{ onProgress }
		)

		expect(payload).toEqual({ ok: true })
		expect(onProgress).toHaveBeenCalledWith(
			expect.objectContaining({ phase: 'uploading', percent: 50 })
		)
		expect(onProgress).toHaveBeenCalledWith(
			expect.objectContaining({ phase: 'processing', percent: 100 })
		)
		expect(FakeXMLHttpRequest.instances[0]?.headers).toEqual({
			'X-Frappe-CSRF-Token': 'csrf-token',
		})
		expect(FakeXMLHttpRequest.instances[0]?.body).toBe(formData)
	})

	it('apiPostWithProgress sends canonical json payloads through the progress transport', async () => {
		const onProgress = vi.fn()

		await apiPostWithProgress<{ ok: boolean }>(
			'ifitwala_ed.api.documents.upload_json',
			{ mode: 'portal', content: 'abc' },
			{ onProgress }
		)

		expect(FakeXMLHttpRequest.instances[0]?.headers).toEqual({
			'Content-Type': 'application/json',
			'X-Frappe-CSRF-Token': 'csrf-token',
		})
		expect(FakeXMLHttpRequest.instances[0]?.body).toBe(
			JSON.stringify({ mode: 'portal', content: 'abc' })
		)
		expect(onProgress).toHaveBeenCalledWith(
			expect.objectContaining({ phase: 'uploading', percent: 50 })
		)
	})
})
