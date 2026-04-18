import type { TaskSummary } from '@/types/contracts/gradebook/fetch_group_tasks'
import type { Delivery } from '@/types/contracts/gradebook/get_grid'
import type { DeliveryPayload } from '@/types/contracts/gradebook/get_drawer'
import type { TaskPayload } from '@/types/contracts/gradebook/get_task_gradebook'

export const DEFAULT_STUDENT_IMAGE = '/assets/ifitwala_ed/images/default_student_image.png'

type TaskLikeShape = {
	grading_mode?: 'None' | 'Completion' | 'Binary' | 'Points' | 'Criteria' | null
	allow_feedback?: 0 | 1 | boolean | null
	rubric_scoring_strategy?: 'Sum Total' | 'Separate Criteria' | null
	max_points?: number | null
	task_type?: string | null
	delivery_type?: string | null
	delivery_mode?: string | null
	points?: 0 | 1
	binary?: 0 | 1
	criteria?: 0 | 1
	observations?: 0 | 1
}

type TaskLike = TaskPayload | TaskSummary | Delivery | DeliveryPayload | TaskLikeShape | null | undefined

function resolveDeliveryMode(task?: TaskLike | Record<string, unknown> | null) {
	if (!task) return null
	if (typeof task === 'object' && 'delivery_type' in task) {
		return String((task as { delivery_type?: string | null }).delivery_type || '')
	}
	if (typeof task === 'object' && 'delivery_mode' in task) {
		return String((task as { delivery_mode?: string | null }).delivery_mode || '')
	}
	return null
}

export function formatDate(dateStr?: string | null) {
	if (!dateStr) return ''
	return new Date(dateStr).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function formatDateTime(value?: string | null) {
	if (!value) return ''
	return new Date(value).toLocaleString(undefined, {
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
	})
}

export function formatPoints(value: number | null | undefined) {
	return typeof value === 'number' ? value : '—'
}

export function isPointsTask(task?: TaskLike) {
	return task?.grading_mode === 'Points'
}

export function isBinaryTask(task?: TaskLike) {
	return task?.grading_mode === 'Binary'
}

export function isCompletionTask(task?: TaskLike) {
	return task?.grading_mode === 'Completion' || resolveDeliveryMode(task) === 'Assign Only'
}

export function isCriteriaTask(task?: TaskLike) {
	return task?.grading_mode === 'Criteria'
}

export function isCollectWorkTask(task?: TaskLike) {
	return resolveDeliveryMode(task) === 'Collect Work'
}

export function supportsFeedback(task?: TaskLike) {
	return Boolean(task?.allow_feedback)
}

export function showsBooleanResult(task?: TaskLike) {
	return isBinaryTask(task) || isCompletionTask(task)
}

export function showsScoreSummary(task?: TaskLike) {
	if (isPointsTask(task)) return true
	if (!isCriteriaTask(task)) return false
	return task?.rubric_scoring_strategy !== 'Separate Criteria'
}

export function showsStatusControl(task?: TaskLike) {
	return resolveDeliveryMode(task) === 'Assess'
}

export function showMaxPointsPill(task?: TaskLike) {
	return isPointsTask(task) && task?.max_points !== null && task?.max_points !== undefined
}

export function isAssessedQuizTask(task?: TaskLike) {
	return task?.task_type === 'Quiz' && resolveDeliveryMode(task) === 'Assess'
}

export function scoreSummaryLabel(task?: TaskLike) {
	return isCriteriaTask(task) ? 'Total' : 'Score'
}

export function booleanControlLabel(task?: TaskLike) {
	return isBinaryTask(task) ? 'Yes/No' : 'Completion'
}

export function booleanPositiveLabel(task?: TaskLike) {
	return isBinaryTask(task) ? 'Yes' : 'Complete'
}

export function booleanNegativeLabel(task?: TaskLike) {
	return isBinaryTask(task) ? 'No' : 'Not complete'
}

export function taskModeBadge(task?: TaskLike) {
	if (isCriteriaTask(task)) return 'Criteria'
	if (isPointsTask(task)) return 'Points'
	if (isBinaryTask(task)) return 'Yes/No'
	if (isCompletionTask(task)) return 'Complete'
	if (resolveDeliveryMode(task) === 'Collect Work') return 'Collect'
	return null
}

export function normalizeFeedback(value?: string | null) {
	if (!value) return ''
	try {
		if (typeof DOMParser !== 'undefined') {
			const parser = new DOMParser()
			const doc = parser.parseFromString(value, 'text/html')
			const text = doc.body.innerText || doc.body.textContent || ''
			return text.replace(/\u00a0/g, ' ').trim()
		}
	} catch {
		/* fall through to regex cleanup */
	}

	return value
		.replace(/<br\s*\/?>/gi, '\n')
		.replace(/<\/p>/gi, '\n')
		.replace(/<[^>]*>/g, '')
		.replace(/\u00a0/g, ' ')
		.replace(/\n{3,}/g, '\n\n')
		.trim()
}
