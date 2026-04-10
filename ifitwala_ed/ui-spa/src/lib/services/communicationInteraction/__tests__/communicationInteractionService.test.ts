// ifitwala_ed/ui-spa/src/lib/services/communicationInteraction/__tests__/communicationInteractionService.test.ts

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

import { createCommunicationInteractionService } from '@/lib/services/communicationInteraction/communicationInteractionService'

describe('communicationInteractionService', () => {
	beforeEach(() => {
		createResourceMock.mockClear()
		emitMock.mockClear()
		resourceRecords.length = 0
	})

	it('wires canonical org communication interaction endpoints', () => {
		createCommunicationInteractionService()

		expect(resourceRecords.map(record => record.config.url)).toEqual([
			'ifitwala_ed.api.org_communication_interactions.get_org_communication_interaction_summary',
			'ifitwala_ed.api.org_communication_interactions.get_org_communication_thread',
			'ifitwala_ed.api.org_communication_interactions.react_to_org_communication',
			'ifitwala_ed.api.org_communication_interactions.post_org_communication_comment',
			'ifitwala_ed.api.org_communication_interactions.mark_org_communication_read',
		])
		expect(resourceRecords.every(record => record.config.method === 'POST')).toBe(true)
		expect(resourceRecords.every(record => record.config.auto === false)).toBe(true)
	})

	it('reactToOrgCommunication sends canonical payload and emits invalidate on success', async () => {
		const service = createCommunicationInteractionService()
		resourceRecords[2].submit.mockResolvedValue({ name: 'ENTRY-0001' })

		await service.reactToOrgCommunication({
			org_communication: 'COMM-0001',
			reaction_code: 'like',
		})

		expect(resourceRecords[2].submit).toHaveBeenCalledWith({
			org_communication: 'COMM-0001',
			reaction_code: 'like',
			surface: 'Portal Feed',
		})
		expect(emitMock).toHaveBeenCalledWith('org_communication:invalidate', {
			names: ['COMM-0001'],
		})
	})

	it('postOrgCommunicationComment sends canonical payload and emits invalidate on success', async () => {
		const service = createCommunicationInteractionService()
		resourceRecords[3].submit.mockResolvedValue({ name: 'ENTRY-0002' })

		await service.postOrgCommunicationComment({
			org_communication: 'COMM-0002',
			note: 'Thanks for the update',
			surface: 'Morning Brief',
		})

		expect(resourceRecords[3].submit).toHaveBeenCalledWith({
			org_communication: 'COMM-0002',
			note: 'Thanks for the update',
			surface: 'Morning Brief',
		})
		expect(emitMock).toHaveBeenCalledWith('org_communication:invalidate', {
			names: ['COMM-0002'],
		})
	})

	it('markOrgCommunicationRead sends canonical payload without emitting invalidate', async () => {
		const service = createCommunicationInteractionService()
		resourceRecords[4].submit.mockResolvedValue({
			ok: true,
			org_communication: 'COMM-0003',
			read_at: '2026-04-10T11:00:00',
		})

		await service.markOrgCommunicationRead({
			org_communication: 'COMM-0003',
		})

		expect(resourceRecords[4].submit).toHaveBeenCalledWith({
			org_communication: 'COMM-0003',
		})
		expect(emitMock).not.toHaveBeenCalled()
	})
})
