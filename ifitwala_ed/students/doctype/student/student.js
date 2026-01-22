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
