// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/setup/doctype/meeting/meeting.js

frappe.ui.form.on('Meeting', {
	refresh(frm) {
		// Bulk attendance helpers
		frm.add_custom_button(__('Mark All Present'), () => {
			(frm.doc.participants || []).forEach(r => {
				r.attendance_status = 'Present';
			});
			frm.refresh_field('participants');
		});

		frm.add_custom_button(__('Mark All Absent'), () => {
			(frm.doc.participants || []).forEach(r => {
				r.attendance_status = 'Absent';
			});
			frm.refresh_field('participants');
		});

		// Schedule next meeting helper
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Schedule Next Meeting'), () => {
				const defaultOffset = 14;
				const baseDate = frm.doc.date || frappe.datetime.get_today();
				const defaultDate = frappe.datetime.add_days(baseDate, defaultOffset);

				const dialog = new frappe.ui.Dialog({
					title: __('Schedule Next Meeting'),
					fields: [
						{
							fieldname: 'offset_days',
							fieldtype: 'Int',
							label: __('Days until next meeting'),
							default: defaultOffset,
						},
						{
							fieldname: 'new_date',
							fieldtype: 'Date',
							label: __('New Date'),
							default: defaultDate,
						},
						{
							fieldname: 'new_time',
							fieldtype: 'Time',
							label: __('Start Time'),
							default: frm.doc.start_time,
						},
					],
					primary_action_label: __('Create'),
					primary_action: data => {
						frappe.new_doc('Meeting', {
							meeting_name: (frm.doc.meeting_name || '') + ' – next',
							meeting_code: '',
							team: frm.doc.team,
							date: data.new_date,
							start_time: data.new_time,
							location: frm.doc.location,
							agenda: frm.doc.agenda,
							participants: (frm.doc.participants || []).map(r => ({
								participant: r.participant,
								role_in_meeting: r.role_in_meeting,
								attendance_status: 'Absent',
							})),
						});
						dialog.hide();
					},
				});
				dialog.show();
			});
		}

		// Restrict participant User selection (only enabled users)
		const gridField = frm.fields_dict.participants?.grid.get_field('participant');
		if (gridField) {
			gridField.get_query = function () {
				return {
					filters: {
						enabled: 1,
					},
				};
			};
		}
	},

	team(frm) {
		// When Team changes, offer to load team members as participants
		if (!frm.doc.team) {
			return;
		}

		const has_participants =
			Array.isArray(frm.doc.participants) && frm.doc.participants.length > 0;

		if (has_participants) {
			frappe.confirm(
				__(
					'Do you want to replace the current participants with all members of this Team?'
				),
				() => {
					load_team_participants(frm, true);
				},
				() => {
					// No → keep existing participants
				}
			);
		} else {
			load_team_participants(frm, true);
		}
	},
});

frappe.ui.form.on('Meeting Participant', {
	employee(frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		if (!row.employee) {
			frappe.model.set_value(cdt, cdn, 'participant', null);
			frappe.model.set_value(cdt, cdn, 'participant_name', null);
			return;
		}

		frappe.db
			.get_value('Employee', row.employee, ['employee_full_name', 'user_id'])
			.then(r => {
				const data = r.message || {};
				if (data.employee_full_name) {
					frappe.model.set_value(cdt, cdn, 'participant_name', data.employee_full_name);
				}
				if (data.user_id) {
					frappe.model.set_value(cdt, cdn, 'participant', data.user_id);
					// After setting participant, enforce duplicate guard
					prevent_duplicate_participant(frm, cdt, cdn);
				}
			});
	},

	participant(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.participant) {
			return;
		}

		// Live duplicate guard first
		if (prevent_duplicate_participant(frm, cdt, cdn)) {
			// Duplicate was found and cleared, stop here.
			return;
		}

		// Keep participant_name in sync with User.full_name
		frappe.db
			.get_value('User', row.participant, 'full_name')
			.then(r => {
				const fullName = r.message?.full_name;
				if (fullName) {
					frappe.model.set_value(cdt, cdn, 'participant_name', fullName);
				}
			});

		// If Employee is empty, try to resolve from User.user_id
		if (!row.employee) {
			frappe.db
				.get_value('Employee', { user_id: row.participant }, 'name')
				.then(res => {
					const employee = res.message?.name;
					if (employee) {
						frappe.model.set_value(cdt, cdn, 'employee', employee);
					}
				});
		}
	},
});

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function load_team_participants(frm, replace) {
	if (!frm.doc.team) {
		return;
	}

	frappe.call({
		method: 'ifitwala_ed.setup.doctype.meeting.meeting.get_team_participants',
		args: {
			team: frm.doc.team,
		},
		callback: function (r) {
			const data = r.message || [];
			if (!data.length) {
				frappe.msgprint({
					title: __('No Team Members Found'),
					message: __(
						'No Team Members with linked Users were found for this Team.'
					),
					indicator: 'yellow',
				});
				return;
			}

			if (replace) {
				frm.clear_table('participants');
			}

			const existing = new Set(
				(frm.doc.participants || [])
					.map(row => row.participant)
					.filter(u => !!u)
			);

			data.forEach(row => {
				if (!row.user_id) return;
				if (existing.has(row.user_id)) return;

				const child = frm.add_child('participants');
				child.participant = row.user_id;
				if (row.full_name) {
					child.participant_name = row.full_name;
				}
				// If Meeting Participant child has an employee field, keep it in sync
				if (row.employee && child.employee !== undefined) {
					child.employee = row.employee;
				}

				existing.add(row.user_id);
			});

			frm.refresh_field('participants');
		},
	});
}

/**
 * Prevent the same participant (User) from being added twice.
 *
 * Returns:
 *   true  → a duplicate was found and the current row was cleared.
 *   false → no duplicate.
 */
function prevent_duplicate_participant(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.participant) {
		return false;
	}

	const all_rows = frm.doc.participants || [];
	const same_user_rows = all_rows.filter(r => r.participant === row.participant);

	if (same_user_rows.length > 1) {
		frappe.msgprint({
			title: __('Duplicate Participant'),
			message: __('This user is already in the participants list.'),
			indicator: 'orange',
		});

		frappe.model.set_value(cdt, cdn, 'participant', null);
		if (row.participant_name) {
			frappe.model.set_value(cdt, cdn, 'participant_name', null);
		}
		if (row.employee) {
			frappe.model.set_value(cdt, cdn, 'employee', null);
		}

		frm.refresh_field('participants');
		return true;
	}

	return false;
}

