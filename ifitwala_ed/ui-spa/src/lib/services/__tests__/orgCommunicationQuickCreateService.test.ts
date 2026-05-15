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

const { apiMock, apiUploadMock, createResourceMock, emitMock, resourceRecords } = vi.hoisted(() => {
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
	const apiMock = vi.fn()
	const apiUploadMock = vi.fn()
	return { apiMock, apiUploadMock, createResourceMock, emitMock, resourceRecords }
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

vi.mock('@/lib/client', () => ({
	api: apiMock,
	apiUpload: apiUploadMock,
}))

import {
	addOrgCommunicationLink,
	createOrgCommunicationQuick,
	removeOrgCommunicationAttachment,
	searchOrgCommunicationStudentGroups,
	searchOrgCommunicationTeams,
	uploadOrgCommunicationAttachment,
} from '@/lib/services/orgCommunicationQuickCreateService'

describe('orgCommunicationQuickCreateService', () => {
	beforeEach(() => {
		apiMock.mockReset()
		apiUploadMock.mockReset()
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

	it('addOrgCommunicationLink emits invalidate after link success', async () => {
		apiMock.mockResolvedValue({
			ok: true,
			org_communication: 'COMM-LINK-1',
			attachment: {
				row_name: 'row-link-1',
				kind: 'link',
				title: 'Policy PDF',
				external_url: 'https://example.com/policy.pdf',
			},
		})

		await addOrgCommunicationLink({
			org_communication: 'COMM-LINK-1',
			title: 'Policy PDF',
			external_url: 'https://example.com/policy.pdf',
		})

		expect(apiMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.org_communication_attachments.add_org_communication_link',
			{
				org_communication: 'COMM-LINK-1',
				title: 'Policy PDF',
				external_url: 'https://example.com/policy.pdf',
			}
		)
		expect(emitMock).toHaveBeenCalledWith('org_communication:invalidate', {
			names: ['COMM-LINK-1'],
			reason: 'org_communication_attachment',
		})
	})

	it('searchOrgCommunicationTeams calls the canonical quick-create team search endpoint', async () => {
		apiMock.mockResolvedValue({
			results: [{ name: 'TEAM-1', team_name: 'Operations', team_code: 'OPS' }],
		})

		await searchOrgCommunicationTeams({
			query: 'ops',
			organization: 'ORG-1',
			school: 'SCH-1',
			limit: 8,
		})

		expect(apiMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.org_communication_quick_create.search_org_communication_teams',
			{
				query: 'ops',
				organization: 'ORG-1',
				school: 'SCH-1',
				limit: 8,
			}
		)
	})

	it('searchOrgCommunicationStudentGroups calls the canonical quick-create student-group search endpoint', async () => {
		apiMock.mockResolvedValue({
			results: [{ name: 'SG-1', student_group_name: 'Grade 6 Math' }],
		})

		await searchOrgCommunicationStudentGroups({
			query: 'math',
			school: 'SCH-1',
			limit: 8,
		})

		expect(apiMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.org_communication_quick_create.search_org_communication_student_groups',
			{
				query: 'math',
				school: 'SCH-1',
				limit: 8,
			}
		)
	})

	it('removeOrgCommunicationAttachment emits invalidate after remove success', async () => {
		apiMock.mockResolvedValue({
			ok: true,
			org_communication: 'COMM-LINK-1',
			row_name: 'row-link-1',
		})

		await removeOrgCommunicationAttachment({
			org_communication: 'COMM-LINK-1',
			row_name: 'row-link-1',
		})

		expect(apiMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.org_communication_attachments.remove_org_communication_attachment',
			{
				org_communication: 'COMM-LINK-1',
				row_name: 'row-link-1',
			}
		)
		expect(emitMock).toHaveBeenCalledWith('org_communication:invalidate', {
			names: ['COMM-LINK-1'],
			reason: 'org_communication_attachment',
		})
	})

	it('uploadOrgCommunicationAttachment uses shared multipart transport and emits invalidate', async () => {
		const file = new File(['pdf-bytes'], 'policy.pdf', { type: 'application/pdf' })
		const onProgress = vi.fn()
		apiUploadMock.mockResolvedValue({
			ok: true,
			org_communication: 'COMM-UPLOAD-1',
			attachment: {
				row_name: 'row-file-1',
				kind: 'file',
				title: 'Policy PDF',
				file_name: 'policy.pdf',
			},
		})

		await uploadOrgCommunicationAttachment({
			org_communication: 'COMM-UPLOAD-1',
			row_name: 'row-file-1',
			file,
		}, {
			onProgress,
		})

		expect(apiUploadMock).toHaveBeenCalledTimes(1)
		expect(apiUploadMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.org_communication_attachments.upload_org_communication_attachment',
			expect.any(FormData),
			{ onProgress }
		)
		const formData = apiUploadMock.mock.calls[0][1] as FormData
		expect(formData.get('org_communication')).toBe('COMM-UPLOAD-1')
		expect(formData.get('row_name')).toBe('row-file-1')
		const uploadedFile = formData.get('file')
		expect(uploadedFile).toBeInstanceOf(File)
		expect((uploadedFile as File).name).toBe(file.name)
		expect((uploadedFile as File).type).toBe(file.type)
		expect(emitMock).toHaveBeenCalledWith('org_communication:invalidate', {
			names: ['COMM-UPLOAD-1'],
			reason: 'org_communication_attachment',
		})
	})
})
