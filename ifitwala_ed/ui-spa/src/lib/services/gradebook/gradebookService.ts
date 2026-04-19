// ui-spa/src/lib/services/gradebook/gradebookService.ts

import { createResource } from 'frappe-ui'
import { SIGNAL_GRADEBOOK_INVALIDATE, uiSignals } from '@/lib/uiSignals'

import type {
	Request as FetchGroupsRequest,
	Response as FetchGroupsResponse,
} from '@/types/contracts/gradebook/fetch_groups'
import type {
	Request as FetchGroupTasksRequest,
	Response as FetchGroupTasksResponse,
} from '@/types/contracts/gradebook/fetch_group_tasks'
import type {
	Request as GetDrawerRequest,
	Response as GetDrawerResponse,
} from '@/types/contracts/gradebook/get_drawer'
import type {
	Request as ModeratorActionRequest,
	Response as ModeratorActionResponse,
} from '@/types/contracts/gradebook/moderator_action'
import type {
	Request as GetGridRequest,
	Response as GetGridResponse,
} from '@/types/contracts/gradebook/get_grid'
import type {
	Request as GetTaskGradebookRequest,
	Response as GetTaskGradebookResponse,
} from '@/types/contracts/gradebook/get_task_gradebook'
import type {
	Request as GetTaskQuizManualReviewRequest,
	Response as GetTaskQuizManualReviewResponse,
} from '@/types/contracts/gradebook/get_task_quiz_manual_review'
import type {
	Request as MarkNewSubmissionSeenRequest,
	Response as MarkNewSubmissionSeenResponse,
} from '@/types/contracts/gradebook/mark_new_submission_seen'
import type {
	Request as PublishOutcomesRequest,
	Response as PublishOutcomesResponse,
} from '@/types/contracts/gradebook/publish_outcomes'
import type {
	Request as RepairTaskRosterRequest,
	Response as RepairTaskRosterResponse,
} from '@/types/contracts/gradebook/repair_task_roster'
import type {
	Request as SaveDraftRequest,
	Response as SaveDraftResponse,
} from '@/types/contracts/gradebook/save_draft'
import type {
	Request as SaveFeedbackDraftRequest,
	Response as SaveFeedbackDraftResponse,
} from '@/types/contracts/gradebook/save_feedback_draft'
import type {
	Request as SaveFeedbackPublicationRequest,
	Response as SaveFeedbackPublicationResponse,
} from '@/types/contracts/gradebook/save_feedback_publication'
import type {
	Request as SaveTaskQuizManualReviewRequest,
	Response as SaveTaskQuizManualReviewResponse,
} from '@/types/contracts/gradebook/save_task_quiz_manual_review'
import type {
	Request as SubmitContributionRequest,
	Response as SubmitContributionResponse,
} from '@/types/contracts/gradebook/submit_contribution'
import type {
	Request as UpdateTaskStudentRequest,
	Response as UpdateTaskStudentResponse,
} from '@/types/contracts/gradebook/update_task_student'

