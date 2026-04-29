import { api } from '@/lib/client';

import type {
	AdmissionsInboxContext,
	AdmissionsInboxRequest,
} from '@/types/contracts/admissions_inbox/get_admissions_inbox_context';

export async function getAdmissionsInboxContext(
	payload: AdmissionsInboxRequest = {}
): Promise<AdmissionsInboxContext> {
	return api(
		'ifitwala_ed.api.admissions_inbox.get_admissions_inbox_context',
		payload
	) as Promise<AdmissionsInboxContext>;
}
