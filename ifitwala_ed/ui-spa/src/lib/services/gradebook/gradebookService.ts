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
	Request as GetTaskGradebookRequest,
	Response as GetTaskGradebookResponse,
} from '@/types/contracts/gradebook/get_task_gradebook'
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

	const getTaskGradebookResource = createResource<GetTaskGradebookResponse>({
		url: 'ifitwala_ed.api.gradebook.get_task_gradebook',
		method: 'POST',
		auto: false,
	})

	const updateTaskStudentResource = createResource<UpdateTaskStudentResponse>({
		url: 'ifitwala_ed.api.gradebook.update_task_student',
		method: 'POST',
		auto: false,
	})

	async function fetchGroups(payload: FetchGroupsRequest = {}): Promise<FetchGroupsResponse> {
		return fetchGroupsResource.submit(payload)
	}

	async function fetchGroupTasks(payload: FetchGroupTasksRequest): Promise<FetchGroupTasksResponse> {
		return fetchGroupTasksResource.submit(payload)
	}

	async function getTaskGradebook(
		payload: GetTaskGradebookRequest,
	): Promise<GetTaskGradebookResponse> {
		return getTaskGradebookResource.submit(payload)
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

	return {
		fetchGroups,
		fetchGroupTasks,
		getTaskGradebook,
		updateTaskStudent,
	}
}
