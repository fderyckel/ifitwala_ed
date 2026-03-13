// ui-spa/src/lib/services/guardianMonitoring/guardianMonitoringService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetGuardianMonitoringSnapshotRequest,
	Response as GetGuardianMonitoringSnapshotResponse,
} from '@/types/contracts/guardian/get_guardian_monitoring_snapshot'

const METHOD = 'ifitwala_ed.api.guardian_monitoring.get_guardian_monitoring_snapshot'

export async function getGuardianMonitoringSnapshot(
	payload: GetGuardianMonitoringSnapshotRequest = {}
): Promise<GetGuardianMonitoringSnapshotResponse> {
	return apiMethod<GetGuardianMonitoringSnapshotResponse>(METHOD, payload)
}
