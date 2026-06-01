const LOAD_STUDENTS_METHOD =
	"ifitwala_ed.accounting.doctype.student_account_holder_tool.student_account_holder_tool.load_students";
const CREATE_ACCOUNT_HOLDERS_METHOD =
	"ifitwala_ed.accounting.doctype.student_account_holder_tool.student_account_holder_tool.create_account_holders";

async function ensure_tool_saved(frm) {
	if (frm.is_new() || frm.is_dirty()) {
		await frm.save();
	}
}

function render_headline(frm) {
	if (!frm.dashboard?.set_headline) {
		return;
	}

	const rows = frm.doc.students || [];
	if (!rows.length) {
		frm.dashboard.set_headline(
			`<span class="text-muted">${frappe.utils.escape_html(
				__("Load students who are missing Account Holders, review sibling groups, then create or link payers in batch.")
			)}</span>`
		);
		return;
	}

	const selected = rows.filter((row) => cint(row.selected)).length;
	const blocked = rows.filter((row) => row.action === "Blocked").length;
	frm.dashboard.set_headline(
		`<span class="text-muted">${frappe.utils.escape_html(
			__("Students loaded")
		)}: ${rows.length}. ${frappe.utils.escape_html(__("Selected"))}: ${selected}. ${frappe.utils.escape_html(
			__("Blocked")
		)}: ${blocked}.</span>`
	);
}

async function load_students(frm) {
	if (!frm.doc.organization) {
		frappe.msgprint(__("Choose an Organization before loading students."));
		return;
	}

	await ensure_tool_saved(frm);
	const response = await frappe.call({
		method: LOAD_STUDENTS_METHOD,
		args: { name: frm.doc.name },
		freeze: true,
		freeze_message: __("Loading students without Account Holders…"),
	});
	const summary = response.message || {};
	await frm.reload_doc();
	frappe.show_alert({
		message: __("Loaded {0} student row(s).", [summary.loaded_count || 0]),
		indicator: summary.loaded_count ? "green" : "orange",
	});
}

async function create_account_holders(frm) {
	const selected = (frm.doc.students || []).filter((row) => cint(row.selected));
	if (!selected.length) {
		frappe.msgprint(__("Select at least one student row first."));
		return;
	}

	await ensure_tool_saved(frm);
	const response = await frappe.call({
		method: CREATE_ACCOUNT_HOLDERS_METHOD,
		args: { name: frm.doc.name },
		freeze: true,
		freeze_message: __("Creating and linking Account Holders..."),
	});
	const summary = response.message || {};
	await frm.reload_doc();
	frappe.msgprint({
		title: __("Account Holder Setup Finished"),
		message:
			summary.result_summary ||
			__("Created {0} Account Holder(s), linked {1} Student(s), failed {2}.", [
				summary.created_count || 0,
				summary.linked_count || 0,
				summary.failed_count || 0,
			]),
		indicator: summary.failed_count ? "orange" : "green",
	});
}

function add_action_buttons(frm) {
	frm.add_custom_button(__("Load Students"), () => {
		load_students(frm).catch((error) => {
			frappe.msgprint(error?.message || __("Unable to load students."));
		});
	});

	if ((frm.doc.students || []).length) {
		frm.add_custom_button(
			__("Create / Link Account Holders"),
			() => {
				create_account_holders(frm).catch((error) => {
					frappe.msgprint(error?.message || __("Unable to create or link Account Holders."));
				});
			},
			__("Actions")
		);
	}

	if (frm.doc.source_program_billing_plan) {
		frm.add_custom_button(
			__("Open Program Billing Plan"),
			() => frappe.set_route("Form", "Program Billing Plan", frm.doc.source_program_billing_plan),
			__("View")
		);
	}
}

frappe.ui.form.on("Student Account Holder Tool", {
	refresh(frm) {
		frm.clear_custom_buttons();
		frm.set_query("school", () => ({
			filters: {
				organization: frm.doc.organization || "",
			},
		}));
		frm.set_query("program_offering", () => ({
			filters: {},
		}));
		add_action_buttons(frm);
		render_headline(frm);

		if (frm.is_new() && frm.doc.source_program_billing_plan && !frm.__auto_loaded_from_plan) {
			frm.__auto_loaded_from_plan = true;
			setTimeout(() => {
				load_students(frm).catch((error) => {
					frappe.msgprint(error?.message || __("Unable to load students from the Billing Plan."));
				});
			}, 250);
		}
	},

	load_students(frm) {
		load_students(frm).catch((error) => {
			frappe.msgprint(error?.message || __("Unable to load students."));
		});
	},

	create_account_holders(frm) {
		create_account_holders(frm).catch((error) => {
			frappe.msgprint(error?.message || __("Unable to create or link Account Holders."));
		});
	},

	organization(frm) {
		if (frm.doc.school) {
			frm.set_value("school", null);
		}
	},

	program_offering(frm) {
		if (!frm.doc.program_offering && frm.doc.academic_year) {
			frm.set_value("academic_year", null);
		}
	},
});
