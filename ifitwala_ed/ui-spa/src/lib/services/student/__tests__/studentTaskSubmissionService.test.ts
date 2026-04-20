import { afterEach, describe, expect, it, vi } from 'vitest'

const { apiMethodMock, apiUploadMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
	apiUploadMock: vi.fn(),
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

vi.mock('@/lib/client', () => ({
	apiUpload: apiUploadMock,
}))

import {
	getStudentTaskSubmission,
	submitStudentTaskSubmission,
} from '@/lib/services/student/studentTaskSubmissionService'

afterEach(() => {
	apiMethodMock.mockReset()
	apiUploadMock.mockReset()
})

describe('studentTaskSubmissionService', () => {
	it('uses the canonical read method for latest submission lookup', async () => {
		apiMethodMock.mockResolvedValue({ submission_id: 'TSU-1' })

		await getStudentTaskSubmission({
			outcome_id: 'OUT-1',
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.task_submission.get_latest_submission',
			{
				outcome_id: 'OUT-1',
			}
		)
	})

	it('uses the canonical json method when no files are attached', async () => {
		apiMethodMock.mockResolvedValue({ submission_id: 'TSU-2', version: 1 })

		await submitStudentTaskSubmission({
			task_outcome: 'OUT-2',
			text_content: 'Reflection',
			link_url: 'https://example.com/work',
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.task_submission.create_or_resubmit',
			{
				task_outcome: 'OUT-2',
				text_content: 'Reflection',
				link_url: 'https://example.com/work',
			}
		)
		expect(apiUploadMock).not.toHaveBeenCalled()
	})

	it('switches to multipart upload when files are attached', async () => {
		const onProgress = vi.fn()
		const file = new File(['evidence'], 'lab-report.pdf', { type: 'application/pdf' })
		apiUploadMock.mockResolvedValue({ submission_id: 'TSU-3', version: 2 })

		await submitStudentTaskSubmission(
			{
				task_outcome: 'OUT-3',
				text_content: 'Updated reflection',
				link_url: 'https://example.com/final',
				files: [file],
			},
			{ onProgress }
		)

		expect(apiUploadMock).toHaveBeenCalledTimes(1)
		expect(apiUploadMock.mock.calls[0][0]).toBe(
			'ifitwala_ed.api.task_submission.create_or_resubmit'
		)
		const formData = apiUploadMock.mock.calls[0][1] as FormData
		expect(formData.get('task_outcome')).toBe('OUT-3')
		expect(formData.get('text_content')).toBe('Updated reflection')
		expect(formData.get('link_url')).toBe('https://example.com/final')
		expect(formData.getAll('files')).toHaveLength(1)
		expect((formData.getAll('files')[0] as File).name).toBe('lab-report.pdf')
		expect(apiUploadMock.mock.calls[0][2]).toEqual({ onProgress })
		expect(apiMethodMock).not.toHaveBeenCalledWith(
			'ifitwala_ed.api.task_submission.create_or_resubmit',
			expect.anything()
		)
	})
})
