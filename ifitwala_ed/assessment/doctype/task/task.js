// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/assessment/doctype/task/task.js

frappe.ui.form.on("Task", {
	setup(frm) {
		set_unit_plan_query(frm);
		set_quiz_question_bank_query(frm);
	},

	refresh(frm) {
		set_unit_plan_query(frm);
		set_quiz_question_bank_query(frm);
		frm.trigger("setup_governed_resource_upload");
		frm.trigger("setup_governed_drive_link");
	},

	course(frm) {
		reset_curriculum_fields(frm);
	},

	default_course(frm) {
		reset_curriculum_fields(frm);
	},

	quiz_question_bank(frm) {
		enforce_quiz_defaults(frm);
	},

	unit_plan(frm) {
	},

	default_delivery_mode(frm) {
		enforce_delivery_mode_defaults(frm);
	},

	setup_governed_resource_upload(frm) {
		const openUploader = () => {
			if (frm.is_new()) {
				frappe.msgprint(__("Please save the Task before uploading resources."));
				return;
			}

			new frappe.ui.FileUploader({
				method: "ifitwala_ed.utilities.governed_uploads.upload_task_resource",
				args: { task: frm.doc.name },
				doctype: "Task",
				docname: frm.doc.name,
				is_private: 1,
				disable_private: true,
				allow_multiple: false,
				on_success(fileDoc) {
					const payload = fileDoc?.message
						|| (Array.isArray(fileDoc) ? fileDoc[0] : fileDoc)
						|| (typeof fileDoc === "string" ? { file_url: fileDoc } : null);
					if (payload?.file_url) {
						frm.refresh_field("attachments");
					}
					frm.reload_doc();
				},
				on_error() {
					frappe.msgprint(__("Upload failed. Please try again."));
				},
			});
		};

		const table_field = frm.get_field("attachments");
		if (table_field?.grid) {
			table_field.grid.update_docfield_property("file", "read_only", 1);
		}

		frm.set_df_property(
			"attachments",
			"description",
			__("Use the Upload Task Resource action for governed files. External URLs can still be added manually.")
		);

		frm.remove_custom_button(__("Upload Task Resource"), __("Actions"));
		frm.remove_custom_button(__("Upload Task Resource"));
		frm.add_custom_button(
			__("Upload Task Resource"),
			openUploader
		);
	},

	setup_governed_drive_link(frm) {
		const drive = window.ifitwala_ed && window.ifitwala_ed.drive;
		if (!drive || typeof drive.addOpenContextButton !== "function" || frm.is_new()) {
			return;
		}

		drive.addOpenContextButton(frm, {
			doctype: "Task",
			name: frm.doc.name,
			label: __("Open in Drive"),
			group: __("Actions"),
		});
	}
});

function get_course_value(frm) {
	return (frm.doc.course || frm.doc.default_course || "").trim();
}

function set_unit_plan_query(frm) {
	frm.set_query("unit_plan", () => {
		const course = get_course_value(frm);
		if (!course) {
			return {};
		}
		return { filters: { course } };
	});
}

function set_quiz_question_bank_query(frm) {
	frm.set_query("quiz_question_bank", () => {
		const course = get_course_value(frm);
		if (!course) {
			return {};
		}
		return { filters: { course, is_published: 1 } };
	});
}

function reset_curriculum_fields(frm) {
	if (frm.doc.unit_plan) {
		frm.set_value("unit_plan", null);
	}
	set_unit_plan_query(frm);
}

function enforce_delivery_mode_defaults(frm) {
	if (frm.doc.default_delivery_mode && frm.doc.default_delivery_mode !== "Assess") {
		if (frm.doc.default_grading_mode !== "None") {
			frm.set_value("default_grading_mode", "None");
		}
		clear_grading_defaults(frm);
	}
	enforce_quiz_defaults(frm);
}

function clear_grading_defaults(frm) {
	const fields = ["default_max_points", "default_grade_scale", "default_rubric_scoring_strategy"];
	for (const field of fields) {
		if (frm.doc[field]) {
			frm.set_value(field, null);
		}
	}
}

function enforce_quiz_defaults(frm) {
	if (frm.doc.task_type !== "Quiz") {
		return;
	}
	if (frm.doc.default_delivery_mode === "Assess") {
		if (frm.doc.default_grading_mode !== "Points") {
			frm.set_value("default_grading_mode", "Points");
		}
		if (!frm.doc.default_max_points && frm.doc.quiz_question_count) {
			frm.set_value("default_max_points", frm.doc.quiz_question_count);
		}
		return;
	}
	if (frm.doc.default_grading_mode !== "None") {
		frm.set_value("default_grading_mode", "None");
	}
	clear_grading_defaults(frm);
}
