// Copyright (c) 2020, ifitwala and contributors
// For license information, please see license.txt

frappe.ui.form.on('Department', {
	refresh: function(frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__('Update Dpt Member Email Group'), function() {
				frappe.call({
					method: 'ifitwala_ed.organization_settings.doctype.department.department.update_dpt_email',
					args: {
						'doctype': 'Department',
						'name': frm.doc.name
					}
				});
			}, __('Communication'));

			frm.add_custom_button(__('Newsletter'), function() {
				frappe.route_options = {'Newsletter Email Group.email_group': frm.doc.name};
				frappe.set_route('List', 'Newsletter');
			}, __('Communication'));

			frm.add_custom_button(__('Meetings'), function() {
				frappe.route_options = {'department': frm.doc.name};
				frappe.set_route('List', 'Meeting');
			});
		}
	}

});

// in member child table, do filter out already present members.
frappe.ui.form.on('Department Member', {
	members_add: function(frm){
		frm.fields_dict['members'].grid.get_field('member').get_query = function(doc){
			let member_list = [];
			if(!doc.__islocal) member_list.push(doc.member);
			$.each(doc.members, function(idx, val){
				if (val.member) member_list.push(val.member);
			});
			return { filters: [['User', 'name', 'not in', member_list]] };
		};
	}
});
