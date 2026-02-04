// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/setup/doctype/meeting/meeting.js

frappe.ui.form.on('Meeting', {
	refresh(frm) {
		// Auto default follow-up date if applicable
		set_auto_follow_up_due_date(frm);

		// Smart default for visibility_scope on new meetings
		if (frm.is_new() && !frm.doc.visibility_scope) {
			if (frm.doc.team) {
				frm.set_value('visibility_scope', 'Team & Participants');
			} else {
				frm.set_value('visibility_scope', 'Participants Only');
			}
		}

		// Bulk attendance helpers
		frm.add_custom_button(__('Mark All Present'), () => {
			(frm.doc.participants || []).forEach(r => {
				r.attendance_status = 'Present';
			});
			frm.refresh_field('participants');
		});

		// Schedule next meeting helper
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Schedule Next Meeting'), () => {
				const defaultOffset = 7; // one week
				const baseDate = frm.doc.date || frappe.datetime.get_today();
				const defaultDate = frappe.datetime.add_days(baseDate, defaultOffset);

				const dialog = new frappe.ui.Dialog({
					title: __('Schedule Next Meeting'),
					fields: [
						{
							fieldname: 'offset_days',
							fieldtype: 'Int',
							label: __('Days until next meeting'),
							// no default on purpose → starts blank
							description: __('Leave blank to keep the suggested date below.'),
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
					primary_action: (data) => {
						const base = frm.doc.date || frappe.datetime.get_today();

						let next_date = data.new_date;
						const raw_offset = data.offset_days;

						// If offset_days is filled, override date from that
						if (
							raw_offset !== undefined &&
							raw_offset !== null &&
							String(raw_offset).trim() !== ''
						) {
							const offset = to_int(raw_offset, defaultOffset);
							next_date = frappe.datetime.add_days(base, offset);
						}

						// If still no date (user cleared everything), fall back to 1 week
						if (!next_date) {
							next_date = frappe.datetime.add_days(base, defaultOffset);
						}

						const next_time = data.new_time || frm.doc.start_time;

						if (!next_date) {
							frappe.msgprint(__('Please choose a date for the next meeting.'));
							return;
						}

						dialog.disable_primary_action();

						frappe.call({
							method: 'ifitwala_ed.setup.doctype.meeting.meeting.create_next_meeting',
							args: {
								source_meeting: frm.doc.name,
								new_date: next_date,
								new_time: next_time,
							},
						})
							.then(r => {
								const name = r.message;
								if (name) {
									frappe.set_route('Form', 'Meeting', name);
								}
								dialog.hide();
							})
							.always(() => {
								dialog.enable_primary_action();
							});
					},
				});

				// One-way helper: when offset changes, update date
				const offsetField = dialog.get_field('offset_days');
				if (offsetField) {
					offsetField.df.onchange = () => {
						const raw = dialog.get_value('offset_days');
						if (raw === undefined || raw === null || String(raw).trim() === '') {
							// Do nothing if cleared
							return;
						}
						const offset = to_int(raw, defaultOffset);
						const base = frm.doc.date || frappe.datetime.get_today();
						const new_date = frappe.datetime.add_days(base, offset);
						dialog.set_value('new_date', new_date);
					};
				}

				dialog.show();
			});
		}

		// Filter Academic Year to current/future, non-archived
		if (frm.fields_dict.academic_year) {
			frm.set_query('academic_year', function () {
				const filters = {
					archived: 0,
					year_end_date: ['>=', frappe.datetime.get_today()],
				};

				if (frm.doc.school) {
					filters.school = frm.doc.school;
				}

				return { filters };
			});
		}

		// Restrict participant User selection (only enabled users)
		const gridField =
			frm.fields_dict.participants &&
			frm.fields_dict.participants.grid &&
			frm.fields_dict.participants.grid.get_field('participant');

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

	validate(frm) {
		// Before saving, nudge: include creator? and assign Chair?
		ensure_creator_and_chair(frm);
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

	date(frm) {
		set_auto_follow_up_due_date(frm);
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
				// Default role if empty
				if (!row.role_in_meeting) {
					frappe.model.set_value(cdt, cdn, 'role_in_meeting', 'Participant');
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

		// Default role if empty
		if (!row.role_in_meeting) {
			frappe.model.set_value(cdt, cdn, 'role_in_meeting', 'Participant');
		}
	},
});

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function to_int(value, fallback = 0) {
	const parsed = parseInt(value, 10);
	return Number.isNaN(parsed) ? fallback : parsed;
}

function set_auto_follow_up_due_date(frm) {
	if (!frm.doc.date) {
		return;
	}

	const suggested = frappe.datetime.add_days(frm.doc.date, 14);
	const current = frm.doc.follow_up_due_date;
	const was_auto =
		frm._auto_follow_up_due_date && current === frm._auto_follow_up_due_date;

	if (!current || was_auto) {
		frm._auto_follow_up_due_date = suggested;
		frm.set_value('follow_up_due_date', suggested);
	} else {
		frm._auto_follow_up_due_date = null;
	}
}

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
				if (row.employee && child.employee !== undefined) {
					child.employee = row.employee;
				}
				// ⬇️ Default role for auto-added team members
				if (child.role_in_meeting !== undefined && !child.role_in_meeting) {
					child.role_in_meeting = 'Participant';
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

/**
 * Ensure:
 * 1) Current user is offered a seat in the meeting if not listed.
 * 2) If no one is Chair, offer to assign a Chair.
 *
 * Uses frappe.validated + re-save pattern:
 * - Cancel the current save.
 * - Run one or two confirms.
 * - After decisions, call frm.save() once more.
 */
function ensure_creator_and_chair(frm) {
	// Only enforce on draft
	if (frm.doc.docstatus !== 0) return;
	if (frm._role_checks_done) return;

	const currentUser = frappe.session.user;
	const participants = frm.doc.participants || [];

	const hasCurrentUser = participants.some(r => r.participant === currentUser);

	const hasChair = participants.some(
		r => (r.role_in_meeting || "").toLowerCase() === "chair"
	);
	const hasFacilitator = participants.some(
		r => (r.role_in_meeting || "").toLowerCase() === "facilitator"
	);

	// If everything is fine, allow save
	if (hasCurrentUser && (hasChair || hasFacilitator)) {
		frm._role_checks_done = true;
		return;
	}

	// Prevent automatic save; we will trigger save ourselves
	frappe.validated = false;

	//--------------------------------------------------------------------
	// 1. Ensure creator (current user) is included
	//--------------------------------------------------------------------
	const ensure_current_user = (callback) => {
		if (hasCurrentUser || currentUser === "Guest") {
			callback();
			return;
		}

		frappe.confirm(
			__(
				"You ({0}) are not listed as a participant. Do you want to be added to this meeting?",
				[currentUser]
			),
			() => {
				const row = frm.add_child("participants");
				row.participant = currentUser;
				row.role_in_meeting = row.role_in_meeting || "Participant";
				frm.refresh_field("participants");

				callback();
			},
			() => {
				// User declines; still proceed to role assignment
				callback();
			}
		);
	};

	//--------------------------------------------------------------------
	// 2. Ensure meeting has either Chair or Facilitator
	//--------------------------------------------------------------------
	const ensure_role_assignment = () => {
		const rows = frm.doc.participants || [];
		const nowHasChair = rows.some(
			r => (r.role_in_meeting || "").toLowerCase() === "chair"
		);
		const nowHasFacilitator = rows.some(
			r => (r.role_in_meeting || "").toLowerCase() === "facilitator"
		);

		// Already satisfied → save
		if (nowHasChair || nowHasFacilitator) {
			frm._role_checks_done = true;
			frm.save();
			return;
		}

		// Ask which role to assign
		frappe.prompt(
			[
				{
					fieldname: "chosen_role",
					fieldtype: "Select",
					label: __("Assign role"),
					options: ["Chair", "Facilitator"],
					reqd: 1,
				},
			],
			(values) => {
				const desiredRole = values.chosen_role;

				const freshRows = frm.doc.participants || [];

				// Prefer current user, else first participant
				let target =
					freshRows.find(r => r.participant === currentUser) ||
					freshRows[0];

				if (target) {
					target.role_in_meeting = desiredRole;
				}

				frm.refresh_field("participants");

				frm._role_checks_done = true;
				frm.save();
			},
			__("This meeting has no Chair or Facilitator"),
			__("Assign")
		);
	};

	//--------------------------------------------------------------------
	// Combined flow
	//--------------------------------------------------------------------
	ensure_current_user(ensure_role_assignment);
}
