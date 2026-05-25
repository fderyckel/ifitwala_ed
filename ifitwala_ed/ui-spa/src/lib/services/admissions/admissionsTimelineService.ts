import { api } from '@/lib/client';

import type {
	AdmissionsTimelineContext,
	AdmissionsTimelineRequest,
} from '@/types/contracts/admissions_timeline/get_admissions_timeline_context';

export async function getAdmissionsTimelineContext(
	payload: AdmissionsTimelineRequest
): Promise<AdmissionsTimelineContext> {
	return api(
		'ifitwala_ed.api.admissions_timeline.get_admissions_timeline_context',
		payload
	) as Promise<AdmissionsTimelineContext>;
}
