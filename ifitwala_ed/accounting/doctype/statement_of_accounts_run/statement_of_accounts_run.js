frappe.ui.form.on("Statement Of Accounts Run", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Load Account Holders"), async () => {
				await frappe.call(
					"ifitwala_ed.accounting.doctype.statement_of_accounts_run.statement_of_accounts_run.load_account_holders",
					{ name: frm.doc.name }
				);
				await frm.reload_doc();
			});

			if ((frm.doc.items || []).length && frm.doc.status === "Draft") {
				frm.add_custom_button(__("Mark Processed"), async () => {
					await frappe.call(
						"ifitwala_ed.accounting.doctype.statement_of_accounts_run.statement_of_accounts_run.mark_processed",
						{ name: frm.doc.name }
					);
					await frm.reload_doc();
				});
			}
		}
	},
});
