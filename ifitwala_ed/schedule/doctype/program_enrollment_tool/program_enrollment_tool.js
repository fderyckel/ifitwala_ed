// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.js

const REQUEST_SOURCE_MODE = 'Program Enrollment Request';

function canFetchStudents(frm) {
	const source = frm.doc.get_students_from;
	if (source === 'Program Enrollment') {
		return Boolean(frm.doc.program_offering && frm.doc.target_academic_year);
	}
	if (source === REQUEST_SOURCE_MODE) {
		return Boolean(frm.doc.program_offering && frm.doc.target_academic_year);
	}
	if (source === 'Cohort') {
		return Boolean(frm.doc.student_cohort);
	}
	return false;
}

function isExistingRequestSource(frm) {
	return frm.doc.get_students_from === REQUEST_SOURCE_MODE;
}

function hasDestinationContext(frm) {
	return Boolean(frm.doc.new_program_offering && frm.doc.new_target_academic_year);
}

function hasStudents(frm) {
	return Boolean((frm.doc.students || []).length);
}

function hasRequestSourceContext(frm) {
	return Boolean(frm.doc.program_offering && frm.doc.target_academic_year);
}

function prettyCountLabel(key) {
	return String(key || '')
		.split('_')
		.map(part => part.charAt(0).toUpperCase() + part.slice(1))
		.join(' ');
}

function runToolAction(frm, method) {
	if (method === 'prepare_requests' && isExistingRequestSource(frm)) {
		frappe.msgprint(__('Prepare Requests is only used when the tool is building new requests from students.'));
		return;
	}

	if (isExistingRequestSource(frm)) {
		if (!hasRequestSourceContext(frm)) {
			frappe.msgprint(__('Please choose the request Program Offering and request Academic Year first.'));
			return;
		}
	} else if (!hasDestinationContext(frm)) {
		frappe.msgprint(__('Please choose a destination Program Offering and destination Academic Year first.'));
		return;
	}

	if (!hasStudents(frm)) {
		frappe.msgprint(isExistingRequestSource(frm) ? __('Please load requests first.') : __('Please load or add students first.'));
		return;
	}

	frappe.call({
		doc: frm.doc,
		method,
		freeze: true
	});
}

async function openRequestOverview(frm) {
	if (!hasRequestSourceContext(frm)) {
		frappe.msgprint(__('Please choose the request Program Offering and request Academic Year first.'));
		return;
	}

	const response = await frappe.db.get_value('Program Offering', frm.doc.program_offering, ['school', 'program']);
	const offeringContext = response?.message || {};

	frappe.route_options = {
		view_mode: 'Student x Course Matrix',
		school: offeringContext.school || '',
		academic_year: frm.doc.target_academic_year || '',
		program: offeringContext.program || '',
		program_offering: frm.doc.program_offering || '',
		request_kind: 'Academic',
		latest_request_only: 1,
	};
	frappe.set_route('query-report', 'Program Enrollment Request Overview');
}

function applyToolCopy(frm) {
	const existingRequestSource = isExistingRequestSource(frm);
	frm.set_df_property('program_offering', 'label', existingRequestSource ? __('Request Program Offering') : __('Source Program Offering'));
	frm.set_df_property('target_academic_year', 'label', existingRequestSource ? __('Request Academic Year') : __('Source Academic Year'));
	frm.set_df_property('get_students', 'label', existingRequestSource ? __('Get Existing Requests') : __('Get Students'));
	frm.set_df_property('new_enrollment_details_section', 'label', existingRequestSource ? __('Materialization Details') : __('New Enrollment Details'));
	frm.set_df_property('new_enrollment_date', 'label', existingRequestSource ? __('Enrollment Date') : __('Destination Enrollment Date'));
}

