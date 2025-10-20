// Student Attendance Tool – Vue bridge
// Loads the compiled frappe-ui bundle and mounts the SPA component inside the desk page.

frappe.provide('ifitwala_ed.studentAttendanceTool')

frappe.pages['student_attendance_tool'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Student Attendance'),
		single_column: true,
	})

	page.set_primary_action(null)
	page.clear_primary_action()
	page.clear_actions()

	const mountPoint = document.createElement('div')
	mountPoint.id = 'student-attendance-tool-root'
	mountPoint.classList.add('student-attendance-tool-root', 'h-full')
	page.main.empty().append(mountPoint)

	const assets = [
		'/assets/ifitwala_ed/dist/student_attendance_tool.bundle.css',
		'/assets/ifitwala_ed/dist/student_attendance_tool.bundle.js',
	]

	frappe.require(assets, () => {
		const mount = window.ifitwala_ed?.studentAttendanceTool?.mount
		if (typeof mount === 'function') {
			mount(mountPoint, page)
		} else {
			console.error('[StudentAttendanceTool] mount function not found on window.ifitwala_ed')
			mountPoint.innerHTML = `
				<div class="p-6 text-center text-muted">
					${__('Unable to load Student Attendance tool. Please refresh the page.')}
				</div>`
		}
	})
}

