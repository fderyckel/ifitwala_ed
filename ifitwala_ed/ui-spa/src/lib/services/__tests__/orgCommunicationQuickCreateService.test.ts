// ui-spa/src/lib/services/__tests__/orgCommunicationQuickCreateService.test.ts

import { beforeEach, describe, expect, it, vi } from 'vitest'

type ResourceRecord = {
	config: {
		url?: string
		method?: string
		auto?: boolean
	}
	submit: ReturnType<typeof vi.fn>
}

const { createResourceMock, emitMock, resourceRecords } = vi.hoisted(() => {
	const resourceRecords: ResourceRecord[] = []
	const createResourceMock = vi.fn((config: ResourceRecord['config']) => {
		const record: ResourceRecord = {
			config,
			submit: vi.fn(),
		}
		resourceRecords.push(record)
		return {
			submit: record.submit,
		}
	})
	const emitMock = vi.fn()
	return { createResourceMock, emitMock, resourceRecords }
})

vi.mock('frappe-ui', () => ({
	createResource: createResourceMock,
}))

vi.mock('@/lib/uiSignals', () => ({
	uiSignals: {
		emit: emitMock,
	},
	SIGNAL_ORG_COMMUNICATION_INVALIDATE: 'org_communication:invalidate',
}))

import {
	createOrgCommunicationQuick,
} from '@/lib/services/orgCommunicationQuickCreateService'

describe('orgCommunicationQuickCreateService', () => {
	beforeEach(() => {
		emitMock.mockClear()
		for (const record of resourceRecords) {
			record.submit.mockReset()
		}
	})

	it('wires canonical org communication quick-create endpoints', () => {
		expect(resourceRecords.map(record => record.config.url)).toEqual([
			'ifitwala_ed.api.org_communication_quick_create.get_org_communication_quick_create_options',
			'ifitwala_ed.api.org_communication_quick_create.create_org_communication_quick',
		])
		expect(resourceRecords.every(record => record.config.method === 'POST')).toBe(true)
		expect(resourceRecords.every(record => record.config.auto === false)).toBe(true)
	})

	it('createOrgCommunicationQuick emits invalidate on semantic success', async () => {
		resourceRecords[1].submit.mockResolvedValue({
			ok: true,
			status: 'created',
			name: 'COMM-0001',
			title: 'Staff update',
		})

		await createOrgCommunicationQuick({
			title: 'Staff update',
			communication_type: 'Information',
			status: 'Published',
			priority: 'Normal',
			portal_surface: 'Everywhere',
			audiences: [],
			client_request_id: 'req-1',
		})

		expect(resourceRecords[1].submit).toHaveBeenCalledWith({
			title: 'Staff update',
			communication_type: 'Information',
			status: 'Published',
			priority: 'Normal',
			portal_surface: 'Everywhere',
			audiences: [],
			client_request_id: 'req-1',
		})
		expect(emitMock).toHaveBeenCalledWith('org_communication:invalidate', {
			names: ['COMM-0001'],
			reason: 'quick_create',
		})
	})
})