function renderToolGuidance(frm) {
	if (!frm.dashboard?.set_headline) {
		return;
	}

	if (isExistingRequestSource(frm)) {
		if (!hasStudents(frm)) {
			frm.dashboard.set_headline(
				`<span class="text-muted">${frappe.utils.escape_html(__('Load existing academic Program Enrollment Requests, then validate, approve, or materialize them in batch.'))}</span>`
			);
			return;
		}

		const counts = {
			draft: 0,
			submitted: 0,
			approved: 0,
			valid: 0,
			invalid: 0,
			override: 0,
			materialized: 0
		};
		(frm.doc.students || []).forEach((row) => {
			const status = String(row.request_status || '').trim();
			const validationStatus = String(row.validation_status || '').trim();
			if (status === 'Draft') counts.draft += 1;
			if (status === 'Submitted' || status === 'Under Review') counts.submitted += 1;
			if (status === 'Approved') counts.approved += 1;
			if (validationStatus === 'Valid') counts.valid += 1;
			if (validationStatus === 'Invalid') counts.invalid += 1;
			if (Number(row.requires_override || 0) === 1) counts.override += 1;
			if (Number(row.already_materialized || 0) === 1) counts.materialized += 1;
		});
		frm.dashboard.set_headline(
			`<span class="text-muted">${frappe.utils.escape_html(
				__('Requests loaded')
			)}: ${counts.draft} ${frappe.utils.escape_html(__('draft'))}, ${counts.submitted} ${frappe.utils.escape_html(__('submitted / under review'))}, ${counts.approved} ${frappe.utils.escape_html(__('approved'))}, ${counts.valid} ${frappe.utils.escape_html(__('valid'))}, ${counts.invalid} ${frappe.utils.escape_html(__('invalid'))}, ${counts.override} ${frappe.utils.escape_html(__('needs override'))}, ${counts.materialized} ${frappe.utils.escape_html(__('already materialized'))}.</span>`
		);
		return;
	}

	frm.dashboard.set_headline(
		`<span class="text-muted">${frappe.utils.escape_html(__('Load a student population, prepare requests, then validate, approve, and materialize in batch.'))}</span>`
	);
}

frappe.ui.form.on('Program Enrollment Tool', {
	refresh(frm) {
		frm.disable_save();
		frm.clear_custom_buttons();

		if (!frm.__pe_rt_bound) {
			frappe.realtime.on('program_enrollment_tool', data => {
				frappe.hide_msgprint(true);
				frappe.show_progress(
					data.action_label || __('Processing'),
					data.progress?.[0] || 0,
					data.progress?.[1] || 0
				);
			});

			frappe.realtime.on('program_enrollment_tool_done', summary => {
				const counts = Object.entries(summary?.counts || {})
					.map(([key, value]) => `${prettyCountLabel(key)}: ${value}`)
					.join(', ');
				const detailsLink = summary?.details_link
					? `<br><a href="${summary.details_link}" target="_blank">${__('Download details CSV')}</a>`
					: '';
				frappe.msgprint({
					title: summary?.title || __('Batch Finished'),
					message: `${counts}${detailsLink}`,
					indicator: 'green'
				});
			});

			frm.__pe_rt_bound = true;
		}

		frm.set_query('target_academic_year', () => ({
			query: 'ifitwala_ed.schedule.doctype.program_enrollment_tool.program_enrollment_tool.program_offering_target_ay_query',
			filters: { program_offering: frm.doc.program_offering }
		}));

		frm.set_query('new_target_academic_year', () => ({
			query: 'ifitwala_ed.schedule.doctype.program_enrollment_tool.program_enrollment_tool.program_offering_target_ay_query',
			filters: { program_offering: frm.doc.new_program_offering }
		}));

		applyToolCopy(frm);
		toggleFilterFields(frm);
		addTableToolbar(frm);
		addActionButtons(frm);
		highlightTargetCollisions(frm);
		renderToolGuidance(frm);
	},

	get_students_from(frm) {
		applyToolCopy(frm);
		toggleFilterFields(frm);
		renderToolGuidance(frm);
	},

	program_offering(frm) {
		frm.set_value('target_academic_year', null);
	},

	new_program_offering(frm) {
		frm.set_value('new_target_academic_year', null);
	},

	get_students(frm) {
		if (!canFetchStudents(frm)) {
			frappe.msgprint(
				isExistingRequestSource(frm)
					? __('Please choose the request Program Offering and request Academic Year first.')
					: __('Please complete the required filters for the selected source first.')
			);
			return;
		}

		frm.set_value('students', []);
		frappe.call({
			doc: frm.doc,
			method: 'get_students',
			callback(r) {
				if (r.message) {
					frm.set_value('students', r.message);
					highlightTargetCollisions(frm);
					renderToolGuidance(frm);
					frm.refresh();
				}
			}
		});
	},

	enroll_students(frm) {
		runToolAction(frm, 'prepare_requests');
	}
});

