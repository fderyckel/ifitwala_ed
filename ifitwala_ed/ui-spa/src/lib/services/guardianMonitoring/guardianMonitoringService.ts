// ui-spa/src/lib/services/guardianMonitoring/guardianMonitoringService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	MarkGuardianStudentLogReadRequest,
	MarkGuardianStudentLogReadResponse,
	PageRequest as GetGuardianMonitoringPageRequest,
	PublishedResultPageResponse,
	Request as GetGuardianMonitoringSnapshotRequest,
	StudentLogPageResponse,
	Response as GetGuardianMonitoringSnapshotResponse,
} from '@/types/contracts/guardian/get_guardian_monitoring_snapshot'

const SNAPSHOT_METHOD = 'ifitwala_ed.api.guardian_monitoring.get_guardian_monitoring_snapshot'
const STUDENT_LOGS_METHOD = 'ifitwala_ed.api.guardian_monitoring.get_guardian_monitoring_student_logs'
const PUBLISHED_RESULTS_METHOD =
	'ifitwala_ed.api.guardian_monitoring.get_guardian_monitoring_published_results'
const MARK_LOG_READ_METHOD = 'ifitwala_ed.api.guardian_monitoring.mark_guardian_student_log_read'

export async function getGuardianMonitoringSnapshot(
	payload: GetGuardianMonitoringSnapshotRequest = {}
): Promise<GetGuardianMonitoringSnapshotResponse> {
	return apiMethod<GetGuardianMonitoringSnapshotResponse>(SNAPSHOT_METHOD, payload)
}

export async function getGuardianMonitoringStudentLogs(
	payload: GetGuardianMonitoringPageRequest = {}
): Promise<StudentLogPageResponse> {
	return apiMethod<StudentLogPageResponse>(STUDENT_LOGS_METHOD, payload)
}

export async function getGuardianMonitoringPublishedResults(
	payload: GetGuardianMonitoringPageRequest = {}
): Promise<PublishedResultPageResponse> {
	return apiMethod<PublishedResultPageResponse>(PUBLISHED_RESULTS_METHOD, payload)
}

export async function markGuardianStudentLogRead(
	payload: MarkGuardianStudentLogReadRequest
): Promise<MarkGuardianStudentLogReadResponse> {
	return apiMethod<MarkGuardianStudentLogReadResponse>(MARK_LOG_READ_METHOD, payload)
}
