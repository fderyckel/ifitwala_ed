const GET_PROGRAM_OFFERING_ACADEMIC_YEARS =
	'ifitwala_ed.accounting.doctype.program_billing_plan.program_billing_plan.get_program_offering_academic_years';
const GET_TERM_SPLIT_TERMS =
	'ifitwala_ed.accounting.doctype.program_billing_plan.program_billing_plan.get_term_split_terms';
const PREVIEW_BILLING_SCHEDULE_GENERATION =
	'ifitwala_ed.accounting.doctype.program_billing_plan.program_billing_plan.preview_billing_schedule_generation';
const GENERATE_BILLING_SCHEDULES =
	'ifitwala_ed.accounting.doctype.program_billing_plan.program_billing_plan.generate_billing_schedules';
const CUSTOM_PERCENTAGE_BASIS = 'Annual Amount Split by Custom Percentages';

function open_account_holder_tool(frm, payload) {
	frappe.new_doc('Student Account Holder Tool', {
		source_program_billing_plan: frm.doc.name,
		organization: payload.organization || frm.doc.organization,
		program_offering: payload.program_offering || frm.doc.program_offering,
		academic_year: payload.academic_year || frm.doc.academic_year,
	});
}

function create_billing_run_from_plan(frm) {
	if (!frm.doc.is_active) {
		frappe.msgprint(__('Only active Program Billing Plans can be used for Billing Runs.'));
		return;
	}

	frappe.new_doc('Billing Run', {
		billing_plan: frm.doc.name,
		organization: frm.doc.organization,
		program_offering: frm.doc.program_offering,
		academic_year: frm.doc.academic_year,
	});
}

function set_academic_year_query(frm) {
	frm.set_query('academic_year', () => {
		const academicYears = frm._program_billing_plan_academic_years || [];
		if (academicYears.length) {
			return {
				filters: { name: ['in', academicYears] },
				order_by: 'year_start_date desc',
			};
		}

		return { filters: { name: ['=', '___NONE___'] } };
	});
}

async function load_program_offering_academic_years(frm) {
	if (!frm.doc.program_offering) {
		frm._program_billing_plan_academic_years = [];
		return [];
	}

	const response = await frappe.call({
		method: GET_PROGRAM_OFFERING_ACADEMIC_YEARS,
		args: {
			program_offering: frm.doc.program_offering,
			organization: frm.doc.organization || null,
		},
	});
	const rows = response.message || [];
	frm._program_billing_plan_academic_years = rows
		.map(row => row.academic_year)
		.filter(academicYear => Boolean(academicYear));
	return frm._program_billing_plan_academic_years;
}

async function sync_academic_year_state(frm) {
	const academicYears = await load_program_offering_academic_years(frm);
	const hasOffering = Boolean(frm.doc.program_offering);
	const singleAcademicYear = hasOffering && academicYears.length === 1;

	frm.set_df_property('academic_year', 'read_only', !hasOffering || singleAcademicYear ? 1 : 0);
	frm.set_df_property(
		'academic_year',
		'description',
		hasOffering
			? __('Academic Year must be one of the years configured on the selected Program Offering.')
			: __('Select Program Offering first.')
	);

	if (!hasOffering) {
		if (frm.doc.academic_year) {
			await frm.set_value('academic_year', null);
		}
		frm.refresh_field('academic_year');
		return;
	}

	if (frm.doc.academic_year && !academicYears.includes(frm.doc.academic_year)) {
		await frm.set_value('academic_year', null);
		frappe.show_alert({
			message: __(
				'Academic Year was cleared because it is not part of the selected Program Offering.'
			),
			indicator: 'orange',
		});
	}

	if (!frm.doc.academic_year && singleAcademicYear) {
		await frm.set_value('academic_year', academicYears[0]);
	}

	frm.refresh_field('academic_year');
}

function has_custom_term_split_component(frm) {
	return (frm.doc.components || []).some(row => row.amount_basis === CUSTOM_PERCENTAGE_BASIS);
}