export function createGradebookService() {
	const fetchGroupsResource = createResource<FetchGroupsResponse>({
		url: 'ifitwala_ed.api.gradebook.fetch_groups',
		method: 'POST',
		auto: false,
	})

	const fetchGroupTasksResource = createResource<FetchGroupTasksResponse>({
		url: 'ifitwala_ed.api.gradebook.fetch_group_tasks',
		method: 'POST',
		auto: false,
	})

	const getGridResource = createResource<GetGridResponse>({
		url: 'ifitwala_ed.api.gradebook.get_grid',
		method: 'POST',
		auto: false,
	})

	const getDrawerResource = createResource<GetDrawerResponse>({
		url: 'ifitwala_ed.api.gradebook.get_drawer',
		method: 'POST',
		auto: false,
	})

	const saveDraftResource = createResource<SaveDraftResponse>({
		url: 'ifitwala_ed.api.gradebook.save_draft',
		method: 'POST',
		auto: false,
	})

	const saveFeedbackDraftResource = createResource<SaveFeedbackDraftResponse>({
		url: 'ifitwala_ed.api.gradebook.save_feedback_draft',
		method: 'POST',
		auto: false,
	})

	const saveFeedbackPublicationResource = createResource<SaveFeedbackPublicationResponse>({
		url: 'ifitwala_ed.api.gradebook.save_feedback_publication',
		method: 'POST',
		auto: false,
	})

	const submitContributionResource = createResource<SubmitContributionResponse>({
		url: 'ifitwala_ed.api.gradebook.submit_contribution',
		method: 'POST',
		auto: false,
	})

	const moderatorActionResource = createResource<ModeratorActionResponse>({
		url: 'ifitwala_ed.api.gradebook.moderator_action',
		method: 'POST',
		auto: false,
	})

	const getTaskGradebookResource = createResource<GetTaskGradebookResponse>({
		url: 'ifitwala_ed.api.gradebook.get_task_gradebook',
		method: 'POST',
		auto: false,
	})

	const repairTaskRosterResource = createResource<RepairTaskRosterResponse>({
		url: 'ifitwala_ed.api.gradebook.repair_task_roster',
		method: 'POST',
		auto: false,
	})

	const getTaskQuizManualReviewResource = createResource<GetTaskQuizManualReviewResponse>({
		url: 'ifitwala_ed.api.gradebook.get_task_quiz_manual_review',
		method: 'POST',
		auto: false,
	})

	const saveTaskQuizManualReviewResource = createResource<SaveTaskQuizManualReviewResponse>({
		url: 'ifitwala_ed.api.gradebook.save_task_quiz_manual_review',
		method: 'POST',
		auto: false,
	})

	const updateTaskStudentResource = createResource<UpdateTaskStudentResponse>({
		url: 'ifitwala_ed.api.gradebook.update_task_student',
		method: 'POST',
		auto: false,
	})

	const markNewSubmissionSeenResource = createResource<MarkNewSubmissionSeenResponse>({
		url: 'ifitwala_ed.api.gradebook.mark_new_submission_seen',
		method: 'POST',
		auto: false,
	})

	const publishOutcomesResource = createResource<PublishOutcomesResponse>({
		url: 'ifitwala_ed.api.gradebook.publish_outcomes',
		method: 'POST',
		auto: false,
	})

	const unpublishOutcomesResource = createResource<PublishOutcomesResponse>({
		url: 'ifitwala_ed.api.gradebook.unpublish_outcomes',
		method: 'POST',
		auto: false,
	})

	async function fetchGroups(payload: FetchGroupsRequest = {}): Promise<FetchGroupsResponse> {
		return fetchGroupsResource.submit(payload)
	}

	async function fetchGroupTasks(payload: FetchGroupTasksRequest): Promise<FetchGroupTasksResponse> {
		return fetchGroupTasksResource.submit(payload)
	}

	async function getGrid(payload: GetGridRequest): Promise<GetGridResponse> {
		return getGridResource.submit(payload)
	}

	async function getDrawer(payload: GetDrawerRequest): Promise<GetDrawerResponse> {
		return getDrawerResource.submit(payload)
	}

	async function saveDraft(payload: SaveDraftRequest): Promise<SaveDraftResponse> {
		return saveDraftResource.submit(payload)
	}

	async function saveFeedbackDraft(
		payload: SaveFeedbackDraftRequest,
	): Promise<SaveFeedbackDraftResponse> {
		return saveFeedbackDraftResource.submit(payload)
	}

	async function saveFeedbackPublication(
		payload: SaveFeedbackPublicationRequest,
	): Promise<SaveFeedbackPublicationResponse> {
		return saveFeedbackPublicationResource.submit(payload)
	}

	async function submitContribution(
		payload: SubmitContributionRequest,
	): Promise<SubmitContributionResponse> {
		return submitContributionResource.submit(payload)
	}

	async function moderatorAction(
		payload: ModeratorActionRequest,
	): Promise<ModeratorActionResponse> {
		return moderatorActionResource.submit(payload)
	}

	async function getTaskGradebook(
		payload: GetTaskGradebookRequest,
	): Promise<GetTaskGradebookResponse> {
		return getTaskGradebookResource.submit(payload)
	}

	async function repairTaskRoster(
		payload: RepairTaskRosterRequest,
	): Promise<RepairTaskRosterResponse> {
		return repairTaskRosterResource.submit(payload)
	}

	async function getTaskQuizManualReview(
		payload: GetTaskQuizManualReviewRequest,
	): Promise<GetTaskQuizManualReviewResponse> {
		return getTaskQuizManualReviewResource.submit(payload)
	}

	async function saveTaskQuizManualReview(
		payload: SaveTaskQuizManualReviewRequest,
	): Promise<SaveTaskQuizManualReviewResponse> {
		return saveTaskQuizManualReviewResource.submit(payload)
	}

	async function updateTaskStudent(
		payload: UpdateTaskStudentRequest,
	): Promise<UpdateTaskStudentResponse> {
		const response = await updateTaskStudentResource.submit(payload)
		if (response.task_student) {
			uiSignals.emit(SIGNAL_GRADEBOOK_INVALIDATE, { task_student: response.task_student })
		}
		return response
	}

	async function markNewSubmissionSeen(
		payload: MarkNewSubmissionSeenRequest,
	): Promise<MarkNewSubmissionSeenResponse> {
		return markNewSubmissionSeenResource.submit(payload)
	}

	async function publishOutcomes(
		payload: PublishOutcomesRequest,
	): Promise<PublishOutcomesResponse> {
		return publishOutcomesResource.submit(payload)
	}

	async function unpublishOutcomes(
		payload: PublishOutcomesRequest,
	): Promise<PublishOutcomesResponse> {
		return unpublishOutcomesResource.submit(payload)
	}

	return {
		fetchGroups,
		fetchGroupTasks,
		getGrid,
		getDrawer,
		saveDraft,
		saveFeedbackDraft,
		saveFeedbackPublication,
		submitContribution,
		moderatorAction,
		getTaskGradebook,
		repairTaskRoster,
		getTaskQuizManualReview,
		saveTaskQuizManualReview,
		updateTaskStudent,
		markNewSubmissionSeen,
		publishOutcomes,
		unpublishOutcomes,
	}
}
