// ui-spa/src/lib/services/guardianFinance/guardianFinanceService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetGuardianFinanceSnapshotRequest,
	Response as GetGuardianFinanceSnapshotResponse,
} from '@/types/contracts/guardian/get_guardian_finance_snapshot'

const METHOD = 'ifitwala_ed.api.guardian_finance.get_guardian_finance_snapshot'

export async function getGuardianFinanceSnapshot(
	payload: GetGuardianFinanceSnapshotRequest = {}
): Promise<GetGuardianFinanceSnapshotResponse> {
	return apiMethod<GetGuardianFinanceSnapshotResponse>(METHOD, payload)
}