function sync_term_split_ui(frm) {
	frm.set_df_property('term_splits', 'hidden', 1);
	frm.remove_custom_button(__('Set Term Split Percentages'));
	if (frm.doc.billing_cadence === 'Term' && has_custom_term_split_component(frm)) {
		frm.add_custom_button(__('Set Term Split Percentages'), () => open_term_split_dialog(frm));
	}
}

async function open_term_split_dialog(frm) {
	if (!frm.doc.program_offering) {
		frappe.msgprint(__('Select Program Offering before editing term split percentages.'));
		return;
	}
	if (!frm.doc.academic_year) {
		frappe.msgprint(__('Select Academic Year before editing term split percentages.'));
		return;
	}

	const response = await frappe.call({
		method: GET_TERM_SPLIT_TERMS,
		args: {
			program_offering: frm.doc.program_offering,
			academic_year: frm.doc.academic_year,
			organization: frm.doc.organization || null,
		},
	});
	const terms = response.message || [];
	if (!terms.length) {
		frappe.msgprint(__('No academic terms are available for this billing plan.'));
		return;
	}

	const saved = {};
	(frm.doc.term_splits || []).forEach(row => {
		if (row.term) {
			saved[row.term] = row.percentage;
		}
	});

	const dialog = new frappe.ui.Dialog({
		title: __('Term Split Percentages'),
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'term_split_html',
			},
		],
		primary_action_label: __('Apply'),
		primary_action() {
			const values = read_term_split_values(dialog, terms);
			if (!values) {
				return;
			}

			frm.clear_table('term_splits');
			values.forEach(row => {
				const child = frm.add_child('term_splits');
				child.term = row.term;
				child.term_label = row.term_label;
				child.percentage = row.percentage;
			});
			frm.refresh_field('term_splits');
			frm.dirty();
			dialog.hide();
		},
	});

	dialog.show();
	dialog.fields_dict.term_split_html.$wrapper.html(render_term_split_table(terms, saved));
}

function read_term_split_values(dialog, terms) {
	const rows = [];
	let total = 0;
	let has_invalid_value = false;
	dialog.fields_dict.term_split_html.$wrapper.find('[data-term-percentage]').each(function () {
		const input = $(this);
		const term = input.attr('data-term');
		const termRow = terms.find(row => row.term === term);
		const percentage = Number(input.val());
		if (!Number.isFinite(percentage) || percentage < 0) {
			has_invalid_value = true;
			return;
		}
		total += percentage;
		rows.push({
			term,
			term_label: termRow?.term_label || term,
			percentage,
		});
	});

	if (has_invalid_value) {
		frappe.msgprint(__('Each term split percentage must be zero or greater.'));
		return null;
	}

	if (Math.abs(total - 100) > 0.0001) {
		frappe.msgprint(
			__('Term split percentages must total 100%. Current total is {0}.', [total.toFixed(4)])
		);
		return null;
	}

	return rows;
}

function render_term_split_table(terms, saved) {
	const body = terms
		.map(term => {
			const percentage =
				saved[term.term] !== undefined && saved[term.term] !== null
					? saved[term.term]
					: term.length_percentage || 0;
			return `
				<tr>
					<td>${escape_html(term.term_label || term.term)}</td>
					<td>${escape_html(term.coverage_start || '')} - ${escape_html(term.coverage_end || '')}</td>
					<td class="text-right">${escape_html(String(term.day_count || 0))}</td>
					<td class="text-right">${escape_html(String(term.length_percentage || 0))}%</td>
					<td>
						<input
							class="form-control text-right"
							type="number"
							min="0"
							step="0.0001"
							value="${escape_html(String(percentage))}"
							data-term="${escape_html(term.term)}"
							data-term-percentage="1"
						/>
					</td>
				</tr>
			`;
		})
		.join('');

	return `
		<div class="small text-muted" style="margin-bottom: 12px;">
			${escape_html(__("Set each term's share of the full annual amount. The total must be 100%."))}
		</div>
		<div class="table-responsive">
			<table class="table table-bordered">
				<thead>
					<tr>
						<th>${escape_html(__('Term'))}</th>
						<th>${escape_html(__('Coverage'))}</th>
						<th class="text-right">${escape_html(__('Days'))}</th>
						<th class="text-right">${escape_html(__('By Length'))}</th>
						<th>${escape_html(__('Custom %'))}</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>
		</div>
	`;
}

