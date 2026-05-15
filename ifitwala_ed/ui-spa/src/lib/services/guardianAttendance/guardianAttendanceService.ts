// ui-spa/src/lib/services/guardianAttendance/guardianAttendanceService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetGuardianAttendanceSnapshotRequest,
	Response as GetGuardianAttendanceSnapshotResponse,
} from '@/types/contracts/guardian/get_guardian_attendance_snapshot'

const METHOD = 'ifitwala_ed.api.guardian_attendance.get_guardian_attendance_snapshot'

export async function getGuardianAttendanceSnapshot(
	payload: GetGuardianAttendanceSnapshotRequest = {}
): Promise<GetGuardianAttendanceSnapshotResponse> {
	return apiMethod<GetGuardianAttendanceSnapshotResponse>(METHOD, payload)
}