function addActionButtons(frm) {
	if (isExistingRequestSource(frm)) {
		if (hasRequestSourceContext(frm)) {
			frm.add_custom_button(__('Open Request Overview'), () => {
				openRequestOverview(frm).catch((error) => {
					frappe.msgprint(error?.message || __('Unable to open the request overview.'));
				});
			}, __('Actions'));
		}
	} else if (!hasDestinationContext(frm)) {
		return;
	}

	if (!hasStudents(frm)) {
		return;
	}

	if (!isExistingRequestSource(frm)) {
		frm.toggle_display('enroll_students', true);
	} else {
		frm.toggle_display('enroll_students', false);
	}

	frm.add_custom_button(__('Validate Requests'), () => runToolAction(frm, 'validate_requests'), __('Actions'));
	frm.add_custom_button(__('Approve Valid Requests'), () => runToolAction(frm, 'approve_requests'), __('Actions'));
	frm.add_custom_button(__('Materialize Requests'), () => runToolAction(frm, 'materialize_requests'), __('Actions'));
}

function addTableToolbar(frm) {
	const grid = frm.get_field('students').grid;
	if (grid.__programEnrollmentToolToolbarBound) {
		return;
	}

	grid.add_custom_button(__('Select All'), () => {
		grid.grid_rows.forEach(row => {
			row.doc.__checked = 1;
		});
		grid.refresh();
	});

	grid.add_custom_button(__('Clear Table'), () => {
		frm.set_value('students', []);
	});

	grid.add_custom_button(__('Add Student…'), () => {
		frappe.prompt(
			[{ fieldtype: 'Link', label: 'Student', fieldname: 'student', options: 'Student', reqd: 1 }],
			values => {
				frappe.db.get_value('Student', values.student, ['student_full_name', 'cohort']).then(({ message }) => {
					grid.add_new_row({
						student: values.student,
						student_name: message.student_full_name,
						student_cohort: message.cohort
					});
					grid.refresh();
				});
			}
		);
	});

	grid.__programEnrollmentToolToolbarBound = true;
}

function highlightTargetCollisions(frm) {
	const grid = frm.get_field('students').grid;
	grid.grid_rows.forEach(row => {
		const doc = row.doc || {};
		let background = '';
		let title = '';
		if (isExistingRequestSource(frm)) {
			if (Number(doc.already_materialized || 0) === 1) {
				background = '#e8f5e9';
				title = __('Already materialized into Program Enrollment.');
			} else if (Number(doc.requires_override || 0) === 1) {
				background = '#fff4e5';
				title = __('Request requires an override before approval.');
			} else if (String(doc.validation_status || '').trim() === 'Invalid') {
				background = '#ffebe9';
				title = __('Request is invalid and needs review before approval.');
			} else if (String(doc.request_status || '').trim() === 'Approved' && String(doc.validation_status || '').trim() === 'Valid') {
				background = '#eef6ff';
				title = __('Request is approved and ready to materialize.');
			} else if (String(doc.validation_status || '').trim() === 'Valid') {
				background = '#f0f9ff';
				title = __('Request is valid and can be approved.');
			}
		} else if (doc.already_enrolled) {
			background = '#ffebe9';
			title = __('Student is already enrolled in the destination offering and academic year.');
		}
		row.wrapper.css({ background });
		row.wrapper.attr('title', title);
	});
}

function toggleFilterFields(frm) {
	const source = frm.doc.get_students_from;

	frm.toggle_display('program_offering', false);
	frm.toggle_display('target_academic_year', false);
	frm.toggle_display('student_cohort', false);
	frm.toggle_display('new_program_offering', source !== REQUEST_SOURCE_MODE);
	frm.toggle_display('new_target_academic_year', source !== REQUEST_SOURCE_MODE);
	frm.toggle_display('new_enrollment_date', source !== 'Cohort' || source === REQUEST_SOURCE_MODE || hasDestinationContext(frm));
	frm.toggle_display('enroll_students', source !== REQUEST_SOURCE_MODE);

	if (source === 'Program Enrollment') {
		frm.toggle_display('program_offering', true);
		frm.toggle_display('target_academic_year', true);
		frm.toggle_display('student_cohort', true);
	} else if (source === REQUEST_SOURCE_MODE) {
		frm.toggle_display('program_offering', true);
		frm.toggle_display('target_academic_year', true);
		frm.toggle_display('student_cohort', true);
	} else if (source === 'Cohort') {
		frm.toggle_display('student_cohort', true);
	}
}