function escape_html(value) {
	return frappe.utils?.escape_html
		? frappe.utils.escape_html(value)
		: $('<div>').text(value).html();
}

async function open_billing_schedule_preview_dialog(frm) {
	try {
		if (frm.is_dirty()) {
			await frm.save();
		}
	} catch (error) {
		frappe.msgprint(
			error?.message || __('Save the billing plan before previewing schedule generation.')
		);
		return;
	}

	let response;
	try {
		response = await frappe.call({
			method: PREVIEW_BILLING_SCHEDULE_GENERATION,
			args: { program_billing_plan: frm.doc.name },
		});
	} catch (error) {
		frappe.msgprint(error?.message || __('Unable to preview billing schedule generation.'));
		return;
	}
	const preview = response.message || {};
	const hasEnrollments = Number(preview.enrollment_count || 0) > 0;
	const dialog = new frappe.ui.Dialog({
		title: __('Review Billing Schedule Generation'),
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'preview_html',
			},
		],
		primary_action_label: hasEnrollments ? __('Confirm and Generate') : __('Close'),
		async primary_action() {
			if (!hasEnrollments) {
				dialog.hide();
				return;
			}
			const primaryButton = dialog.get_primary_btn();
			primaryButton.prop('disabled', true);
			primaryButton.text(__('Generating...'));
			const generated = await generate_billing_schedules(frm);
			if (generated) {
				dialog.hide();
				return;
			}
			primaryButton.prop('disabled', false);
			primaryButton.text(__('Confirm and Generate'));
		},
	});

	dialog.show();
	dialog.fields_dict.preview_html.$wrapper.html(render_billing_schedule_preview(preview));
}

async function generate_billing_schedules(frm) {
	try {
		const r = await frappe.call(GENERATE_BILLING_SCHEDULES, {
			program_billing_plan: frm.doc.name,
		});
		const message = r.message || {};
		if (message.requires_account_holder_setup) {
			frappe.show_alert({
				message: __(
					'{0} enrolled student(s) need an Account Holder before billing schedules can be generated.',
					[message.missing_count || 0]
				),
				indicator: 'orange',
			});
			open_account_holder_tool(frm, message);
			return true;
		}
		frappe.msgprint(
			__('Generated or refreshed {0} billing schedules.', [message.schedule_names?.length || 0])
		);
		return true;
	} catch (error) {
		frappe.msgprint(error?.message || __('Unable to generate billing schedules.'));
		return false;
	}
}

function render_billing_schedule_preview(preview) {
	const enrollmentCount = Number(preview.enrollment_count || 0);
	const missingCount = Number(preview.missing_account_holder_count || 0);
	const periodRows = Array.isArray(preview.period_totals) ? preview.period_totals : [];
	const componentRows = Array.isArray(preview.component_rows) ? preview.component_rows : [];
	const statusHtml = render_generation_preview_status(enrollmentCount, missingCount);

	return `
		${statusHtml}
		<div class="small text-muted" style="margin-bottom: 12px;">
			${escape_html(
				__(
					'Confirming will create missing schedules and refresh pending schedule rows. Rows already linked to invoices are preserved.'
				)
			)}
		</div>
		${render_generation_period_totals(periodRows)}
		${render_generation_component_rows(componentRows)}
		<div class="small text-muted" style="margin-top: 12px;">
			${escape_html(__('Estimated full generation total: {0}', [format_money(preview.estimated_total || 0)]))}
		</div>
	`;
}

