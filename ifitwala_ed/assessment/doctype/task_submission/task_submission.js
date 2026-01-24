// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Task Submission", {
	refresh(frm) {
		frm.trigger("setup_governed_attachment_upload");
	},

	setup_governed_attachment_upload(frm) {
		const table_field = frm.get_field("attachments");
		if (table_field?.grid) {
			table_field.grid.update_docfield_property("file", "read_only", 1);
		}

		frm.remove_custom_button(__("Upload Submission Attachment"), __("Actions"));
		frm.add_custom_button(
			__("Upload Submission Attachment"),
			() => {
				if (frm.is_new()) {
					frappe.msgprint(__("Please save the Task Submission before uploading attachments."));
					return;
				}

				new frappe.ui.FileUploader({
					method: "ifitwala_ed.utilities.governed_uploads.upload_task_submission_attachment",
					args: { task_submission: frm.doc.name },
					allow_multiple: false,
					on_success(file_doc) {
						if (!file_doc || !file_doc.file_url) {
							frappe.msgprint(__("Upload succeeded but no file URL was returned."));
							return;
						}

						const row = frm.add_child("attachments");
						row.section_break_sbex = file_doc.file_name || __("Attachment");
						row.file = file_doc.file_url;
						row.file_name = file_doc.file_name;
						row.file_size = file_doc.file_size;
						row.public = 0;
						frm.refresh_field("attachments");
					},
				});
			},
			__("Actions")
		);
	},
});
