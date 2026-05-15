frappe.provide('ifitwala_ed.drive');

(function () {
	function buildContextHref(options) {
		const doctype = options && options.doctype ? String(options.doctype).trim() : '';
		const name = options && options.name ? String(options.name).trim() : '';
		const bindingRole = options && options.bindingRole ? String(options.bindingRole).trim() : '';
		const params = new URLSearchParams();

		if (!doctype || !name) {
			return '/drive_workspace';
		}

		params.set('doctype', doctype);
		params.set('name', name);
		if (bindingRole) {
			params.set('binding_role', bindingRole);
		}

		return `/drive_workspace?${params.toString()}`;
	}

	function openContext(options) {
		const href = buildContextHref(options || {});
		window.open(href, '_blank', 'noopener');
		return href;
	}

	function addOpenContextButton(frm, options) {
		if (!frm || !frm.doc || frm.is_new()) {
			return null;
		}

		const label = options && options.label ? options.label : __('Open in Drive');
		const group = options && options.group ? options.group : __('Actions');
		const doctype = options && options.doctype ? options.doctype : frm.doctype;
		const name = options && options.name ? options.name : frm.doc.name;
		const bindingRole = options && options.bindingRole ? options.bindingRole : null;

		frm.remove_custom_button(label, group);
		frm.remove_custom_button(label);

		return frm.add_custom_button(
			label,
			() => {
				openContext({ doctype, name, bindingRole });
			},
			group
		);
	}

	ifitwala_ed.drive.buildContextHref = buildContextHref;
	ifitwala_ed.drive.openContext = openContext;
	ifitwala_ed.drive.addOpenContextButton = addOpenContextButton;
})();