function render_generation_preview_status(enrollmentCount, missingCount) {
	if (!enrollmentCount) {
		return `
			<div class="alert alert-warning">
				${escape_html(__('No active Program Enrollments were found for this billing plan.'))}
			</div>
		`;
	}
	if (missingCount) {
		return `
			<div class="alert alert-warning">
				${escape_html(
					__(
						'{0} enrolled student(s) still need an Account Holder. Confirming will take you to the setup tool before schedules can be generated.',
						[missingCount]
					)
				)}
			</div>
		`;
	}
	return `
		<div class="alert alert-info">
			${escape_html(
				__('This will generate or refresh billing schedules for {0} enrolled student(s).', [
					enrollmentCount,
				])
			)}
		</div>
	`;
}

function render_generation_period_totals(rows) {
	if (!rows.length) {
		return '';
	}
	const body = rows
		.map(row => {
			return `
				<tr>
					<td>${escape_html(row.period_label || row.period_key || '')}</td>
					<td>${escape_html(row.coverage_start || '')} - ${escape_html(row.coverage_end || '')}</td>
					<td class="text-right">${escape_html(format_money(row.per_student_total || 0))}</td>
					<td class="text-right">${escape_html(format_money(row.estimated_total || 0))}</td>
				</tr>
			`;
		})
		.join('');

	return `
		<div class="table-responsive" style="margin-bottom: 12px;">
			<table class="table table-bordered">
				<thead>
					<tr>
						<th>${escape_html(__('Period'))}</th>
						<th>${escape_html(__('Coverage'))}</th>
						<th class="text-right">${escape_html(__('Per Student'))}</th>
						<th class="text-right">${escape_html(__('Estimated Total'))}</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>
		</div>
	`;
}

function render_generation_component_rows(rows) {
	if (!rows.length) {
		return '';
	}
	const body = rows
		.map(row => {
			return `
				<tr>
					<td>${escape_html(row.period_label || '')}</td>
					<td>${escape_html(row.billable_offering_label || row.billable_offering || '')}</td>
					<td>${escape_html(row.amount_basis || '')}</td>
					<td class="text-right">${escape_html(String(row.qty || 0))}</td>
					<td class="text-right">${escape_html(format_money(row.rate || 0))}</td>
					<td class="text-right">${escape_html(format_money(row.expected_amount || 0))}</td>
				</tr>
			`;
		})
		.join('');

	return `
		<div class="table-responsive">
			<table class="table table-bordered">
				<thead>
					<tr>
						<th>${escape_html(__('Period'))}</th>
						<th>${escape_html(__('Component'))}</th>
						<th>${escape_html(__('Basis'))}</th>
						<th class="text-right">${escape_html(__('Qty'))}</th>
					<th class="text-right">${escape_html(__('Unit Billing Amount'))}</th>
					<th class="text-right">${escape_html(__('Line Amount'))}</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>
		</div>
	`;
}

function format_money(value) {
	return frappe.format(Number(value || 0), { fieldtype: 'Currency' });
}

frappe.ui.form.on('Program Billing Plan', {
	setup(frm) {
		set_academic_year_query(frm);
	},

	onload(frm) {
		set_academic_year_query(frm);
		sync_academic_year_state(frm);
	},

	refresh(frm) {
		set_academic_year_query(frm);
		sync_academic_year_state(frm);
		sync_term_split_ui(frm);

		if (!frm.is_new()) {
			frm.add_custom_button(__('Generate Billing Schedules'), async () => {
				await open_billing_schedule_preview_dialog(frm);
			});
			frm.add_custom_button(__('Create Billing Run'), () => {
				create_billing_run_from_plan(frm);
			});
		}
	},

	program_offering(frm) {
		sync_academic_year_state(frm);
	},

	organization(frm) {
		sync_academic_year_state(frm);
	},

	billing_cadence(frm) {
		sync_term_split_ui(frm);
	},
});

frappe.ui.form.on('Program Billing Plan Component', {
	amount_basis(frm) {
		sync_term_split_ui(frm);
	},

	components_remove(frm) {
		sync_term_split_ui(frm);
	},
});
