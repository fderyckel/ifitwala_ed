// ifitwala_ed/assessment/doctype/task/task_calendar.js
// Native Frappe Calendar config for Task

frappe.views.calendar['Task'] = {
	field_map: {
		start: 'due_date',
		end: 'due_date',
		id: 'name',
		title: 'title',
		allDay: 'allDay' // we force 0 in server, but map stays
	},
	gantt: false,
	order_by: 'due_date asc, name asc',
	// The server method feeding events:
	get_events_method: 'ifitwala_ed.assessment.assessment_calendar_utils.get_task_events',

	// Calendar filter UI across the toolbar (Frappe auto-wires these if present)
	filters: [
		{ fieldtype: 'Link', label: __('School'), options: 'School', fieldname: 'school' },
		{ fieldtype: 'Link', label: __('Academic Year'), options: 'Academic Year', fieldname: 'academic_year' },
		{ fieldtype: 'Link', label: __('Program'), options: 'Program', fieldname: 'program' },
		{ fieldtype: 'Link', label: __('Course'), options: 'Course', fieldname: 'course' },
		{ fieldtype: 'Link', label: __('Student Group'), options: 'Student Group', fieldname: 'student_group' },
		{ fieldtype: 'Link', label: __('Instructor (User)'), options: 'User', fieldname: 'instructor_user' },
		{ fieldtype: 'Link', label: __('Student'), options: 'Student', fieldname: 'student' },
		{ fieldtype: 'Select', label: __('Status'), fieldname: 'status',
			options: ['', 'Draft', 'Published', 'Open', 'Closed'] },
		{ fieldtype: 'Select', label: __('Delivery Type'), fieldname: 'delivery_type',
			options: ['', 'Assignment', 'Quiz', 'Discussion', 'Checkpoint', 'External Tool', 'Other'] },
		{ fieldtype: 'Check', label: __('Is Graded'), fieldname: 'is_graded' }
	],

	// Sensible defaults
	options: {
		headerToolbar: {
			left: 'prev,next today',
			center: 'title',
			right: 'dayGridMonth,timeGridWeek,listWeek'
		},
		initialView: 'dayGridMonth'
	}
};
