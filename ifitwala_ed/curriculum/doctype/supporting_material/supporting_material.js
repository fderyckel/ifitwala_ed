// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Supporting Material", {
	refresh(frm) {
		frm.trigger("setup_governed_material_upload");
		frm.trigger("setup_governed_drive_link");
	},

	material_type(frm) {
		frm.trigger("setup_governed_material_upload");
	},

	setup_governed_material_upload(frm) {
		const fieldname = "file";
		const openUploader = () => {
			if (frm.is_new() || frm.is_dirty()) {
				frappe.msgprint(__("Please save the Supporting Material before uploading a file."));
				return;
			}

			if (frm.doc.material_type !== "File") {
				frappe.msgprint(
					__("Set Material Type to File before uploading a governed file for this Supporting Material.")
				);
				return;
			}

			new frappe.ui.FileUploader({
				method: "ifitwala_ed.utilities.governed_uploads.upload_supporting_material_file",
				args: { material: frm.doc.name },
				doctype: "Supporting Material",
				docname: frm.doc.name,
				fieldname,
				is_private: 1,
				disable_private: true,
				allow_multiple: false,
				on_success(fileDoc) {
					const payload = fileDoc?.message
						|| (Array.isArray(fileDoc) ? fileDoc[0] : fileDoc)
						|| (typeof fileDoc === "string" ? { file: fileDoc } : null);
					if (payload?.file) {
						frm.set_value({
							file: payload.file,
							file_name: payload.file_name || null,
							file_size: payload.file_size || null,
						});
						frm.refresh_field("file");
						frm.refresh_field("file_name");
						frm.refresh_field("file_size");
					}
					frm.reload_doc();
				},
				on_error() {
					frappe.msgprint(__("Supporting Material upload failed. Please try again."));
				},
			});
		};

		frm.set_df_property(
			fieldname,
			"description",
			__("Use Upload Material File to attach the governed file for this Supporting Material record.")
		);

		frm.remove_custom_button(__("Upload Material File"), __("Actions"));
		frm.remove_custom_button(__("Upload Material File"));

		if (frm.doc.material_type !== "File") {
			return;
		}

		const $button = frm.add_custom_button(__("Upload Material File"), openUploader, __("Actions"));
		$button.addClass("btn-primary");
	},

	setup_governed_drive_link(frm) {
		const drive = window.ifitwala_ed && window.ifitwala_ed.drive;
		if (!drive || typeof drive.addOpenContextButton !== "function" || frm.is_new()) {
			return;
		}

		drive.addOpenContextButton(frm, {
			doctype: "Supporting Material",
			name: frm.doc.name,
			label: __("Open in Drive"),
			group: __("Actions"),
		});
	},
});
