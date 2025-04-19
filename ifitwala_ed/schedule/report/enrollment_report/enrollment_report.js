// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Enrollment Report"] = {
	"filters": [
			{
					"fieldname": "report_type",
					"label": "Report Type",
					"fieldtype": "Select",
					"options": "\nProgram\nCourse",
					"default": "Program"
			},
			{
					"fieldname": "school",
					"label": "School",
					"fieldtype": "Link",
					"options": "School"
			},
			{
					"fieldname": "program",
					"label": "Program",
					"fieldtype": "Link",
					"options": "Program"
			},
			{
					"fieldname": "academic_year",
					"label": "Academic Year",
					"fieldtype": "Link",
					"options": "Academic Year",
					"depends_on": "eval:doc.report_type=='Course' || doc.report_type=='Program'", 
					"get_query": function (doc) {
						let school = frappe.query_report.get_filter_value("school");
						if (school) {
								return {
										query: "ifitwala_ed.schedule.report.enrollment_report.enrollment_report.get_academic_years_for_school",
										filters: { school: school }
								};
						}
					}
			}
	],
	"chart_type": "bar",
	"default_columns": 2,

	onload: function (report) {
		frappe.after_ajax(() => {
			let tries = 0;
			const interval = setInterval(() => {
				const chart = report.chartObj?.chart;
				const opts = report.chart?.custom_options;
	
				if (chart && opts?.tooltip_breakdown) {
					clearInterval(interval);
	
					// ✅ Tooltip override
					chart.options.tooltipOptions = {
						formatTooltipX: label => label,
						formatTooltipY: (value, name, opts, index) => {
							const breakdown = report.chart.custom_options.tooltip_breakdown;
							const label = chart.data.labels[index];
							const items = breakdown[label];
							if (items?.length) {
								return `<strong>${label}</strong><br>${items.join("<br>")}`;
							}
							return `${name}: ${value}`;
						}
					};
	
					chart.update(chart.data);
	
					// ✅ Custom Legend
					const legendLabels = opts.legend_labels || [];
					const legendColors = opts.legend_colors || [];
	
					if (legendLabels.length && legendColors.length) {
						const container = document.createElement("div");
						container.className = "custom-legend";
						container.style.display = "flex";
						container.style.flexWrap = "wrap";
						container.style.marginTop = "12px";
						container.style.gap = "12px";
	
						legendLabels.forEach((label, i) => {
							const item = document.createElement("div");
							item.style.display = "flex";
							item.style.alignItems = "center";
							item.innerHTML = `
								<span style="width: 12px; height: 12px; background: ${legendColors[i]}; display: inline-block; margin-right: 6px; border-radius: 3px;"></span>
								<span>${label}</span>
							`;
							container.appendChild(item);
						});
	
						const chartWrapper = report.chartObj.wrapper;
						chartWrapper.parentElement.appendChild(container);
					}
				}
	
				if (++tries > 20) clearInterval(interval);
			}, 250);
		});
	}
	
	
};
