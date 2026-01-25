// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Task Submission", {
	refresh(frm) {
		frm.trigger("setup_governed_attachment_upload");
	},

	setup_governed_attachment_upload(frm) {
		const openUploader = () => {
			if (frm.is_new()) {
				frappe.msgprint(__("Please save the Task Submission before uploading attachments."));
				return;
			}

			new frappe.ui.FileUploader({
				method: "ifitwala_ed.utilities.governed_uploads.upload_task_submission_attachment",
				args: { task_submission: frm.doc.name },
				doctype: "Task Submission",
				docname: frm.doc.name,
				allow_multiple: false,
				on_success(file_doc) {
					const payload = file_doc?.message
						|| (Array.isArray(file_doc) ? file_doc[0] : file_doc)
						|| (typeof file_doc === "string" ? { file_url: file_doc } : null);
					if (!payload || !payload.file_url) {
						frappe.msgprint(__("Upload succeeded but no file URL was returned."));
						return;
					}

					frm.refresh_field("attachments");
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
			__("Use the Upload Submission Attachment action to attach governed files.")
		);

		frm.remove_custom_button(__("Upload Submission Attachment"), __("Actions"));
		frm.remove_custom_button(__("Upload Submission Attachment"));
		frm.add_custom_button(
			__("Upload Submission Attachment"),
			openUploader
		);
	},
});
