// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/setup/doctype/meeting/meeting.js

frappe.ui.form.on('Meeting', {
	refresh(frm) {
		frm.add_custom_button(__('Mark All Present'), () => {
			(frm.doc.participants || []).forEach(r => r.attendance_status = 'Present');
			frm.refresh_field('participants');
		});
		frm.add_custom_button(__('Mark All Absent'), () => {
			(frm.doc.participants || []).forEach(r => r.attendance_status = 'Absent');
			frm.refresh_field('participants');
		});

		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Schedule Next Meeting'), () => {
				const defaultOffset = 14;
				const defaultDate = frappe.datetime.add_days(frm.doc.date, defaultOffset);
				const dialog = new frappe.ui.Dialog({
					title: __('Schedule Next Meeting'),
					fields: [
						{ fieldname: 'offset_days', fieldtype: 'Int', label: __('Days until next meeting'), default: defaultOffset },
						{ fieldname: 'new_date',   fieldtype: 'Date', label: __('New Date'), default: defaultDate },
						{ fieldname: 'new_time',   fieldtype: 'Time', label: __('Start Time'), default: frm.doc.start_time }
					],
					primary_action_label: __('Create'),
					primary_action: data => {
						frappe.new_doc('Meeting', {
							meeting_name: frm.doc.meeting_name + ' – next',
							meeting_code: '',
							team: frm.doc.team,
							date: data.new_date,
							start_time: data.new_time,
							location: frm.doc.location,
							agenda: frm.doc.agenda,
							participants: frm.doc.participants.map(r => ({
								participant: r.participant,
								role_in_meeting: r.role_in_meeting,
								attendance_status: "Absent"
							}))
						});
						dialog.hide();
					}
				});
				dialog.show();
			});
		}

		const gridField = frm.fields_dict.participants?.grid.get_field('participant');
		if (gridField) {
			gridField.get_query = function() {
				return {
					filters: {
						"enabled": 1
					}
				};
			};
		}
	}
});

frappe.ui.form.on('Meeting Participant', {
	employee(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.employee) {
			frappe.model.set_value(cdt, cdn, 'participant', null);
			frappe.model.set_value(cdt, cdn, 'participant_name', null);
			return;
		}
		frappe.db.get_value('Employee', row.employee, ['employee_full_name', 'user_id'])
			.then(r => {
				const data = r.message || {};
				if (data.employee_full_name) {
					frappe.model.set_value(cdt, cdn, 'participant_name', data.employee_full_name);
				}
				if (data.user_id) {
					frappe.model.set_value(cdt, cdn, 'participant', data.user_id);
				}
			});
	},
    participant(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.participant) {
			return;
		}
        frappe.db.get_value('User', row.participant, 'full_name')
            .then(r => {
				const fullName = r.message?.full_name;
				if (fullName) {
					frappe.model.set_value(cdt, cdn, 'participant_name', fullName);
				}
            });
		if (!row.employee) {
			frappe.db.get_value('Employee', { user_id: row.participant }, 'name')
				.then(res => {
					const employee = res.message?.name;
					if (employee) {
						frappe.model.set_value(cdt, cdn, 'employee', employee);
					}
				});
		}
    }
});
