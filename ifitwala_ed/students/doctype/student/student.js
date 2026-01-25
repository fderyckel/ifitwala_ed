frappe.ui.form.on('Student', {
	refresh: function(frm) {
    if (!frm.doc.__islocal) {
      frm.trigger('setup_account_holder_filter');
    }

		if (frm.is_new()) {
			frm.disable_save();

			frm.set_intro(
				__(
					"<b>Direct Student creation is disabled.</b><br><br>" +
					"Students must be created via one of the following paths:<br>" +
					"1️⃣ <b>Admissions</b>: Promote a <i>Student Applicant</i><br>" +
					"2️⃣ <b>Migration / Import</b>: Use the Data Import tool (system-only)<br>" +
					"3️⃣ <b>System Scripts / API</b>: With explicit bypass flag<br><br>" +
					"If you are onboarding a new student, start from <b>Admissions</b>."
				),
				"orange"
			);
		}

		frm.trigger("setup_governed_image_upload");
	},

    anchor_school: function(frm) {
        frm.trigger('setup_account_holder_filter');
    },

    setup_account_holder_filter: function(frm) {
        if (frm.doc.anchor_school) {
             frappe.call({
                method: "ifitwala_ed.accounting.account_holder_utils.get_school_organization",
                args: { school: frm.doc.anchor_school },
                callback: function(r) {
                    if (r.message) {
                        frm.set_query("account_holder", function() {
                            return {
                                filters: {
                                    organization: r.message
                                }
                            };
                        });
                    }
                }
             });
        }
    }
});

frappe.ui.form.on("Student", {
	setup_governed_image_upload: function(frm) {
		const fieldname = "student_image";

		frm.set_df_property(fieldname, "read_only", 1);
		frm.set_df_property(
			fieldname,
			"description",
			__("Use the Upload Student Image action to attach a governed file.")
		);

		frm.remove_custom_button(__("Upload Student Image"), __("Actions"));
		frm.add_custom_button(
			__("Upload Student Image"),
			() => {
				if (frm.is_new()) {
					frappe.msgprint(__("Please save the Student before uploading an image."));
					return;
				}
				if (!frm.doc.anchor_school) {
					frappe.msgprint(__("Anchor School is required before uploading a student image."));
					return;
				}

				new frappe.ui.FileUploader({
					method: "ifitwala_ed.utilities.governed_uploads.upload_student_image",
					args: { student: frm.doc.name },
					allow_multiple: false,
					on_success(file_doc) {
						if (!file_doc || !file_doc.file_url) {
							frappe.msgprint(__("Upload succeeded but no file URL was returned."));
							return;
						}
						frm.set_value(fieldname, file_doc.file_url);
						frm.refresh_field(fieldname);
					},
				});
			},
			__("Actions")
		);

		if (frm.is_new()) {
			return;
		}

		frm.call({
			method: "ifitwala_ed.utilities.governed_uploads.get_governed_status",
			args: {
				doctype: "Student",
				name: frm.doc.name,
				fieldname,
			},
		}).then((res) => {
			const governed = res?.message?.governed ? __("Governed ✅") : __("Governed ❌");
			const base = __("Use the Upload Student Image action to attach a governed file.");
			frm.set_df_property(fieldname, "description", `${base} ${governed}`);
		});
	}
});
