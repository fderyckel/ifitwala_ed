// ui-spa/src/lib/services/guardianHome/guardianHomeService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetGuardianHomeSnapshotRequest,
	Response as GetGuardianHomeSnapshotResponse,
} from '@/types/contracts/guardian/get_guardian_home_snapshot'

const METHOD = 'ifitwala_ed.api.guardian_home.get_guardian_home_snapshot'

export async function getGuardianHomeSnapshot(
	payload: GetGuardianHomeSnapshotRequest = {}
): Promise<GetGuardianHomeSnapshotResponse> {
	return apiMethod<GetGuardianHomeSnapshotResponse>(METHOD, payload)
}
