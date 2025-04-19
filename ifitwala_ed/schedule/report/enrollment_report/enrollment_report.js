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
	
	onload: function(report) {
		frappe.after_ajax(() => {
				let tries = 0;
				const interval = setInterval(() => {
						const chart = report.chartObj?.chart;
						const breakdown = report.chart?.custom_options?.tooltip_breakdown;
						const legend_labels = report.chart?.custom_options?.legend_labels || [];
						const legend_colors = report.chart?.custom_options?.legend_colors || [];

						if (chart) {
								clearInterval(interval);

								// 1. Handle tooltips
								chart.options.tooltipOptions = {
										formatTooltipX: label => label,
										formatTooltipY: (value, name, opts, index) => {
												const label = chart.data.labels[index];
												const items = breakdown?.[label] || [];
												return items.length 
														? `<strong>${label}</strong><br>${items.join("<br>")}`
														: `${name}: ${value}`;
										}
								};

								// 2. Always create legend if we have labels
								if (legend_labels.length) {
										const wrapper = chart.wrapper.parentElement;
										const legend = document.createElement("div");
										legend.style.display = "flex";
										legend.style.gap = "12px";
										legend.style.marginTop = "16px";
										legend.style.flexWrap = "wrap";

										legend_labels.forEach((label, i) => {
												const item = document.createElement("div");
												item.style.display = "flex";
												item.style.alignItems = "center";
												item.innerHTML = `
														<div style="width:12px; height:12px; 
																background:${legend_colors[i] || '#999'}; 
																border-radius:3px; margin-right:6px;">
														</div>
														<span>${label}</span>
												`;
												legend.appendChild(item);
										});

										wrapper?.appendChild(legend);
								}

								chart.update(chart.data);
						}

						if (++tries > 20) clearInterval(interval);
				}, 250);
		});
	}
};
