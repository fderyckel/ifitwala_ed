// ifitwala_ed/ui-spa/src/lib/services/portfolio/portfolioService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetPortfolioFeedRequest,
	Response as GetPortfolioFeedResponse,
} from '@/types/contracts/portfolio/get_portfolio_feed'
import type {
	Request as CreateReflectionEntryRequest,
	Response as CreateReflectionEntryResponse,
} from '@/types/contracts/portfolio/create_reflection_entry'
import type {
	Request as ListReflectionEntriesRequest,
	Response as ListReflectionEntriesResponse,
} from '@/types/contracts/portfolio/list_reflection_entries'
import type {
	Request as AddPortfolioItemRequest,
	Response as AddPortfolioItemResponse,
} from '@/types/contracts/portfolio/add_portfolio_item'
import type {
	Request as UpdatePortfolioItemRequest,
	Response as UpdatePortfolioItemResponse,
} from '@/types/contracts/portfolio/update_portfolio_item'
import type {
	Request as SetShowcaseStateRequest,
	Response as SetShowcaseStateResponse,
} from '@/types/contracts/portfolio/set_showcase_state'
import type {
	Request as ApplyEvidenceTagRequest,
	Response as ApplyEvidenceTagResponse,
} from '@/types/contracts/portfolio/apply_evidence_tag'
import type {
	Request as RemoveEvidenceTagRequest,
	Response as RemoveEvidenceTagResponse,
} from '@/types/contracts/portfolio/remove_evidence_tag'
import type {
	Request as CreatePortfolioShareLinkRequest,
	Response as CreatePortfolioShareLinkResponse,
} from '@/types/contracts/portfolio/create_portfolio_share_link'
import type {
	Request as RevokePortfolioShareLinkRequest,
	Response as RevokePortfolioShareLinkResponse,
} from '@/types/contracts/portfolio/revoke_portfolio_share_link'
import type {
	Request as ExportPortfolioPdfRequest,
	Response as ExportPortfolioPdfResponse,
} from '@/types/contracts/portfolio/export_portfolio_pdf'
import type {
	Request as ExportReflectionPdfRequest,
	Response as ExportReflectionPdfResponse,
} from '@/types/contracts/portfolio/export_reflection_pdf'

const METHODS = {
	getPortfolioFeed: 'ifitwala_ed.api.student_portfolio.get_portfolio_feed',
	createReflectionEntry: 'ifitwala_ed.api.student_portfolio.create_reflection_entry',
	listReflectionEntries: 'ifitwala_ed.api.student_portfolio.list_reflection_entries',
	addPortfolioItem: 'ifitwala_ed.api.student_portfolio.add_portfolio_item',
	updatePortfolioItem: 'ifitwala_ed.api.student_portfolio.update_portfolio_item',
	setShowcaseState: 'ifitwala_ed.api.student_portfolio.set_showcase_state',
	applyEvidenceTag: 'ifitwala_ed.api.student_portfolio.apply_evidence_tag',
	removeEvidenceTag: 'ifitwala_ed.api.student_portfolio.remove_evidence_tag',
	createPortfolioShareLink: 'ifitwala_ed.api.student_portfolio.create_portfolio_share_link',
	revokePortfolioShareLink: 'ifitwala_ed.api.student_portfolio.revoke_portfolio_share_link',
	exportPortfolioPdf: 'ifitwala_ed.api.student_portfolio.export_portfolio_pdf',
	exportReflectionPdf: 'ifitwala_ed.api.student_portfolio.export_reflection_pdf',
} as const

export async function getPortfolioFeed(
	payload: GetPortfolioFeedRequest = {}
): Promise<GetPortfolioFeedResponse> {
	return apiMethod<GetPortfolioFeedResponse>(METHODS.getPortfolioFeed, payload)
}

export async function createReflectionEntry(
	payload: CreateReflectionEntryRequest
): Promise<CreateReflectionEntryResponse> {
	return apiMethod<CreateReflectionEntryResponse>(METHODS.createReflectionEntry, payload)
}

export async function listReflectionEntries(
	payload: ListReflectionEntriesRequest = {}
): Promise<ListReflectionEntriesResponse> {
	return apiMethod<ListReflectionEntriesResponse>(METHODS.listReflectionEntries, payload)
}

export async function addPortfolioItem(
	payload: AddPortfolioItemRequest
): Promise<AddPortfolioItemResponse> {
	return apiMethod<AddPortfolioItemResponse>(METHODS.addPortfolioItem, payload)
}

export async function updatePortfolioItem(
	payload: UpdatePortfolioItemRequest
): Promise<UpdatePortfolioItemResponse> {
	return apiMethod<UpdatePortfolioItemResponse>(METHODS.updatePortfolioItem, payload)
}

export async function setShowcaseState(
	payload: SetShowcaseStateRequest
): Promise<SetShowcaseStateResponse> {
	return apiMethod<SetShowcaseStateResponse>(METHODS.setShowcaseState, payload)
}

export async function applyEvidenceTag(
	payload: ApplyEvidenceTagRequest
): Promise<ApplyEvidenceTagResponse> {
	return apiMethod<ApplyEvidenceTagResponse>(METHODS.applyEvidenceTag, payload)
}

export async function removeEvidenceTag(
	payload: RemoveEvidenceTagRequest
): Promise<RemoveEvidenceTagResponse> {
	return apiMethod<RemoveEvidenceTagResponse>(METHODS.removeEvidenceTag, payload)
}

export async function createPortfolioShareLink(
	payload: CreatePortfolioShareLinkRequest
): Promise<CreatePortfolioShareLinkResponse> {
	return apiMethod<CreatePortfolioShareLinkResponse>(METHODS.createPortfolioShareLink, payload)
}

export async function revokePortfolioShareLink(
	payload: RevokePortfolioShareLinkRequest
): Promise<RevokePortfolioShareLinkResponse> {
	return apiMethod<RevokePortfolioShareLinkResponse>(METHODS.revokePortfolioShareLink, payload)
}

export async function exportPortfolioPdf(
	payload: ExportPortfolioPdfRequest
): Promise<ExportPortfolioPdfResponse> {
	return apiMethod<ExportPortfolioPdfResponse>(METHODS.exportPortfolioPdf, payload)
}

export async function exportReflectionPdf(
	payload: ExportReflectionPdfRequest
): Promise<ExportReflectionPdfResponse> {
	return apiMethod<ExportReflectionPdfResponse>(METHODS.exportReflectionPdf, payload)
}
