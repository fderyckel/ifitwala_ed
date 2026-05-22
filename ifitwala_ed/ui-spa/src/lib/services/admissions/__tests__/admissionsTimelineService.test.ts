import { beforeEach, describe, expect, it, vi } from 'vitest';

const { apiMock } = vi.hoisted(() => ({
	apiMock: vi.fn(),
}));

vi.mock('@/lib/client', () => ({
	api: apiMock,
}));

import { getAdmissionsTimelineContext } from '@/lib/services/admissions/admissionsTimelineService';

describe('admissionsTimelineService', () => {
	beforeEach(() => {
		apiMock.mockReset();
	});

	it('loads the bounded contextual admissions timeline through the server endpoint', async () => {
		const response = {
			ok: true,
			context: {
				doctype: 'Inquiry',
				name: 'INQ-0001',
				limit: 30,
			},
			summary: {
				needs_reply: false,
				counts: {},
				completion_ladder: [],
			},
			items: [],
			actions: [],
			has_more: false,
			sources: {},
		};
		apiMock.mockResolvedValue(response);

		const result = await getAdmissionsTimelineContext({
			context_doctype: 'Inquiry',
			context_name: 'INQ-0001',
			limit: 30,
		});

		expect(apiMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.admissions_timeline.get_admissions_timeline_context',
			{
				context_doctype: 'Inquiry',
				context_name: 'INQ-0001',
				limit: 30,
			}
		);
		expect(result).toBe(response);
	});
});
