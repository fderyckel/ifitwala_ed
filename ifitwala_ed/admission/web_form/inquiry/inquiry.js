frappe.ready(function() {
	const admissionFields = [
		'student_first_name',
		'student_last_name',
		'intended_academic_year',
		'grade_level_interest',
		'program_interest'
	];
	const currentFamilyFields = ['student_name_or_id', 'relationship_to_student'];
	const partnershipFields = ['organization_name', 'partnership_context'];
	const dynamicFields = [...admissionFields, ...currentFamilyFields, ...partnershipFields];

	function setFieldHidden(fieldname, hidden) {
		if (!frappe.web_form || !fieldname) {
			return;
		}

		if (typeof frappe.web_form.set_df_property === 'function') {
			frappe.web_form.set_df_property(fieldname, 'hidden', hidden ? 1 : 0);
			return;
		}

		const field = frappe.web_form.fields_dict && frappe.web_form.fields_dict[fieldname];
		if (field && field.df) {
			field.df.hidden = hidden ? 1 : 0;
			if (typeof field.refresh === 'function') {
				field.refresh();
			}
		}
	}

	function clearField(fieldname) {
		if (!frappe.web_form || typeof frappe.web_form.set_value !== 'function') {
			return;
		}
		frappe.web_form.set_value(fieldname, '');
	}

	function updateInquiryFields() {
		if (!frappe.web_form || typeof frappe.web_form.get_value !== 'function') {
			return;
		}

		const type = String(frappe.web_form.get_value('type_of_inquiry') || '').trim();
		const visibleFields = new Set();

		if (type === 'Admission') {
			admissionFields.forEach((fieldname) => visibleFields.add(fieldname));
		} else if (type === 'Current Family') {
			currentFamilyFields.forEach((fieldname) => visibleFields.add(fieldname));
		} else if (type === 'Partnership / Agent') {
			partnershipFields.forEach((fieldname) => visibleFields.add(fieldname));
		}

		dynamicFields.forEach((fieldname) => {
			const hidden = !visibleFields.has(fieldname);
			setFieldHidden(fieldname, hidden);
			if (hidden) {
				clearField(fieldname);
			}
		});
	}

	if (frappe.web_form && typeof frappe.web_form.on === 'function') {
		frappe.web_form.on('type_of_inquiry', updateInquiryFields);
	}

	updateInquiryFields();
});
