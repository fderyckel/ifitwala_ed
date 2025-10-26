import { createApp } from 'vue'
import { FrappeUI, setConfig, toast } from 'frappe-ui'
import StudentAttendanceTool from '@/pages/staff/schedule/student-attendance-tool/StudentAttendanceTool.vue'
import '@/style.css'
import 'frappe-ui/src/style.css'
import { setupFrappeUI } from '@/resources/frappe'

// Ensure frappe-ui resources use the standard frappeRequest helper
setupFrappeUI()

// Provide a sensible global error handler so desk users see feedback
setConfig('onError', (error: any) => {
	if (!error) return
	const message =
		typeof error === 'string'
			? error
			: error._server_messages || error.message || __('An unexpected error occurred.')

	if (message) {
		toast({
			title: __('Something went wrong'),
			message,
			appearance: 'danger',
		})
	}
	console.error('[StudentAttendanceTool] Unhandled error', error)
})

export function mountStudentAttendanceTool(target: Element, page?: any) {
	const app = createApp(StudentAttendanceTool, { page })
	app.use(FrappeUI)
	app.mount(target)
	return app
}

declare global {
	interface Window {
		ifitwala_ed?: Record<string, any>
	}
}

window.ifitwala_ed = window.ifitwala_ed || {}
window.ifitwala_ed.studentAttendanceTool = {
	mount: mountStudentAttendanceTool,
}
