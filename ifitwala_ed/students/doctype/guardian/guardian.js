// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/students/doctype/guardian/guardian.js

frappe.ui.form.on("Guardian", {
	refresh(frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: "name", doctype: "Guardian" };
		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}

		if (!frm.doc.user && !frm.is_new()) {
			frm.add_custom_button(__("Create and Invite as User"), () => {
				frappe.call({
					method: "ifitwala_ed.students.doctype.guardian.guardian.create_guardian_user",
					args: { guardian: frm.doc.name }
				}).then(() => frm.reload_doc());
			});
		}

		frm.trigger("setup_governed_image_upload");
		frm.trigger("setup_governed_drive_link");
	},

	setup_governed_image_upload(frm) {
		const fieldname = "guardian_image";
		const openUploader = () => {
			if (frm.is_new()) {
				frappe.msgprint(__("Please save the Guardian before uploading a photo."));
				return;
			}

			if (!frm.doc.organization) {
				frappe.msgprint(
					__("Guardian Organization is required, or must be derivable from linked students, before uploading a photo.")
				);
			}

			new frappe.ui.FileUploader({
				method: "ifitwala_ed.utilities.governed_uploads.upload_guardian_image",
				args: { guardian: frm.doc.name },
				doctype: "Guardian",
				docname: frm.doc.name,
				fieldname,
				is_private: 0,
				disable_private: true,
				allow_multiple: false,
				on_success(file_doc) {
					const payload = file_doc?.message
						|| (Array.isArray(file_doc) ? file_doc[0] : file_doc)
						|| (typeof file_doc === "string" ? { file_url: file_doc } : null);
					if (payload?.file_url) {
						frm.set_value(fieldname, payload.file_url);
						frm.refresh_field(fieldname);
					}
					frm.reload_doc();
				},
				on_error() {
					frappe.msgprint(__("Upload failed. Please try again."));
				},
			});
		};

		frm.set_df_property(fieldname, "read_only", 1);
		frm.set_df_property(
			fieldname,
			"description",
			__("Use the Upload Guardian Photo action to attach a governed file.")
		);

		frm.remove_custom_button(__("Upload Guardian Photo"), __("Actions"));
		frm.remove_custom_button(__("Upload Guardian Photo"));
		const $actionBtn = frm.add_custom_button(__("Upload Guardian Photo"), openUploader);
		$actionBtn.addClass("btn-primary");

		const wrapper = frm.get_field(fieldname)?.$wrapper;
		if (wrapper?.length && !wrapper.find(".governed-upload-btn").length) {
			const $container = wrapper.find(".control-input").length
				? wrapper.find(".control-input")
				: wrapper;
			const $btn = $(
				`<button type="button" class="btn btn-xs btn-primary governed-upload-btn">
					${__("Upload Guardian Photo")}
				</button>`
			);
			$btn.on("click", openUploader);
			$container.append($btn);
		}

		if (frm.is_new()) {
			return;
		}

		frm.call({
			method: "ifitwala_ed.utilities.governed_uploads.get_governed_status",
			args: {
				doctype: "Guardian",
				name: frm.doc.name,
				fieldname,
			},
		}).then((res) => {
			const governed = res?.message?.governed ? __("Governed ✅") : __("Governed ❌");
			const base = __("Use the Upload Guardian Photo action to attach a governed file.");
			frm.set_df_property(fieldname, "description", `${base} ${governed}`);
		});
	},

	setup_governed_drive_link(frm) {
		const drive = window.ifitwala_ed && window.ifitwala_ed.drive;
		if (!drive || typeof drive.addOpenContextButton !== "function" || frm.is_new()) {
			return;
		}

		drive.addOpenContextButton(frm, {
			doctype: "Guardian",
			name: frm.doc.name,
			label: __("Open in Drive"),
			group: __("Actions"),
		});
	},

	salutation(frm) {
		if (!frm.doc.salutation) return;
		const map = { "Mr": "Male", "Ms": "Female", "Mrs": "Female", "Miss": "Female", "Mx": "Prefer Not To Say" };
		const v = map[frm.doc.salutation];
		if (v) frm.set_value("guardian_gender", v);
	},
});
