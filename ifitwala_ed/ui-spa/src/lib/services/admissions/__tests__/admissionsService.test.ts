import { beforeEach, describe, expect, it, vi } from 'vitest'

const { apiPostWithProgressMock, createResourceMock, emitMock, submitMocks } = vi.hoisted(() => {
	const submitMocks: ReturnType<typeof vi.fn>[] = []
	const createResourceMock = vi.fn(() => {
		const submit = vi.fn()
		submitMocks.push(submit)
		return { submit }
	})
	return {
		apiPostWithProgressMock: vi.fn(),
		createResourceMock,
		emitMock: vi.fn(),
		submitMocks,
	}
})

vi.mock('frappe-ui', () => ({
	createResource: createResourceMock,
}))

vi.mock('@/lib/client', () => ({
	apiPostWithProgress: apiPostWithProgressMock,
}))

vi.mock('@/lib/uiSignals', () => ({
	uiSignals: {
		emit: emitMock,
	},
	SIGNAL_ADMISSIONS_PORTAL_INVALIDATE: 'admissions:invalidate',
}))

import { createAdmissionsService } from '@/lib/services/admissions/admissionsService'

describe('admissionsService uploads', () => {
	beforeEach(() => {
		apiPostWithProgressMock.mockReset()
		emitMock.mockReset()
		for (const submit of submitMocks) {
			submit.mockReset()
		}
	})

	it('uploads applicant documents through the shared progress transport and emits invalidate', async () => {
		const service = createAdmissionsService()
		const onProgress = vi.fn()
		apiPostWithProgressMock.mockResolvedValue({
			file: 'FILE-1',
			file_url: '/private/files/evidence.pdf',
			drive_file_id: 'DRV-FILE-1',
			canonical_ref: 'drv:ORG-1:DRV-FILE-1',
			applicant_document: 'APP-DOC-1',
			applicant_document_item: 'ROW-1',
			item_key: 'passport',
			item_label: 'Passport',
		})

		await service.uploadDocument(
			{
				document_type: 'Passport',
				file_name: 'passport.pdf',
				content: 'YmFzZTY0',
			},
			{ onProgress }
		)

		expect(apiPostWithProgressMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.admissions_portal.upload_applicant_document',
			{
				document_type: 'Passport',
				file_name: 'passport.pdf',
				content: 'YmFzZTY0',
			},
			{ onProgress }
		)
		expect(emitMock).toHaveBeenCalledWith('admissions:invalidate')
	})
})
